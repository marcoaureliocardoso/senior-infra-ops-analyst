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
  consumeOwnedOperation,
  ownedOperationCorrelation,
} from './browser-binding-store.mjs';
import {
  BrowserLifetimeError, createOperationClock, createOperationLifetime, hasOperationLifetime,
} from './browser-operation-lifetime.mjs';
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
const TRUSTED_REASON_CODES = new Set(['ADAPTER_CLOSE_FAILED']);
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
    if (step.valueClass === 'credential'
        && !opening.envelope.authOrigins.includes(step.origin)) {
      fail('WORKFLOW_CREDENTIAL_ORIGIN_NOT_BOUND');
    }
    if (step.valueClass === 'configuration'
        && !opening.envelope.serviceOrigins.includes(step.origin)) {
      fail('WORKFLOW_CONFIGURATION_ORIGIN_NOT_BOUND');
    }
    if (!opening.envelope.actions.includes(step.step)) fail('WORKFLOW_ACTION_NOT_BOUND');
  }
  for (const step of workflow.validationSteps) {
    if (['fill', 'select', 'click'].includes(step.step)
        && !opening.envelope.authOrigins.includes(step.origin)) {
      fail('WORKFLOW_VALIDATION_AUTH_ORIGIN_NOT_BOUND');
    }
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


function adapterOrigins(envelope) {
  return [...new Set([...envelope.serviceOrigins, ...envelope.authOrigins])];
}


async function selectedAdapter(active, dependencies, env, operationLifetime) {
  if (dependencies.adapter) return { state: 'ACTIVE', adapter: dependencies.adapter };
  const factory = dependencies.adapterFactory ?? resolveBrowserAdapter;
  try {
    const detected = await factory({
      preference: env.OPS_BROWSER_ADAPTER ?? null,
      options: {
        allowedOrigins: adapterOrigins(active.envelope),
        artifactManager: dependencies.artifactManager ?? null,
        operationLifetime,
      },
    });
    return detected;
  } catch {
    return null;
  }
}


async function resolveWorkflowAdapter(request, dependencies, env, operationLifetime) {
  const factory = dependencies.adapterFactory ?? resolveBrowserAdapter;
  try {
    return await factory({
      preference: env.OPS_BROWSER_ADAPTER ?? null,
      options: {
        allowedOrigins: adapterOrigins(request.envelope),
        artifactManager: dependencies.artifactManager ?? null,
        operationLifetime,
      },
    });
  } catch {
    return null;
  }
}


function mutableWorkflow(effect) {
  return ['LOW_RISK_CHANGE', 'DISRUPTIVE_CHANGE', 'DESTRUCTIVE_CHANGE'].includes(effect);
}


function possiblyStateChanging(effect) {
  return effect === 'INTERACTIVE_STATE' || mutableWorkflow(effect);
}


function successfulStepMayPersist(step, effect) {
  return mutableWorkflow(effect)
    || (effect === 'INTERACTIVE_STATE'
      && ['fill', 'select', 'click', 'submit'].includes(step.step));
}


function runnerErrorReason(error, fallback) {
  if (error instanceof BrowserLifetimeError) return error.code;
  if (error instanceof BrowserRunnerError && typeof error.code === 'string'
      && error.code.startsWith('BROWSER_RUNNER_')) {
    return error.code.slice('BROWSER_RUNNER_'.length);
  }
  if (typeof error?.code === 'string' && TRUSTED_REASON_CODES.has(error.code)) return error.code;
  if (typeof error?.message === 'string' && TRUSTED_REASON_CODES.has(error.message)) return error.message;
  return fallback;
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


function workflowStepsCapability(steps, expectedEffect, adapter, dependencies) {
  const capabilities = adapter?.capabilities ?? {};
  const effects = new Set(['SENSITIVE_READ']);
  for (const step of steps) {
    const effect = stepEffect(step);
    if (effect === 'INTERACTIVE_STATE') effects.add(effect);
    if (effect === 'SENSITIVE_ARTIFACT' && dependencies.artifactManager) effects.add(effect);
    if (mutableWorkflow(effect) && capabilities.popups === true) effects.add(effect);
  }
  if (expectedEffect === 'INTERACTIVE_STATE') effects.add('INTERACTIVE_STATE');
  if (mutableWorkflow(expectedEffect) && capabilities.popups === true) {
    effects.add(expectedEffect);
  }
  if (steps.some((step) => stepEffect(step) === 'SENSITIVE_ARTIFACT') && dependencies.artifactManager) {
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
      artifacts: Boolean(
        steps.some((step) => stepEffect(step) === 'SENSITIVE_ARTIFACT') && dependencies.artifactManager,
      ),
    },
  });
}


