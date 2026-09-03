#!/usr/bin/env node

import { randomUUID } from 'node:crypto';
import { pathToFileURL } from 'node:url';

import {
  activatePendingWorkflow,
  completeIndependentValidation,
  completeBrowserCall,
  invalidateOperation,
  readActiveOperation,
  readPendingOperation,
  reconcileOutcomeUnknown,
  recordOutcomeUnknown,
  stageBrowserCall,
  writePendingOperation,
} from './browser-binding-store.mjs';
import { EFFECT_CLASSES, normalizeOrigin, parseOperationEnvelope } from './browser-contract.mjs';
import { BrowserWorkflowError, parseWorkflowSteps, workflowFingerprint } from './browser-workflow.mjs';
import { resolveBrowserAdapter } from './browser-adapters/index.mjs';


const STEPS = Object.freeze([
  'open', 'inspect', 'navigate', 'fill', 'select', 'click', 'submit',
  'upload', 'download', 'screenshot', 'trace', 'validate', 'close',
]);
const REPEATABLE = new Set([
  '--service-origin', '--auth-origin', '--action', '--modifier', '--artifact-type',
  '--artifact-source-class', '--artifact-destination-class',
  '--workflow-step', '--validation-step',
]);
const OPEN_FLAGS = new Set([
  '--step', '--operation-id', '--session-id', '--role', '--objective-ref', '--target',
  '--environment', '--service-origin', '--auth-origin', '--identity-ref',
  '--credential-transport', '--permission-mode', '--action', '--effect', '--risk',
  '--modifier', '--precondition-ref', '--validation-ref', '--compensation-ref',
  '--expires-in-seconds',
  '--artifact-type', '--artifact-purpose-ref', '--artifact-source-class',
  '--artifact-destination-class', '--artifact-max-items', '--artifact-max-bytes',
  '--artifact-redaction', '--artifact-retention-seconds',
  '--workflow-step', '--validation-step',
]);
const STEP_FLAGS = new Set([
  '--operation-id', '--step', '--origin', '--locator-role', '--locator-name',
  '--value-ref', '--expect-ref', '--effect', '--artifact-ref',
]);
const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$/u;
const ACTION = /^[a-z0-9][a-z0-9-]{0,95}$/u;
const RISK_ALIASES = new Map([
  ['safe', 'SAFE_READ_ONLY'], ['low', 'LOW_RISK_CHANGE'],
  ['medium', 'DISRUPTIVE_CHANGE'], ['high', 'DESTRUCTIVE'],
]);
const EXECUTOR_ROLES = new Set([
  'main', 'cloud-platform-operator', 'database-operator', 'diagnostic-operator',
  'kubernetes-operator', 'network-edge-operator', 'observability-sre',
  'release-cicd-operator',
]);
const AUDIT_ACTIONS = new Set(['inspect', 'validate', 'close']);


export class BrowserRunnerError extends Error {
  constructor(code) {
    super(code);
    this.name = 'BrowserRunnerError';
    this.code = code;
  }
}


function fail(code) {
  throw new BrowserRunnerError(`BROWSER_RUNNER_${code}`);
}


function freeze(value) {
  if (value && typeof value === 'object') {
    for (const child of Object.values(value)) freeze(child);
    Object.freeze(value);
  }
  return value;
}


function parseFlags(argv) {
  if (!Array.isArray(argv) || argv.length < 2 || argv.length > 224) fail('INVALID_ARGUMENTS');
  const values = new Map();
  for (let index = 0; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (typeof flag !== 'string' || !flag.startsWith('--') || typeof value !== 'string'
        || value.length < 1 || value.length > 2048 || /[\r\n\0]/u.test(value)) fail('INVALID_ARGUMENTS');
    if (!REPEATABLE.has(flag) && values.has(flag)) fail('DUPLICATE_FLAG');
    const entries = values.get(flag) ?? [];
    entries.push(value);
    values.set(flag, entries);
  }
  return values;
}


function one(values, flag, required = true) {
  const entries = values.get(flag) ?? [];
  if (entries.length === 0 && !required) return null;
  if (entries.length !== 1) fail('MISSING_OR_DUPLICATE_FLAG');
  return entries[0];
}


