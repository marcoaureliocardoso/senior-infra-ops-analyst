import { createHash, randomBytes } from 'node:crypto';
import {
  chmodSync, existsSync, lstatSync, mkdirSync, readFileSync, renameSync, rmdirSync,
  writeFileSync,
} from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { operationFingerprint, parseOperationEnvelope } from './browser-contract.mjs';
import { BrowserLifetimeError } from './browser-operation-lifetime.mjs';


const VERSION = 1;
const MAX_ENTRIES = 16;
const MAX_STATE_BYTES = 128 * 1024;
const LOCK_ATTEMPTS = 400;
const LOCK_WAIT_MS = 5;
const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$/u;
const INVOCATION_FINGERPRINT = /^[a-f0-9]{64}$/u;
const WORKFLOW_APPROVAL_MARKER = 'PENDING_NATIVE_APPROVAL';
const EFFECTS = new Set([
  'PUBLIC_READ', 'SENSITIVE_READ', 'INTERACTIVE_STATE', 'LOW_RISK_CHANGE',
  'DISRUPTIVE_CHANGE', 'DESTRUCTIVE_CHANGE', 'SENSITIVE_ARTIFACT',
]);
const CAPABILITY_FIELDS = Object.freeze([
  'state', 'reasonCode', 'adapterId', 'routeClass', 'settingsFingerprint',
  'descriptorId', 'serverName', 'toolPrefix', 'effects', 'enforcement',
]);
const ENFORCEMENT_FIELDS = Object.freeze([
  'preCall', 'topLevelOrigin', 'redirects', 'popups', 'artifacts',
]);


function bounded(value, code) {
  if (typeof value !== 'string' || !IDENTIFIER.test(value)) throw new Error(code);
  return value;
}


function stateDirectory(env) {
  return path.resolve(env.OPS_BROWSER_STATE_DIR ?? path.join(
    os.homedir(), '.claude', 'senior-infra-ops-analyst', 'browser-operation-state',
  ));
}


export function resolveBrowserStateDirectory(env = process.env) {
  return stateDirectory(env);
}


function statePath(sessionId, env) {
  const name = createHash('sha256').update(bounded(sessionId, 'INVALID_SESSION'), 'utf8').digest('hex');
  return path.join(stateDirectory(env), `${name}.json`);
}


function emptyState() {
  return { version: VERSION, pending: [], active: [], calls: [] };
}


function clone(value) {
  return structuredClone(value);
}


export function ownedOperationCorrelation(entry) {
  return Object.freeze({
    sessionId: entry.sessionId, operationId: entry.operationId, toolUseId: entry.toolUseId,
    invocationFingerprint: entry.invocationFingerprint, expiresAt: entry.expiresAt,
  });
}


function matchesOwnedGrant(entry, owner) {
  if (owner === undefined) return true;
  return Boolean(owner && typeof owner === 'object' && !Array.isArray(owner)
    && entry.sessionId === owner.sessionId && entry.operationId === owner.operationId
    && entry.toolUseId === owner.toolUseId && entry.invocationFingerprint === owner.invocationFingerprint
    && entry.expiresAt === owner.expiresAt);
}


function matchesCallGrant(call, operation) {
  return call.approvalToolUseId === operation.toolUseId
    && call.sessionId === operation.sessionId && call.operationId === operation.operationId
    && call.expiresAt === operation.expiresAt;
}


function validateStateEntry(entry, kind) {
  if (!entry || typeof entry !== 'object' || Array.isArray(entry)) throw new Error('INVALID_BROWSER_STATE');
  bounded(entry.sessionId, 'INVALID_BROWSER_STATE');
  bounded(entry.operationId, 'INVALID_BROWSER_STATE');
  if (!Number.isSafeInteger(entry.expiresAt) || entry.expiresAt <= 0) throw new Error('INVALID_BROWSER_STATE');
  bounded(entry.toolUseId, 'INVALID_BROWSER_STATE');
  if (kind === 'operation') {
    if (!entry.envelope || entry.envelope.expiresAt !== entry.expiresAt
        || (entry.invocationFingerprint !== null
          && !INVOCATION_FINGERPRINT.test(entry.invocationFingerprint))) {
      throw new Error('INVALID_BROWSER_STATE');
    }
  } else if (entry.approvalToolUseId !== undefined) {
    bounded(entry.approvalToolUseId, 'INVALID_BROWSER_STATE');
  }
  return entry;
}