function effectiveWorkflowCapability(request, adapter, dependencies) {
  return workflowStepsCapability(
    request.executionSteps, request.envelope.expectedEffect, adapter, dependencies,
  );
}


function normalizedValidationStep(step) {
  if (['click', 'submit'].includes(step.step)) return freeze({ ...step, effect: 'INTERACTIVE_STATE' });
  return step;
}


function effectiveValidationCapability(request, adapter, dependencies) {
  return workflowStepsCapability(
    request.validationSteps.map((step) => normalizedValidationStep(step)),
    'INTERACTIVE_STATE',
    adapter,
    dependencies,
  );
}


function workflowCapabilityUsable(capability, steps, dependencies) {
  if (capability?.state !== 'ACTIVE' || capability?.routeClass !== 'PROTECTED_RUNNER') return false;
  if (capability.enforcement?.preCall !== true) return false;
  if (steps.some((step) => typeof step.origin === 'string')
      && (capability.enforcement?.topLevelOrigin !== true || capability.enforcement?.redirects !== true)) {
    return false;
  }
  if (steps.some((step) => ['navigate', 'fill', 'select', 'click', 'submit'].includes(step.step))
      && capability.enforcement?.popups !== true) {
    return false;
  }
  if (steps.some((step) => stepEffect(step) === 'SENSITIVE_ARTIFACT')
      && Boolean(dependencies.artifactManager)
      && capability.enforcement?.artifacts !== true) {
    return false;
  }
  return true;
}


function outcomeObservationForStep(step, effect = stepEffect(step)) {
  return freeze({ action: step.step, effect });
}


function authorizeLiveStep(request, envelope, capability, lifetime) {
  return authorizeRunnerStep(request, envelope, capability, lifetime.assertLive());
}


async function resolveLiveReference(reference, dependencies, env, code) {
  dependencies.lifetime.assertLive();
  const value = await resolveProtectedReference(reference, dependencies, env, code);
  dependencies.lifetime.assertLive();
  return value;
}


async function executeWorkflowStep(adapter, step, envelope, capability, dependencies, env) {
  const { lifetime, scope } = dependencies;
  let authorization;
  try { authorization = authorizeLiveStep(step, envelope, capability, lifetime); } catch (error) {
    return { type: 'denied', reasonCode: runnerErrorReason(error, 'OUTCOME_UNKNOWN'), effect: stepEffect(step), step };
  }
  if (!authorization.allowed) {
    return { type: 'denied', reasonCode: authorization.reasonCode, effect: authorization.effect, step };
  }
  let credential = null;
  let expected = null;
  let dispatched = false;
  try {
    if (['fill', 'select'].includes(step.step)) {
      credential = await resolveLiveReference(
        step.valueRef, dependencies, env, 'CREDENTIAL_REFERENCE_UNRESOLVED',
      );
    }
    if (step.step === 'inspect') {
      expected = await resolveLiveReference(
        step.expectedRef, dependencies, env, 'PRECONDITION_REFERENCE_UNRESOLVED',
      );
    }
    const method = adapter?.[step.step === 'inspect' ? 'verify' : step.step];
    if (typeof method !== 'function') throw new Error('ADAPTER_STEP_UNAVAILABLE');
    lifetime.assertLive();
    dispatched = true;
    if (successfulStepMayPersist(step, authorization.effect)) scope.possiblePersistence = true;
    const result = await method.call(adapter, step.step === 'inspect'
      ? { ...step, expected } : credential === null ? step : { ...step, credential });
    lifetime.assertLive();
    if (step.step === 'inspect') {
      if (result?.expectRef !== step.expectRef || result?.status !== 'met') {
        fail('PRECONDITION_NOT_MET');
      }
    } else if (result?.status !== 'ok') throw new Error('ADAPTER_RESULT_INCONCLUSIVE');
    return { type: 'ok' };
  } catch (error) {
    const reasonCode = runnerErrorReason(error, 'ADAPTER_FAILURE');
    if (error instanceof BrowserLifetimeError) {
      if (dispatched) scope.lateResult = true;
      return { type: dispatched ? 'failure' : 'denied', reasonCode,
        effect: authorization.effect, step, ambiguous: dispatched };
    }
    if (error instanceof BrowserRunnerError) {
      return { type: 'denied', reasonCode, effect: authorization.effect, step };
    }
    return {
      type: 'failure',
      reasonCode,
      effect: authorization.effect,
      step,
      ambiguous: dispatched && possiblyStateChanging(authorization.effect),
    };
  } finally {
    credential = null;
    expected = null;
  }
}