function many(values, flag, minimum = 0) {
  const entries = values.get(flag) ?? [];
  if (entries.length < minimum) fail('MISSING_FLAG');
  return entries;
}


function bounded(value, pattern = IDENTIFIER) {
  if (typeof value !== 'string' || !pattern.test(value)) fail('INVALID_VALUE');
  return value;
}


function origin(value) {
  try {
    return normalizeOrigin(value);
  } catch {
    fail('INVALID_ORIGIN');
  }
}


function risk(value) {
  const normalized = RISK_ALIASES.get(value) ?? value;
  if (!['SAFE_READ_ONLY', 'LOW_RISK_CHANGE', 'DISRUPTIVE_CHANGE', 'DESTRUCTIVE'].includes(normalized)) {
    fail('INVALID_RISK');
  }
  return normalized;
}


function integer(values, flag, maximum) {
  const value = one(values, flag);
  if (!/^[1-9][0-9]{0,7}$/u.test(value) || Number(value) > maximum) fail('INVALID_ARTIFACT_POLICY');
  return Number(value);
}


function parseOpen(values, now, workflow = false) {
  for (const flag of values.keys()) if (!OPEN_FLAGS.has(flag)) fail('UNKNOWN_FLAG');
  if (!workflow && (values.has('--workflow-step') || values.has('--validation-step'))) fail('UNKNOWN_FLAG');
  const seconds = one(values, '--expires-in-seconds');
  if (!/^[1-9][0-9]{0,4}$/u.test(seconds) || Number(seconds) > 86_400) fail('INVALID_EXPIRY');
  const effect = one(values, '--effect');
  if (!EFFECT_CLASSES.includes(effect) || effect === 'UNKNOWN') fail('INVALID_EFFECT');
  const artifactFlags = [
    '--artifact-type', '--artifact-purpose-ref', '--artifact-source-class',
    '--artifact-destination-class', '--artifact-max-items', '--artifact-max-bytes',
    '--artifact-redaction', '--artifact-retention-seconds',
  ];
  const artifactsEnabled = artifactFlags.some((flag) => values.has(flag));
  if (artifactsEnabled && artifactFlags.some((flag) => !values.has(flag))) fail('INVALID_ARTIFACT_POLICY');
  const artifactPolicy = artifactsEnabled ? {
    enabled: true,
    types: many(values, '--artifact-type', 1).map((item) => bounded(item, ACTION)),
    purposeRef: bounded(one(values, '--artifact-purpose-ref')),
    sourceClasses: many(values, '--artifact-source-class', 1).map((item) => bounded(item, ACTION)),
    destinationClasses: many(values, '--artifact-destination-class', 1).map((item) => bounded(item, ACTION)),
    maxItems: integer(values, '--artifact-max-items', 16),
    maxBytes: integer(values, '--artifact-max-bytes', 50_000_000),
    redaction: one(values, '--artifact-redaction'),
    retentionSeconds: integer(values, '--artifact-retention-seconds', 3600),
  } : {
    enabled: false, types: [], purposeRef: 'none', sourceClasses: [],
    destinationClasses: [], maxItems: 0, maxBytes: 0, redaction: 'none', retentionSeconds: 0,
  };
  const envelope = parseOperationEnvelope({
    version: 1,
    operationId: bounded(one(values, '--operation-id')),
    sessionId: bounded(one(values, '--session-id')),
    role: bounded(one(values, '--role')),
    objectiveRef: bounded(one(values, '--objective-ref')),
    target: bounded(one(values, '--target')),
    environment: bounded(one(values, '--environment')),
    serviceOrigins: many(values, '--service-origin', 1).map(origin),
    authOrigins: many(values, '--auth-origin').map(origin),
    identityRef: bounded(one(values, '--identity-ref')),
    credentialTransport: bounded(one(values, '--credential-transport'), ACTION),
    permissionModeAtApproval: bounded(one(values, '--permission-mode')),
    actions: many(values, '--action', 1).map((item) => bounded(item, ACTION)),
    expectedEffect: effect,
    risk: risk(one(values, '--risk')),
    modifiers: many(values, '--modifier').map((item) => bounded(item, /^[A-Z][A-Z_]{0,63}$/u)),
    preconditionRef: bounded(one(values, '--precondition-ref')),
    validationRef: bounded(one(values, '--validation-ref')),
    compensationRef: bounded(one(values, '--compensation-ref')),
    artifactPolicy,
    expiresAt: now + Number(seconds) * 1000,
  }, now);
  const auditReadOnly = envelope.role === 'audit-evidence-collector'
    && ['PUBLIC_READ', 'SENSITIVE_READ'].includes(envelope.expectedEffect)
    && envelope.actions.every((action) => AUDIT_ACTIONS.has(action));
  if (!EXECUTOR_ROLES.has(envelope.role) && !auditReadOnly) fail('ROLE_NOT_EXECUTOR');
  if (envelope.artifactPolicy.enabled
      && envelope.artifactPolicy.types.some((type) => !envelope.actions.includes(type))) {
    fail('INVALID_ARTIFACT_POLICY');
  }
  return freeze({ step: 'open', operationId: envelope.operationId, envelope });
}