function readRawState(sessionId, env) {
  const target = statePath(sessionId, env);
  if (!existsSync(target)) return emptyState();
  const info = lstatSync(target);
  if (!info.isFile() || info.isSymbolicLink() || info.size > MAX_STATE_BYTES) {
    throw new Error('UNSAFE_STATE_FILE');
  }
  const parsed = JSON.parse(readFileSync(target, 'utf8'));
  if (parsed?.version !== VERSION || !Array.isArray(parsed.pending)
      || !Array.isArray(parsed.active) || !Array.isArray(parsed.calls)
      || parsed.pending.length > MAX_ENTRIES || parsed.active.length > MAX_ENTRIES
      || parsed.calls.length > MAX_ENTRIES) throw new Error('INVALID_BROWSER_STATE');
  const state = {
    version: VERSION,
    pending: parsed.pending.map((entry) => validateStateEntry(entry, 'operation')),
    active: parsed.active.map((entry) => validateStateEntry(entry, 'operation')),
    calls: parsed.calls.map((entry) => validateStateEntry(entry, 'call')),
  };
  if ([...state.pending, ...state.active, ...state.calls].some((entry) => entry.sessionId !== sessionId)) {
    throw new Error('INVALID_BROWSER_STATE');
  }
  return state;
}


function readState(sessionId, env, now) {
  const state = readRawState(sessionId, env);
  for (const kind of ['pending', 'active', 'calls']) {
    state[kind] = state[kind].filter(({ expiresAt }) => expiresAt > now);
  }
  return state;
}


function atomicWrite(target, state) {
  const serialized = `${JSON.stringify(state)}\n`;
  if (Buffer.byteLength(serialized, 'utf8') > MAX_STATE_BYTES) throw new Error('BROWSER_STATE_TOO_LARGE');
  const temporary = `${target}.${process.pid}.${randomBytes(8).toString('hex')}.tmp`;
  writeFileSync(temporary, serialized, { encoding: 'utf8', mode: 0o600, flag: 'wx' });
  chmodSync(temporary, 0o600);
  renameSync(temporary, target);
}


function waitForLock() {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, LOCK_WAIT_MS);
}


function withLock(sessionId, env, operation) {
  const directory = stateDirectory(env);
  if (!existsSync(directory)) mkdirSync(directory, { recursive: true, mode: 0o700 });
  const info = lstatSync(directory);
  if (!info.isDirectory() || info.isSymbolicLink()) throw new Error('UNSAFE_STATE_DIRECTORY');
  chmodSync(directory, 0o700);
  const target = statePath(sessionId, env);
  const lock = `${target}.lock`;
  let acquired = false;
  for (let attempt = 0; attempt < LOCK_ATTEMPTS; attempt += 1) {
    try {
      mkdirSync(lock, { mode: 0o700 });
      acquired = true;
      break;
    } catch (error) {
      /* node:coverage disable */
      if (error?.code !== 'EEXIST') throw error;
      /* node:coverage enable */
      waitForLock();
    }
  }
  if (!acquired) throw new Error('BROWSER_STATE_LOCK_UNAVAILABLE');
  try {
    return operation(target);
  } finally {
    rmdirSync(lock);
  }
}


function pushBounded(entries, entry) {
  entries.push(entry);
  if (entries.length > MAX_ENTRIES) entries.shift();
}