async function runWorkflowSteps(adapter, steps, dependencies, env) {
  let lastMutation = null;
  for (const step of steps) {
    const result = await executeWorkflowStep(
      adapter, step, dependencies.envelope, dependencies.capability, dependencies, env,
    );
    if (result.type === 'ok') {
      const effect = stepEffect(step);
      if (successfulStepMayPersist(step, effect)) {
        lastMutation = outcomeObservationForStep(step, effect);
      }
      continue;
    }
    if (lastMutation !== null) {
      return { type: 'needs-validation', reasonCode: result.reasonCode, outcomeObservation: lastMutation };
    }
    if (result.type === 'failure' && result.ambiguous) {
      return {
        type: 'needs-validation',
        reasonCode: result.reasonCode,
        outcomeObservation: outcomeObservationForStep(result.step, result.effect),
      };
    }
    if (result.type !== 'ok') {
      return result;
    }
  }
  return { type: 'ok', lastMutation };
}


async function runWorkflowValidation(adapter, request, dependencies, env) {
  const steps = request.validationSteps.map((step) => normalizedValidationStep(step));
  const validationSteps = steps.slice(0, -1);
  for (const step of validationSteps) {
    const result = await executeWorkflowStep(
      adapter, step, request.envelope, dependencies.capability, dependencies, env,
    );
    if (result.type !== 'ok') {
      return { outcome: 'OUTCOME_UNKNOWN', reasonCode: result.reasonCode };
    }
  }
  const inspect = steps.at(-1);
  const authorization = authorizeLiveStep(inspect, request.envelope, dependencies.capability, dependencies.lifetime);
  if (!authorization.allowed) return { outcome: 'OUTCOME_UNKNOWN', reasonCode: authorization.reasonCode };
  let expected;
  try {
    expected = await resolveLiveReference(
      inspect.expectedRef, dependencies, env, 'VALIDATION_REFERENCE_UNRESOLVED',
    );
  } catch (error) {
    return { outcome: 'OUTCOME_UNKNOWN', reasonCode: runnerErrorReason(error, 'OUTCOME_UNKNOWN') };
  }
  try {
    if (typeof adapter?.verify !== 'function') throw new Error('ADAPTER_VERIFY_UNAVAILABLE');
    dependencies.lifetime.assertLive();
    const result = await adapter.verify({ ...inspect, expected });
    try { dependencies.lifetime.assertLive(); } catch (error) {
      dependencies.scope.lateResult = true;
      throw error;
    }
    if (result?.expectRef !== inspect.expectRef) throw new Error('VALIDATION_REFERENCE_MISMATCH');
    if (result?.status === 'met') return { outcome: 'WORKFLOW_VALIDATED' };
    // A missing desired state does not prove that preceding effects were absent.
    if (result?.status === 'not-met') return { outcome: 'OUTCOME_UNKNOWN', reasonCode: 'POSTCONDITION_NOT_MET' };
  } catch (error) {
    return { outcome: 'OUTCOME_UNKNOWN', reasonCode: runnerErrorReason(error, 'OUTCOME_UNKNOWN') };
  }
  return { outcome: 'OUTCOME_UNKNOWN', reasonCode: 'OUTCOME_UNKNOWN' };
}