function parseWorkflow(values, now) {
  const opening = parseOpen(values, now, true);
  let workflow;
  try {
    workflow = parseWorkflowSteps(many(values, '--workflow-step', 1), many(values, '--validation-step', 1));
  } catch (error) {
    if (error instanceof BrowserWorkflowError) fail(error.code);
    throw error;
  }
  const allowedOrigins = new Set([...opening.envelope.serviceOrigins, ...opening.envelope.authOrigins]);
  for (const step of [...workflow.executionSteps, ...workflow.validationSteps]) {
    if (!allowedOrigins.has(step.origin)) fail('WORKFLOW_ORIGIN_NOT_BOUND');
    if (!opening.envelope.actions.includes(step.step)) fail('WORKFLOW_ACTION_NOT_BOUND');
  }
  if (workflow.validationSteps.at(-1).expectRef !== opening.envelope.validationRef) {
    fail('WORKFLOW_VALIDATION_REFERENCE');
  }
  const request = {
    step: 'workflow', operationId: opening.operationId, envelope: opening.envelope,
    executionSteps: workflow.executionSteps, validationSteps: workflow.validationSteps,
    expiresInSeconds: Number(one(values, '--expires-in-seconds')),
  };
  return freeze({ ...request, invocationFingerprint: workflowFingerprint(request) });
}


function parseStep(values) {
  for (const flag of values.keys()) if (!STEP_FLAGS.has(flag)) fail('UNKNOWN_FLAG');
  const step = one(values, '--step');
  if (!STEPS.includes(step) || step === 'open') fail('INVALID_STEP');
  const request = {
    operationId: bounded(one(values, '--operation-id')),
    step,
    origin: values.has('--origin') ? origin(one(values, '--origin')) : null,
    locatorRole: values.has('--locator-role') ? bounded(one(values, '--locator-role'), ACTION) : null,
    locatorName: values.has('--locator-name') ? bounded(one(values, '--locator-name')) : null,
    valueRef: values.has('--value-ref') ? bounded(one(values, '--value-ref')) : null,
    expectRef: values.has('--expect-ref') ? bounded(one(values, '--expect-ref')) : null,
    effect: values.has('--effect') ? one(values, '--effect') : null,
    artifactRef: values.has('--artifact-ref') ? bounded(one(values, '--artifact-ref')) : null,
  };
  if (request.effect !== null && !EFFECT_CLASSES.includes(request.effect)) fail('INVALID_EFFECT');
  const required = {
    inspect: ['origin', 'locatorRole', 'expectRef'], navigate: ['origin'],
    fill: ['origin', 'locatorRole', 'valueRef'], select: ['origin', 'locatorRole', 'valueRef'],
    click: ['origin', 'locatorRole', 'effect'], submit: ['origin', 'locatorRole', 'effect'],
    upload: ['origin', 'artifactRef'], download: ['origin', 'artifactRef'],
    screenshot: ['origin', 'artifactRef'], trace: ['origin', 'artifactRef'],
    validate: ['expectRef'], close: [],
  }[step];
  for (const field of required) if (request[field] === null) fail('MISSING_FLAG');
  const allowed = new Set(['operationId', 'step', ...required]);
  if (request.locatorName !== null && ['inspect', 'fill', 'select', 'click', 'submit'].includes(step)) {
    allowed.add('locatorName');
  }
  for (const [field, value] of Object.entries(request)) {
    if (value !== null && !allowed.has(field)) fail('FLAG_NOT_ALLOWED_FOR_STEP');
  }
  return freeze(request);
}