function normalizedProof(proof) {
  const permissionModes = Array.isArray(proof?.permissionModes)
    ? [...new Set(proof.permissionModes)] : [];
  if (permissionModes.length < 1 || permissionModes.length > 6
      || permissionModes.some((mode) => typeof mode !== 'string' || mode.length > 64)) {
    throw new Error('INVALID_BROWSER_PROOF');
  }
  if (!proof.capability || typeof proof.capability !== 'object' || Array.isArray(proof.capability)) {
    throw new Error('INVALID_BROWSER_PROOF');
  }
  const invocationFingerprint = proof.invocationFingerprint ?? null;
  if (invocationFingerprint !== null
      && (typeof invocationFingerprint !== 'string' || !INVOCATION_FINGERPRINT.test(invocationFingerprint))) {
    throw new Error('INVALID_BROWSER_PROOF');
  }
  return {
    toolUseId: bounded(proof.toolUseId, 'INVALID_BROWSER_PROOF'),
    adapterId: bounded(proof.adapterId, 'INVALID_BROWSER_PROOF'),
    routeClass: bounded(proof.routeClass, 'INVALID_BROWSER_PROOF'),
    settingsFingerprint: bounded(proof.settingsFingerprint, 'INVALID_BROWSER_PROOF'),
    permissionModes,
    invocationFingerprint,
    capability: clone(proof.capability),
  };
}


function exactDataFields(value, fields) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  if (![Object.prototype, null].includes(Object.getPrototypeOf(value))) return false;
  const descriptors = Object.getOwnPropertyDescriptors(value);
  const keys = Reflect.ownKeys(value);
  return keys.length === fields.length
    && fields.every((field) => Object.hasOwn(descriptors, field)
      && Object.hasOwn(descriptors[field], 'value'));
}


function boundedValue(value) {
  return typeof value === 'string' && IDENTIFIER.test(value);
}


function workflowApprovalMarker(capability) {
  return exactDataFields(capability, ['state']) && capability.state === WORKFLOW_APPROVAL_MARKER;
}


function workflowRequiredEffects(envelope) {
  const required = new Set(['SENSITIVE_READ', envelope.expectedEffect]);
  if (envelope.actions.some((action) => ['navigate', 'fill', 'select', 'click'].includes(action))) {
    required.add('INTERACTIVE_STATE');
  }
  if (envelope.artifactPolicy.enabled) required.add('SENSITIVE_ARTIFACT');
  return required;
}


function effectiveWorkflowCapability(value, pending) {
  if (!exactDataFields(value, CAPABILITY_FIELDS)
      || !exactDataFields(value.enforcement, ENFORCEMENT_FIELDS)
      || value.state !== 'ACTIVE' || value.reasonCode !== 'CAPABILITY_ACTIVE'
      || value.routeClass !== 'PROTECTED_RUNNER'
      || value.adapterId !== pending.adapterId
      || value.routeClass !== pending.routeClass
      || value.settingsFingerprint !== pending.settingsFingerprint
      || value.descriptorId !== 'protected-runner-v1'
      || value.serverName !== null || value.toolPrefix !== null
      || !boundedValue(value.adapterId) || !boundedValue(value.settingsFingerprint)
      || !boundedValue(value.descriptorId)
      || !Array.isArray(value.effects) || value.effects.length < 1
      || value.effects.length > EFFECTS.size
      || new Set(value.effects).size !== value.effects.length
      || value.effects.some((effect) => !EFFECTS.has(effect))
      || ENFORCEMENT_FIELDS.some((field) => typeof value.enforcement[field] !== 'boolean')) {
    return null;
  }
  const requiredEffects = workflowRequiredEffects(pending.envelope);
  if ([...requiredEffects].some((effect) => !value.effects.includes(effect))) return null;
  if (value.enforcement.preCall !== true
      || value.enforcement.topLevelOrigin !== true
      || value.enforcement.redirects !== true
      || value.enforcement.popups !== true
      || (pending.envelope.artifactPolicy.enabled && value.enforcement.artifacts !== true)) {
    return null;
  }
  return clone(value);
}


export function writePendingOperation(envelopeValue, proofValue, env = process.env, now = Date.now()) {
  const envelope = parseOperationEnvelope(envelopeValue, now);
  const proof = normalizedProof(proofValue);
  if (proof.invocationFingerprint !== null && !workflowApprovalMarker(proof.capability)) {
    throw new Error('INVALID_BROWSER_PROOF');
  }
  return withLock(envelope.sessionId, env, (target) => {
    const state = readState(envelope.sessionId, env, now);
    state.pending = state.pending.filter(({ operationId, toolUseId }) =>
      operationId !== envelope.operationId && toolUseId !== proof.toolUseId);
    pushBounded(state.pending, {
      sessionId: envelope.sessionId,
      operationId: envelope.operationId,
      role: envelope.role,
      envelope: clone(envelope),
      operationFingerprint: operationFingerprint(envelope),
      ...proof,
      expiresAt: envelope.expiresAt,
    });
    atomicWrite(target, state);
    return true;
  });
}