async function closeWorkflowAdapter(adapter) {
  try {
    await adapter?.close?.();
    return null;
  } catch (error) {
    return runnerErrorReason(error, 'ADAPTER_CLOSE_FAILED');
  }
}


function workflowOutput(status, reasonCode, request) {
  return freeze({
    status,
    reasonCode,
    operationId: request?.operationId ?? null,
    step: 'workflow',
    effect: request?.envelope?.expectedEffect ?? 'UNKNOWN',
    validationRequired: status === 'outcome-unknown',
    observation: null,
  });
}


function ownedGrant(entry) {
  return ownedOperationCorrelation(entry);
}


async function closeOwnedAdapter(adapter) {
  const reason = await closeWorkflowAdapter(adapter);
  if (reason) throw new BrowserRunnerError('BROWSER_RUNNER_' + reason);
}


async function executeBrowserWorkflowCore(request, dependencies, scope) {
  const env = dependencies.env ?? process.env;
  const now = scope.clock.readNow();
  const sessionId = request?.envelope?.sessionId;
  if (typeof sessionId !== 'string') return workflowOutput('denied', 'SESSION_BINDING_MISSING', request);
  const active = readActiveOperation(sessionId, request.operationId, env, now);
  if (active?.outcome === 'OUTCOME_UNKNOWN') return workflowOutput('outcome-unknown', 'OUTCOME_UNKNOWN', request);
  if (active?.outcome === 'APPLIED_CONFIRMED') return workflowOutput('denied', 'OPERATION_COMPLETE', request);
  const pending = readPendingOperation(sessionId, request.operationId, env, now);
  if (!pending) return workflowOutput('denied', 'OPERATION_NOT_ACTIVE', request);
  if (pending.invocationFingerprint !== request.invocationFingerprint) {
    return workflowOutput('denied', 'APPROVAL_BINDING_INVALID', request);
  }
  scope.owned = ownedGrant(pending);
  const lifetime = createOperationLifetime(pending.envelope, scope.clock);
  scope.lifetime = lifetime;
  const bound = { ...request, envelope: pending.envelope };
  const shared = { ...dependencies, envelope: pending.envelope, lifetime, scope };
  let executionAdapter = null;
  let execution;
  let executionAmbiguous = false;
  try {
    lifetime.assertLive();
    const detected = await resolveWorkflowAdapter(bound, dependencies, env, lifetime);
    executionAdapter = detected?.adapter ?? null;
    lifetime.assertLive();
    if (!executionAdapter || detected.state !== 'ACTIVE') {
      return workflowOutput('denied', 'CAPABILITY_UNAVAILABLE', request);
    }
    if (!hasOperationLifetime(executionAdapter, lifetime)) throw new BrowserLifetimeError('OPERATION_LIFETIME_UNPROVEN');
    const capability = effectiveWorkflowCapability(bound, executionAdapter, dependencies);
    if (!activatePendingWorkflow({
      sessionId, operationId: request.operationId, invocationFingerprint: request.invocationFingerprint,
      effectiveCapability: capability,
      ownedApproval: scope.owned,
    }, env, lifetime.assertLive())) return workflowOutput('denied', 'CAPABILITY_UNAVAILABLE', request);
    try {
      lifetime.assertLive();
      await executionAdapter.open?.();
      lifetime.assertLive();
    } catch (error) {
      if (error instanceof BrowserLifetimeError) throw error;
      return workflowOutput('denied', runnerErrorReason(error, 'WORKFLOW_NOT_APPLIED'), request);
    }
    execution = await runWorkflowSteps(executionAdapter, request.executionSteps, { ...shared, capability }, env);
    if (execution.type === 'needs-validation') {
      lifetime.assertLive();
      executionAmbiguous = true;
      if (!recordOutcomeUnknown(sessionId, request.operationId, {
        reasonCode: execution.reasonCode, action: execution.outcomeObservation.action,
        effect: execution.outcomeObservation.effect,
      }, env, lifetime.assertLive(), scope.owned)) throw new BrowserRunnerError('BROWSER_RUNNER_WORKFLOW_COMPLETION_FAILED');
    }
  } finally {
    await closeOwnedAdapter(executionAdapter);
  }
  lifetime.assertLive();
  if (execution.type === 'denied') return workflowOutput('denied', execution.reasonCode, request);
  if (execution.type === 'failure') return workflowOutput('denied', 'WORKFLOW_NOT_APPLIED', request);
  scope.validationStarted = true;
  let validationAdapter = null;
  let validation;
  try {
    lifetime.assertLive();
    const detected = await resolveWorkflowAdapter(bound, dependencies, env, lifetime);
    validationAdapter = detected?.adapter ?? null;
    lifetime.assertLive();
    if (!validationAdapter || detected.state !== 'ACTIVE') return workflowOutput('outcome-unknown', 'OUTCOME_UNKNOWN', request);
    if (!hasOperationLifetime(validationAdapter, lifetime)) throw new BrowserLifetimeError('OPERATION_LIFETIME_UNPROVEN');
    const capability = effectiveValidationCapability(bound, validationAdapter, dependencies);
    if (!workflowCapabilityUsable(capability, request.validationSteps.map(normalizedValidationStep), dependencies)) {
      return workflowOutput('outcome-unknown', 'OUTCOME_UNKNOWN', request);
    }
    lifetime.assertLive();
    await validationAdapter.open?.();
    lifetime.assertLive();
    validation = await runWorkflowValidation(validationAdapter, bound, { ...shared, capability }, env);
  } finally {
    await closeOwnedAdapter(validationAdapter);
  }
  lifetime.assertLive();
  if (validation.outcome === 'WORKFLOW_VALIDATED') {
    const completed = executionAmbiguous
      ? reconcileOutcomeUnknown(sessionId, request.operationId, pending.envelope.validationRef, 'applied', env, lifetime.assertLive(), scope.owned)
      : completeIndependentValidation(sessionId, request.operationId, pending.envelope.validationRef, env, lifetime.assertLive(), scope.owned);
    if (!completed) return workflowOutput('outcome-unknown', 'WORKFLOW_COMPLETION_FAILED', request);
    lifetime.assertLive();
    return workflowOutput('ok', 'WORKFLOW_VALIDATED', request);
  }
  return workflowOutput('outcome-unknown', validation.reasonCode ?? 'OUTCOME_UNKNOWN', request);
}