export function parseRunnerArgs(argv, now = Date.now()) {
  try {
    if (!Number.isSafeInteger(now) || now < 0) fail('INVALID_CLOCK');
    const values = parseFlags(argv);
    const step = one(values, '--step');
    if (step === 'open') return parseOpen(values, now);
    if (step === 'workflow') return parseWorkflow(values, now);
    return parseStep(values);
  } catch (error) {
    if (error instanceof BrowserRunnerError) throw error;
    fail('INVALID_CONTRACT');
  }
}


function stepEffect(request) {
  if (['inspect', 'validate'].includes(request.step)) return 'SENSITIVE_READ';
  if (['navigate', 'fill', 'select', 'close'].includes(request.step)) return 'INTERACTIVE_STATE';
  if (['click', 'submit'].includes(request.step)) return request.effect;
  if (['upload', 'download', 'screenshot', 'trace'].includes(request.step)) return 'SENSITIVE_ARTIFACT';
  return 'UNKNOWN';
}


function workflowStepEffect(request) {
  if (request.step === 'inspect') return 'SENSITIVE_READ';
  return stepEffect(request);
}


function effectRank(effect) {
  return ['PUBLIC_READ', 'SENSITIVE_READ', 'INTERACTIVE_STATE', 'LOW_RISK_CHANGE',
    'DISRUPTIVE_CHANGE', 'DESTRUCTIVE_CHANGE'].indexOf(effect);
}


export function authorizeRunnerStep(request, envelope, capability, now = Date.now()) {
  if (capability?.state !== 'ACTIVE' || capability?.routeClass !== 'PROTECTED_RUNNER') {
    return freeze({ allowed: false, reasonCode: 'CAPABILITY_UNAVAILABLE', effect: stepEffect(request) });
  }
  if (now >= envelope.expiresAt) return freeze({ allowed: false, reasonCode: 'OPERATION_EXPIRED', effect: stepEffect(request) });
  const effect = stepEffect(request);
  const roleAllowed = EXECUTOR_ROLES.has(envelope.role)
    || (envelope.role === 'audit-evidence-collector' && effect === 'SENSITIVE_READ');
  if (!roleAllowed) return freeze({ allowed: false, reasonCode: 'ROLE_NOT_EXECUTOR', effect });
  if (!Array.isArray(capability.effects) || !capability.effects.includes(effect)) {
    return freeze({ allowed: false, reasonCode: 'CAPABILITY_EFFECT_UNAVAILABLE', effect });
  }
  if (!envelope.actions.includes(request.step)) return freeze({ allowed: false, reasonCode: 'ACTION_NOT_BOUND', effect: stepEffect(request) });
  if (request.origin && ![...envelope.serviceOrigins, ...envelope.authOrigins].includes(request.origin)) {
    return freeze({ allowed: false, reasonCode: 'ORIGIN_ESCAPE', effect: stepEffect(request) });
  }
  const effectAllowed = effect === 'SENSITIVE_ARTIFACT'
    ? envelope.expectedEffect === effect && envelope.artifactPolicy.enabled
    : effectRank(effect) >= 0 && effectRank(effect) <= effectRank(envelope.expectedEffect);
  if (!effectAllowed) return freeze({ allowed: false, reasonCode: 'EFFECT_NOT_BOUND', effect });
  return freeze({ allowed: true, reasonCode: 'BOUND_OPERATION', effect });
}


function output(status, reasonCode, operationId, step, effect, validationRequired, observation = null) {
  const boundedObservation = typeof observation === 'string' && observation.length <= 128
    ? { trust: 'untrusted', summary: observation } : null;
  return freeze({
    status, reasonCode, operationId, step, effect,
    validationRequired: Boolean(validationRequired), observation: boundedObservation,
  });
}