export function activateOperation(correlation, env = process.env, now = Date.now()) {
  const sessionId = bounded(correlation?.sessionId, 'INVALID_BROWSER_CORRELATION');
  const operationId = bounded(correlation?.operationId, 'INVALID_BROWSER_CORRELATION');
  const toolUseId = bounded(correlation?.toolUseId, 'INVALID_BROWSER_CORRELATION');
  return withLock(sessionId, env, (target) => {
    const state = readState(sessionId, env, now);
    const index = state.pending.findIndex((entry) =>
      entry.operationId === operationId && entry.toolUseId === toolUseId);
    if (index < 0) return false;
    const [pending] = state.pending.splice(index, 1);
    state.active = state.active.filter((entry) => entry.operationId !== operationId);
    pushBounded(state.active, {
      ...pending,
      active: true,
      outcome: 'READY',
      validationRequired: false,
    });
    atomicWrite(target, state);
    return true;
  });
}


export function activatePendingWorkflow(correlation, env = process.env, now = Date.now()) {
  const sessionId = bounded(correlation?.sessionId, 'INVALID_BROWSER_CORRELATION');
  const operationId = bounded(correlation?.operationId, 'INVALID_BROWSER_CORRELATION');
  const invocationFingerprint = correlation?.invocationFingerprint;
  if (typeof invocationFingerprint !== 'string' || !INVOCATION_FINGERPRINT.test(invocationFingerprint)) {
    throw new Error('INVALID_BROWSER_CORRELATION');
  }
  return withLock(sessionId, env, (target) => {
    const state = readState(sessionId, env, now);
    const index = state.pending.findIndex((entry) =>
      entry.operationId === operationId
      && entry.invocationFingerprint === invocationFingerprint
      && entry.permissionModes.length === 1
      && entry.permissionModes[0] === entry.envelope.permissionModeAtApproval);
    if (index < 0) return false;
    const pending = state.pending[index];
    if (!matchesOwnedGrant(pending, correlation.ownedApproval)) return false;
    if (!workflowApprovalMarker(pending.capability)) return false;
    const effectiveCapability = effectiveWorkflowCapability(correlation?.effectiveCapability, pending);
    if (!effectiveCapability) return false;
    state.pending.splice(index, 1);
    state.active = state.active.filter((entry) => entry.operationId !== operationId);
    pushBounded(state.active, {
      ...pending,
      capability: effectiveCapability,
      active: true,
      outcome: 'READY',
      validationRequired: false,
    });
    atomicWrite(target, state);
    return true;
  });
}


export function readActiveOperation(sessionId, operationId, env = process.env, now = Date.now()) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const boundedOperation = bounded(operationId, 'INVALID_OPERATION');
  const state = readState(boundedSession, env, now);
  const entry = state.active.find((candidate) => candidate.operationId === boundedOperation);
  return entry ? Object.freeze(clone(entry)) : null;
}


export function readPendingOperation(sessionId, operationId, env = process.env, now = Date.now()) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const boundedOperation = bounded(operationId, 'INVALID_OPERATION');
  const state = readState(boundedSession, env, now);
  const entry = state.pending.find((candidate) => candidate.operationId === boundedOperation);
  return entry ? Object.freeze(clone(entry)) : null;
}


export function readSingleActiveOperation(sessionId, env = process.env, now = Date.now()) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const state = readState(boundedSession, env, now);
  if (state.active.length !== 1) return null;
  return Object.freeze(clone(state.active[0]));
}