export async function executeBrowserWorkflow(request, dependencies = {}) {
  const env = dependencies.env ?? process.env;
  const scope = { clock: null, owned: null, lifetime: null, possiblePersistence: false, lateResult: false, validationStarted: false };
  let result;
  let cleanupFailed = false;
  try {
    scope.clock = createOperationClock(dependencies.now);
    result = await executeBrowserWorkflowCore(request, dependencies, scope);
  } catch (error) {
    const status = error instanceof BrowserLifetimeError
      && !scope.possiblePersistence && !scope.lateResult && !scope.validationStarted ? 'denied' : 'outcome-unknown';
    result = workflowOutput(status, runnerErrorReason(error, 'OUTCOME_UNKNOWN'), request);
  } finally {
    if (scope.owned) {
      try { if (!consumeOwnedOperation(scope.owned, env)) cleanupFailed = true; }
      catch { cleanupFailed = true; }
    }
  }
  if (dependencies.artifactManager && typeof dependencies.artifactManager.close === 'function') {
    try { await dependencies.artifactManager.close({ retain: false, outcome: result.reasonCode }); }
    catch { cleanupFailed = true; }
  }
  if (cleanupFailed) return workflowOutput('outcome-unknown', 'WORKFLOW_CLEANUP_FAILED', request);
  if (result.status === 'ok' && scope.lifetime) {
    try { scope.lifetime.assertLive(); }
    catch (error) { return workflowOutput('outcome-unknown', runnerErrorReason(error, 'OUTCOME_UNKNOWN'), request); }
  }
  return result;
}