async function selectedAdapter(active, dependencies, env) {
  if (dependencies.adapter) return dependencies.adapter;
  const factory = dependencies.adapterFactory ?? resolveBrowserAdapter;
  try {
    const detected = await factory({
      preference: env.OPS_BROWSER_ADAPTER ?? null,
      options: {
        allowedOrigins: [...active.envelope.serviceOrigins, ...active.envelope.authOrigins],
        artifactManager: dependencies.artifactManager ?? null,
      },
    });
    return detected?.state === 'ACTIVE' ? detected.adapter : null;
  } catch {
    return null;
  }
}


async function resolveWorkflowAdapter(request, dependencies, env) {
  const factory = dependencies.adapterFactory ?? resolveBrowserAdapter;
  try {
    return await factory({
      preference: env.OPS_BROWSER_ADAPTER ?? null,
      options: {
        allowedOrigins: [...request.envelope.serviceOrigins, ...request.envelope.authOrigins],
        artifactManager: dependencies.artifactManager ?? null,
      },
    });
  } catch {
    return null;
  }
}


function mutableWorkflow(effect) {
  return ['LOW_RISK_CHANGE', 'DISRUPTIVE_CHANGE', 'DESTRUCTIVE_CHANGE'].includes(effect);
}


function builtInReferenceName(reference) {
  if (typeof reference !== 'string' || !reference.startsWith('env:')) return null;
  const name = reference.slice(4);
  return /^OPS_BROWSER_VALUE_[A-Z0-9_]+$/u.test(name) ? name : null;
}


async function resolveProtectedReference(reference, dependencies, env, errorCode) {
  const envName = builtInReferenceName(reference);
  if (envName !== null) {
    const value = env[envName];
    if (typeof value !== 'string' || value.length < 1) {
      throw new BrowserRunnerError(`BROWSER_RUNNER_${errorCode}`);
    }
    return value;
  }
  if (typeof dependencies.referenceResolver === 'function') {
    const value = await dependencies.referenceResolver(reference);
    if (typeof value === 'string' && value.length > 0) return value;
  }
  throw new BrowserRunnerError(`BROWSER_RUNNER_${errorCode}`);
}


function effectiveWorkflowCapability(request, adapter, dependencies) {
  const capabilities = adapter?.capabilities ?? {};
  const effects = new Set(['SENSITIVE_READ']);
  if (request.envelope.actions.some((action) => ['navigate', 'fill', 'select', 'click'].includes(action))) {
    effects.add('INTERACTIVE_STATE');
  }
  if (request.envelope.expectedEffect === 'INTERACTIVE_STATE') effects.add('INTERACTIVE_STATE');
  if (mutableWorkflow(request.envelope.expectedEffect) && capabilities.popups === true) {
    effects.add(request.envelope.expectedEffect);
  }
  if (request.envelope.artifactPolicy.enabled && dependencies.artifactManager) {
    effects.add('SENSITIVE_ARTIFACT');
  }
  return Object.freeze({
    state: 'ACTIVE',
    reasonCode: 'CAPABILITY_ACTIVE',
    adapterId: 'protected-runner',
    routeClass: 'PROTECTED_RUNNER',
    settingsFingerprint: 'browser-runner-v1',
    descriptorId: 'protected-runner-v1',
    serverName: null,
    toolPrefix: null,
    effects: [...effects],
    enforcement: {
      preCall: capabilities.preCall === true,
      topLevelOrigin: capabilities.topLevelOrigin === true,
      redirects: capabilities.redirects === true,
      popups: capabilities.popups === true,
      artifacts: Boolean(request.envelope.artifactPolicy.enabled && dependencies.artifactManager),
    },
  });
}


async function runWorkflowSteps(adapter, steps, dependencies, env) {
  for (const step of steps) {
    let credential = null;
    try {
      if (['fill', 'select'].includes(step.step)) {
        credential = await resolveProtectedReference(
          step.valueRef, dependencies, env, 'CREDENTIAL_REFERENCE_UNRESOLVED',
        );
      }
      const method = adapter?.[step.step];
      if (typeof method !== 'function') throw new Error('ADAPTER_STEP_UNAVAILABLE');
      const result = await method.call(adapter, credential === null ? step : { ...step, credential });
      if (result?.status !== 'ok') throw new Error('ADAPTER_RESULT_INCONCLUSIVE');
    } finally {
      credential = null;
    }
  }
}