export function stageBrowserCall(sessionId, operationId, call, env = process.env, now = Date.now(), owner) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const boundedOperation = bounded(operationId, 'INVALID_OPERATION');
  const toolUseId = bounded(call?.toolUseId, 'INVALID_BROWSER_CALL');
  const action = bounded(call?.action, 'INVALID_BROWSER_CALL');
  const effect = bounded(call?.effect, 'INVALID_BROWSER_CALL');
  return withLock(boundedSession, env, (target) => {
    const state = readState(boundedSession, env, now);
    const operation = state.active.find((entry) => entry.operationId === boundedOperation);
    if (!operation || !matchesOwnedGrant(operation, owner) || operation.outcome !== 'READY') return false;
    state.calls = state.calls.filter((entry) => entry.toolUseId !== toolUseId);
    pushBounded(state.calls, {
      sessionId: boundedSession,
      operationId: boundedOperation,
      toolUseId,
      approvalToolUseId: operation.toolUseId,
      action,
      effect,
      expiresAt: operation.expiresAt,
    });
    atomicWrite(target, state);
    return true;
  });
}


export function completeBrowserCall(sessionId, toolUseId, env = process.env, now = Date.now(), owner) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const boundedToolUse = bounded(toolUseId, 'INVALID_BROWSER_CALL');
  return withLock(boundedSession, env, (target) => {
    const state = readState(boundedSession, env, now);
    const index = state.calls.findIndex((entry) => entry.toolUseId === boundedToolUse);
    if (index < 0) return false;
    const call = state.calls[index];
    const operation = state.active.find((entry) => entry.operationId === call.operationId);
    if (!operation || !matchesCallGrant(call, operation) || !matchesOwnedGrant(operation, owner)) return false;
    state.calls.splice(index, 1);
    if (!['PUBLIC_READ', 'SENSITIVE_READ'].includes(call.effect)) operation.validationRequired = true;
    atomicWrite(target, state);
    return true;
  });
}


export function recordOutcomeUnknown(sessionId, operationId, observation, env = process.env, now = Date.now(), owner) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const boundedOperation = bounded(operationId, 'INVALID_OPERATION');
  const reasonCode = bounded(observation?.reasonCode, 'INVALID_OUTCOME');
  const action = bounded(observation?.action, 'INVALID_OUTCOME');
  const effect = bounded(observation?.effect, 'INVALID_OUTCOME');
  return withLock(boundedSession, env, (target) => {
    const state = readState(boundedSession, env, now);
    const operation = state.active.find((entry) => entry.operationId === boundedOperation);
    if (!operation || !matchesOwnedGrant(operation, owner)) return false;
    operation.outcome = 'OUTCOME_UNKNOWN';
    operation.outcomeObservation = { reasonCode, action, effect, observedAt: now };
    operation.validationRequired = true;
    state.calls = state.calls.filter((entry) => entry.operationId !== boundedOperation);
    atomicWrite(target, state);
    return true;
  });
}


export function failBrowserCall(sessionId, toolUseId, reasonCode, env = process.env, now = Date.now(), owner) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const boundedToolUse = bounded(toolUseId, 'INVALID_BROWSER_CALL');
  const boundedReason = bounded(reasonCode, 'INVALID_OUTCOME');
  return withLock(boundedSession, env, (target) => {
    const state = readState(boundedSession, env, now);
    const index = state.calls.findIndex((entry) => entry.toolUseId === boundedToolUse);
    if (index < 0) return false;
    const call = state.calls[index];
    const operation = state.active.find((entry) => entry.operationId === call.operationId);
    if (!operation || !matchesCallGrant(call, operation) || !matchesOwnedGrant(operation, owner)) return false;
    state.calls.splice(index, 1);
    operation.outcome = 'OUTCOME_UNKNOWN';
    operation.outcomeObservation = {
      reasonCode: boundedReason, action: call.action, effect: call.effect, observedAt: now,
    };
    operation.validationRequired = true;
    atomicWrite(target, state);
    return true;
  });
}


export function reconcileOutcomeUnknown(
  sessionId, operationId, validationRef, outcome, env = process.env, now = Date.now(), owner,
) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const boundedOperation = bounded(operationId, 'INVALID_OPERATION');
  const boundedValidation = bounded(validationRef, 'INVALID_VALIDATION');
  if (!['applied', 'not-applied'].includes(outcome)) throw new Error('INVALID_VALIDATION_OUTCOME');
  return withLock(boundedSession, env, (target) => {
    const state = readState(boundedSession, env, now);
    const operation = state.active.find((entry) => entry.operationId === boundedOperation);
    if (!operation || !matchesOwnedGrant(operation, owner) || operation.outcome !== 'OUTCOME_UNKNOWN'
        || operation.envelope.validationRef !== boundedValidation) return false;
    operation.outcome = outcome === 'applied' ? 'APPLIED_CONFIRMED' : 'READY';
    operation.validationRequired = false;
    delete operation.outcomeObservation;
    atomicWrite(target, state);
    return true;
  });
}