export async function executeRunnerStep(request, dependencies = {}) {
  if (request.step === 'workflow') return executeBrowserWorkflow(request, dependencies);
  const env = dependencies.env ?? process.env;
  let clock;
  try { clock = createOperationClock(dependencies.now); clock.readNow(); }
  catch { return output('denied', 'OPERATION_CLOCK_UNPROVEN', request.operationId, request.step, stepEffect(request), false); }
  if (request.step === 'open') {
    const now = clock.readNow();
    if (dependencies.proof) writePendingOperation(request.envelope, dependencies.proof, env, now);
    const pending = readPendingOperation(request.envelope.sessionId, request.operationId, env, now);
    return output(pending ? 'pending' : 'denied', pending ? 'PENDING_NATIVE_APPROVAL' : 'PENDING_APPROVAL_MISSING',
      request.operationId, 'open', request.envelope.expectedEffect, false);
  }
  const sessionId = dependencies.sessionId ?? env.OPS_BROWSER_SESSION_ID;
  if (typeof sessionId !== 'string') return output('denied', 'SESSION_BINDING_MISSING', request.operationId, request.step, stepEffect(request), false);
  let active = null;
  let lifetime = null;
  let adapter = null;
  let credential = null;
  let dispatched = false;
  let consume = false;
  let result;
  let cleanupFailed = false;
  let effect = stepEffect(request);
  try {
    active = readActiveOperation(sessionId, request.operationId, env, clock.readNow());
    if (!active) {
      if (request.step === 'close') await dependencies.adapter?.close?.();
      return output('denied', 'OPERATION_NOT_ACTIVE', request.operationId, request.step, effect, false);
    }
    lifetime = createOperationLifetime(active.envelope, clock);
    if (active.invocationFingerprint !== null) {
      consume = true;
      result = output('denied', 'WORKFLOW_BINDING_QUARANTINED', request.operationId, request.step, effect, true);
    } else if (request.step === 'close') {
      consume = true;
      await dependencies.adapter?.close?.();
      result = output('closed', 'OPERATION_CLOSED', request.operationId, 'close', 'INTERACTIVE_STATE', false);
    } else {
      if (active.outcome === 'APPLIED_CONFIRMED') return output('denied', 'OPERATION_COMPLETE', request.operationId, request.step, effect, false);
      if (active.outcome === 'OUTCOME_UNKNOWN' && request.step !== 'validate') {
        return output('denied', 'OUTCOME_UNKNOWN', request.operationId, request.step, effect, true);
      }
      const authorization = authorizeLiveStep(request, active.envelope, active.capability, lifetime);
      effect = authorization.effect;
      if (!authorization.allowed) return output('denied', authorization.reasonCode, request.operationId, request.step, effect, active.validationRequired);
      if (request.valueRef !== null) {
        if (typeof dependencies.credentialResolver !== 'function') return output('denied', 'CREDENTIAL_RESOLVER_UNAVAILABLE', request.operationId, request.step, effect, active.validationRequired);
        lifetime.assertLive();
        credential = await dependencies.credentialResolver(request.valueRef);
        lifetime.assertLive();
        if (typeof credential !== 'string' || credential.length < 1) return output('denied', 'CREDENTIAL_REFERENCE_UNRESOLVED', request.operationId, request.step, effect, active.validationRequired);
      }
      if (request.step === 'validate') {
        if (typeof dependencies.postconditionValidator !== 'function') return output('denied', 'INDEPENDENT_VALIDATOR_UNAVAILABLE', request.operationId, request.step, effect, true);
        lifetime.assertLive();
        dispatched = true;
        const observed = await dependencies.postconditionValidator({
          operationId: request.operationId, validationRef: request.expectRef,
          target: active.envelope.target, environment: active.envelope.environment,
        });
        lifetime.assertLive();
        if (observed?.status !== 'met' || observed.validationRef !== active.envelope.validationRef
            || request.expectRef !== active.envelope.validationRef) return output('denied', 'VALIDATION_FAILED', request.operationId, request.step, effect, true);
        let completed;
        let reason = 'VALIDATED';
        if (active.outcome === 'OUTCOME_UNKNOWN') {
          if (!['applied', 'not-applied'].includes(observed.outcome)) return output('denied', 'VALIDATION_FAILED', request.operationId, request.step, effect, true);
          completed = reconcileOutcomeUnknown(sessionId, request.operationId, request.expectRef, observed.outcome, env, lifetime.assertLive(), ownedGrant(active));
          reason = observed.outcome === 'applied' ? 'RECONCILED_APPLIED' : 'RECONCILED_NOT_APPLIED';
        } else {
          completed = completeIndependentValidation(sessionId, request.operationId, request.expectRef, env, lifetime.assertLive(), ownedGrant(active));
        }
        if (!completed) return output('outcome-unknown', 'WORKFLOW_COMPLETION_FAILED', request.operationId, request.step, effect, true);
        lifetime.assertLive();
        result = output('ok', reason, request.operationId, request.step, effect, false);
      } else {
        lifetime.assertLive();
        const detected = await selectedAdapter(active, dependencies, env, lifetime);
        adapter = detected?.adapter ?? null;
        lifetime.assertLive();
        if (!adapter || detected.state !== 'ACTIVE') return output('denied', 'CAPABILITY_UNAVAILABLE', request.operationId, request.step, effect, active.validationRequired);
        if (!hasOperationLifetime(adapter, lifetime)) throw new BrowserLifetimeError('OPERATION_LIFETIME_UNPROVEN');
        const callId = 'runner-' + randomUUID();
        if (!stageBrowserCall(sessionId, request.operationId, { toolUseId: callId, action: request.step, effect }, env, lifetime.assertLive(), ownedGrant(active))) {
          return output('denied', 'CALL_BINDING_FAILED', request.operationId, request.step, effect, active.validationRequired);
        }
        lifetime.assertLive();
        await adapter.open?.();
        lifetime.assertLive();
        const method = typeof adapter.execute === 'function' ? adapter.execute : adapter[request.step];
        if (typeof method !== 'function') throw new Error('ADAPTER_STEP_UNAVAILABLE');
        lifetime.assertLive();
        dispatched = true;
        const observed = await method.call(adapter, { ...request, credential });
        lifetime.assertLive();
        if (observed?.status !== 'ok') throw new Error('ADAPTER_RESULT_INCONCLUSIVE');
        if (!completeBrowserCall(sessionId, callId, env, lifetime.assertLive(), ownedGrant(active))) {
          consume = true;
          result = output('outcome-unknown', 'WORKFLOW_COMPLETION_FAILED', request.operationId, request.step, effect, true);
        } else {
          const updated = readActiveOperation(sessionId, request.operationId, env, lifetime.assertLive());
          result = output('ok', 'STEP_COMPLETED', request.operationId, request.step, effect, updated?.validationRequired, observed.observation);
        }
      }
    }
  } catch (error) {
    if (error instanceof BrowserLifetimeError) {
      consume = active !== null;
      result = output(dispatched || active?.validationRequired ? 'outcome-unknown' : 'denied',
        error.code, request.operationId, request.step, effect, dispatched || active?.validationRequired);
    } else {
      if (active && lifetime && request.step !== 'validate') {
        try {
          if (!recordOutcomeUnknown(sessionId, request.operationId, {
            reasonCode: 'ADAPTER_FAILURE', action: request.step, effect,
          }, env, lifetime.assertLive(), ownedGrant(active))) consume = true;
        } catch { consume = true; }
      }
      result = output('outcome-unknown', runnerErrorReason(error, request.step === 'validate' ? 'VALIDATION_FAILED' : 'OUTCOME_UNKNOWN'),
        request.operationId, request.step, effect, true);
    }
  } finally {
    credential = null;
    try { await closeOwnedAdapter(adapter); } catch { cleanupFailed = true; }
    if (cleanupFailed) consume = active !== null;
    if (consume && active) {
      try { if (!consumeOwnedOperation(ownedGrant(active), env)) cleanupFailed = true; }
      catch { cleanupFailed = true; }
    }
    if (cleanupFailed) return output('outcome-unknown', 'WORKFLOW_CLEANUP_FAILED', request.operationId, request.step, effect, true);
  }
  if (result?.status === 'ok') {
    try { lifetime.assertLive(); }
    catch (error) {
      try { if (!consumeOwnedOperation(ownedGrant(active), env)) cleanupFailed = true; } catch { cleanupFailed = true; }
      return output('outcome-unknown', cleanupFailed ? 'WORKFLOW_CLEANUP_FAILED' : runnerErrorReason(error, 'OUTCOME_UNKNOWN'),
        request.operationId, request.step, effect, true);
    }
  }
  return result;
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