async function runWorkflowValidation(adapter, request, dependencies, env) {
  const validationSteps = request.validationSteps.slice(0, -1);
  for (const step of validationSteps) {
    let credential = null;
    try {
      if (['fill', 'select'].includes(step.step)) {
        credential = await resolveProtectedReference(
          step.valueRef, dependencies, env, 'CREDENTIAL_REFERENCE_UNRESOLVED',
        );
      }
      const method = adapter?.[step.step];
      if (typeof method !== 'function') throw new Error('ADAPTER_STEP_UNAVAILABLE');
      const result = await method.call(adapter, credential === null ? step : { ...step, credential });
      if (result?.status !== 'ok') throw new Error('ADAPTER_RESULT_INCONCLUSIVE');
    } finally {
      credential = null;
    }
  }
  const inspect = request.validationSteps.at(-1);
  const expected = await resolveProtectedReference(
    inspect.expectedRef, dependencies, env, 'VALIDATION_REFERENCE_UNRESOLVED',
  );
  if (typeof adapter?.verify !== 'function') throw new Error('ADAPTER_VERIFY_UNAVAILABLE');
  const result = await adapter.verify({ ...inspect, expected });
  if (result?.expectRef !== inspect.expectRef) throw new Error('VALIDATION_REFERENCE_MISMATCH');
  if (result?.status === 'met') return 'WORKFLOW_VALIDATED';
  if (result?.status === 'not-met') return 'WORKFLOW_NOT_APPLIED';
  throw new Error('ADAPTER_RESULT_INCONCLUSIVE');
}


function workflowOutput(status, reasonCode, operationId) {
  return freeze({
    status,
    reasonCode,
    operationId,
    step: 'workflow',
    effect: 'SENSITIVE_READ',
    validationRequired: false,
    observation: null,
  });
}


export async function executeBrowserWorkflow(request, dependencies = {}) {
  const env = dependencies.env ?? process.env;
  const now = dependencies.now ?? Date.now();
  const sessionId = request?.envelope?.sessionId;
  if (typeof sessionId !== 'string') {
    return workflowOutput('denied', 'SESSION_BINDING_MISSING', request?.operationId ?? null);
  }

  const detectedExecution = await resolveWorkflowAdapter(request, dependencies, env);
  if (!detectedExecution?.adapter || detectedExecution.state !== 'ACTIVE') {
    return workflowOutput('denied', 'CAPABILITY_UNAVAILABLE', request.operationId);
  }
  const effectiveCapability = effectiveWorkflowCapability(request, detectedExecution.adapter, dependencies);
  if (!activatePendingWorkflow({
    sessionId,
    operationId: request.operationId,
    invocationFingerprint: request.invocationFingerprint,
    effectiveCapability,
  }, env, now)) {
    return workflowOutput('denied', 'CAPABILITY_UNAVAILABLE', request.operationId);
  }

  let activated = true;
  let executionAmbiguous = false;
  let executionAdapter = detectedExecution.adapter;
  try {
    await executionAdapter.open?.();
    try {
      await runWorkflowSteps(executionAdapter, request.executionSteps, dependencies, env);
    } catch (error) {
      const effect = workflowStepEffect(request.executionSteps.find((step) =>
        !['inspect', 'navigate', 'fill', 'select'].includes(step.step)) ?? request.executionSteps.at(-1));
      executionAmbiguous = mutableWorkflow(effect);
      if (executionAmbiguous) {
        recordOutcomeUnknown(sessionId, request.operationId, {
          reasonCode: 'ADAPTER_FAILURE',
          action: request.executionSteps.find((step) => mutableWorkflow(workflowStepEffect(step)))?.step ?? request.executionSteps.at(-1).step,
          effect,
        }, env, now);
      } else {
        return workflowOutput('denied', 'WORKFLOW_NOT_APPLIED', request.operationId);
      }
    }
  } finally {
    await executionAdapter?.close?.();
    executionAdapter = null;
  }

  const detectedValidation = await resolveWorkflowAdapter(request, dependencies, env);
  if (!detectedValidation?.adapter || detectedValidation.state !== 'ACTIVE') {
    return workflowOutput('outcome-unknown', 'OUTCOME_UNKNOWN', request.operationId);
  }

  let validationAdapter = detectedValidation.adapter;
  try {
    await validationAdapter.open?.();
    const outcome = await runWorkflowValidation(validationAdapter, request, dependencies, env);
    if (outcome === 'WORKFLOW_VALIDATED') {
      if (executionAmbiguous) {
        reconcileOutcomeUnknown(sessionId, request.operationId, request.envelope.validationRef, 'applied', env, now);
      } else {
        completeIndependentValidation(sessionId, request.operationId, request.envelope.validationRef, env, now);
      }
      return workflowOutput('ok', 'WORKFLOW_VALIDATED', request.operationId);
    }
    if (executionAmbiguous) {
      reconcileOutcomeUnknown(sessionId, request.operationId, request.envelope.validationRef, 'not-applied', env, now);
    }
    return workflowOutput('ok', 'WORKFLOW_NOT_APPLIED', request.operationId);
  } catch {
    return workflowOutput('outcome-unknown', 'OUTCOME_UNKNOWN', request.operationId);
  } finally {
    await validationAdapter?.close?.();
    if (activated) invalidateOperation(sessionId, request.operationId, 'WORKFLOW_COMPLETE', env, now);
  }
}