export function completeIndependentValidation(
  sessionId, operationId, validationRef, env = process.env, now = Date.now(), owner,
) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const boundedOperation = bounded(operationId, 'INVALID_OPERATION');
  const boundedValidation = bounded(validationRef, 'INVALID_VALIDATION');
  return withLock(boundedSession, env, (target) => {
    const state = readState(boundedSession, env, now);
    const operation = state.active.find((entry) => entry.operationId === boundedOperation);
    if (!operation || !matchesOwnedGrant(operation, owner) || operation.outcome !== 'READY'
        || operation.envelope.validationRef !== boundedValidation) return false;
    operation.validationRequired = false;
    atomicWrite(target, state);
    return true;
  });
}


export function invalidateOperation(sessionId, operationId, reasonCode, env = process.env, now = Date.now()) {
  const boundedSession = bounded(sessionId, 'INVALID_SESSION');
  const boundedOperation = bounded(operationId, 'INVALID_OPERATION');
  bounded(reasonCode, 'INVALID_REASON');
  return withLock(boundedSession, env, (target) => {
    const state = readState(boundedSession, env, now);
    const prior = state.active.length + state.pending.length;
    state.pending = state.pending.filter((entry) => entry.operationId !== boundedOperation);
    state.active = state.active.filter((entry) => entry.operationId !== boundedOperation);
    state.calls = state.calls.filter((entry) => entry.operationId !== boundedOperation);
    if (prior === state.active.length + state.pending.length) return false;
    atomicWrite(target, state);
    return true;
  });
}


export function consumeOwnedOperation(correlation, env = process.env) {
  try {
    const sessionId = bounded(correlation?.sessionId, 'INVALID_BROWSER_CORRELATION');
    const operationId = bounded(correlation?.operationId, 'INVALID_BROWSER_CORRELATION');
    const toolUseId = bounded(correlation?.toolUseId, 'INVALID_BROWSER_CORRELATION');
    const invocationFingerprint = correlation?.invocationFingerprint;
    const expiresAt = correlation?.expiresAt;
    if (!Number.isSafeInteger(expiresAt) || expiresAt <= 0
        || (invocationFingerprint !== null
          && (typeof invocationFingerprint !== 'string' || !INVOCATION_FINGERPRINT.test(invocationFingerprint)))) {
      throw new Error('INVALID_BROWSER_CORRELATION');
    }
    return withLock(sessionId, env, (target) => {
      const state = readRawState(sessionId, env);
      const sameGrant = (entry) => entry.operationId === operationId
        && entry.toolUseId === toolUseId && entry.expiresAt === expiresAt
        && entry.invocationFingerprint === invocationFingerprint;
      const grants = [...state.pending, ...state.active];
      if (grants.some((entry) => entry.operationId === operationId
          && entry.toolUseId === toolUseId && !sameGrant(entry))) return false;
      if (state.calls.some((entry) => entry.operationId === operationId
          && (entry.approvalToolUseId === undefined
            || (entry.approvalToolUseId === toolUseId && entry.expiresAt !== expiresAt)))) return false;
      const sameCall = (entry) => entry.operationId === operationId
        && entry.approvalToolUseId === toolUseId && entry.expiresAt === expiresAt;
      const removed = grants.some(sameGrant) || state.calls.some(sameCall);
      state.pending = state.pending.filter((entry) => !sameGrant(entry));
      state.active = state.active.filter((entry) => !sameGrant(entry));
      state.calls = state.calls.filter((entry) => !sameCall(entry));
      if (removed) atomicWrite(target, state);
      return true;
    });
  } catch {
    throw new BrowserLifetimeError('APPROVAL_BINDING_INVALID');
  }
}