async function invokeAdapter(adapter, request, credential) {
  await adapter.open?.();
  if (typeof adapter.execute === 'function') return adapter.execute({ ...request, credential });
  const method = adapter[request.step];
  if (typeof method !== 'function') throw new Error('ADAPTER_STEP_UNAVAILABLE');
  return method.call(adapter, { ...request, credential });
}


export async function executeRunnerStep(request, dependencies = {}) {
  const env = dependencies.env ?? process.env;
  const now = dependencies.now ?? Date.now();
  if (request.step === 'workflow') return executeBrowserWorkflow(request, dependencies);
  if (request.step === 'open') {
    if (dependencies.proof) writePendingOperation(request.envelope, dependencies.proof, env, now);
    const pending = readPendingOperation(
      request.envelope.sessionId, request.operationId, env, now,
    );
    if (!pending) {
      return output('denied', 'PENDING_APPROVAL_MISSING', request.operationId, 'open', request.envelope.expectedEffect, false);
    }
    return output('pending', 'PENDING_NATIVE_APPROVAL', request.operationId, 'open', request.envelope.expectedEffect, false);
  }

  const sessionId = dependencies.sessionId ?? env.OPS_BROWSER_SESSION_ID;
  if (typeof sessionId !== 'string') {
    return output('denied', 'SESSION_BINDING_MISSING', request.operationId, request.step, stepEffect(request), false);
  }
  const active = readActiveOperation(sessionId, request.operationId, env, now);
  if (!active) return output('denied', 'OPERATION_NOT_ACTIVE', request.operationId, request.step, stepEffect(request), false);
  if (active.outcome === 'APPLIED_CONFIRMED' && request.step !== 'close') {
    return output('denied', 'OPERATION_COMPLETE', request.operationId, request.step, stepEffect(request), false);
  }
  if (active.outcome === 'OUTCOME_UNKNOWN' && !['validate', 'close'].includes(request.step)) {
    return output('denied', 'OUTCOME_UNKNOWN', request.operationId, request.step, stepEffect(request), true);
  }
  if (request.step === 'close') {
    try {
      await dependencies.adapter?.close?.();
    } finally {
      invalidateOperation(sessionId, request.operationId, 'OPERATOR_CLOSED', env, now);
    }
    return output('closed', 'OPERATION_CLOSED', request.operationId, 'close', 'INTERACTIVE_STATE', false);
  }
  const authorization = authorizeRunnerStep(request, active.envelope, active.capability, now);
  if (!authorization.allowed) {
    return output('denied', authorization.reasonCode, request.operationId, request.step, authorization.effect, active.validationRequired);
  }

  let credential = null;
  if (request.valueRef !== null) {
    if (typeof dependencies.credentialResolver !== 'function') {
      return output('denied', 'CREDENTIAL_RESOLVER_UNAVAILABLE', request.operationId, request.step, authorization.effect, active.validationRequired);
    }
    credential = await dependencies.credentialResolver(request.valueRef);
    if (typeof credential !== 'string' || credential.length < 1) {
      return output('denied', 'CREDENTIAL_REFERENCE_UNRESOLVED', request.operationId, request.step, authorization.effect, active.validationRequired);
    }
  }

  if (request.step === 'validate') {
    if (typeof dependencies.postconditionValidator !== 'function') {
      return output('denied', 'INDEPENDENT_VALIDATOR_UNAVAILABLE', request.operationId, request.step, 'SENSITIVE_READ', true);
    }
    try {
      const observed = await dependencies.postconditionValidator({
        operationId: request.operationId,
        validationRef: request.expectRef,
        target: active.envelope.target,
        environment: active.envelope.environment,
      });
      if (observed?.status !== 'met'
          || observed.validationRef !== active.envelope.validationRef
          || request.expectRef !== active.envelope.validationRef) {
        return output('denied', 'VALIDATION_FAILED', request.operationId, request.step, 'SENSITIVE_READ', true);
      }
      if (active.outcome === 'OUTCOME_UNKNOWN') {
        if (!['applied', 'not-applied'].includes(observed.outcome)) {
          return output('denied', 'VALIDATION_FAILED', request.operationId, request.step, 'SENSITIVE_READ', true);
        }
        reconcileOutcomeUnknown(
          sessionId, request.operationId, request.expectRef, observed.outcome, env, now,
        );
        return output('ok', observed.outcome === 'applied'
          ? 'RECONCILED_APPLIED' : 'RECONCILED_NOT_APPLIED',
        request.operationId, request.step, 'SENSITIVE_READ', false);
      }
      completeIndependentValidation(sessionId, request.operationId, request.expectRef, env, now);
      return output('ok', 'VALIDATED', request.operationId, request.step, 'SENSITIVE_READ', false);
    } catch {
      return output('denied', 'VALIDATION_FAILED', request.operationId, request.step, 'SENSITIVE_READ', true);
    }
  }

  const adapter = await selectedAdapter(active, dependencies, env);
  if (!adapter) {
    return output('denied', 'CAPABILITY_UNAVAILABLE', request.operationId, request.step, stepEffect(request), active.validationRequired);
  }

  const callId = `runner-${randomUUID()}`;
  if (!stageBrowserCall(sessionId, request.operationId, {
    toolUseId: callId, action: request.step, effect: authorization.effect,
  }, env, now)) {
    return output('denied', 'CALL_BINDING_FAILED', request.operationId, request.step, authorization.effect, active.validationRequired);
  }
  try {
    const observed = await invokeAdapter(adapter, request, credential);
    if (observed?.status !== 'ok') throw new Error('ADAPTER_RESULT_INCONCLUSIVE');
    completeBrowserCall(sessionId, callId, env, now);
    const updated = readActiveOperation(sessionId, request.operationId, env, now);
    return output('ok', 'STEP_COMPLETED', request.operationId, request.step, authorization.effect, updated?.validationRequired, observed.observation);
  } catch {
    recordOutcomeUnknown(sessionId, request.operationId, {
      reasonCode: 'ADAPTER_FAILURE', action: request.step, effect: authorization.effect,
    }, env, now);
    return output('outcome-unknown', 'OUTCOME_UNKNOWN', request.operationId, request.step, authorization.effect, true);
  } finally {
    credential = null;
    await adapter.close?.();
  }
}


async function main() {
  try {
    const request = parseRunnerArgs(process.argv.slice(2));
    const result = request.step === 'workflow'
      ? await executeBrowserWorkflow(request)
      : await executeRunnerStep(request);
    process.stdout.write(`${JSON.stringify(result)}\n`);
    return ['ok', 'pending', 'closed'].includes(result.status) ? 0 : 2;
  } catch {
    process.stderr.write('Browser runner rejected the request.\n');
    return 2;
  }
}


if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await main();
}
