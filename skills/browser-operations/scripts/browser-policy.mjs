import { operationFingerprint } from './browser-contract.mjs';


export const BROWSER_REASON_CODES = Object.freeze([
  'ALLOW_PUBLIC_READ',
  'ALLOW_BOUND_OPERATION',
  'ASK_SENSITIVE_READ',
  'ASK_INTERACTIVE_STATE',
  'ASK_CHANGE',
  'ASK_DESTRUCTIVE',
  'ASK_SENSITIVE_ARTIFACT',
  'DENY_UNKNOWN_CAPABILITY',
  'DENY_GUARD_UNPROVEN',
  'DENY_OPERATION_MISMATCH',
  'DENY_ORIGIN_ESCAPE',
  'DENY_SECRET_DESTINATION',
  'DENY_ROLE',
  'DENY_EXPIRED',
  'DENY_OUTCOME_UNKNOWN',
  'PROMPT_INJECTION_ATTEMPT',
]);

const EXECUTOR_ROLES = new Set([
  'main', 'cloud-platform-operator', 'database-operator', 'diagnostic-operator',
  'kubernetes-operator', 'network-edge-operator', 'observability-sre',
  'release-cicd-operator',
]);
const REVIEW_ROLES = new Set([
  'change-manager', 'incident-commander', 'rca-facilitator',
  'security-operations-reviewer',
]);
const EFFECT_RANK = new Map([
  ['PUBLIC_READ', 0],
  ['SENSITIVE_READ', 1],
  ['INTERACTIVE_STATE', 2],
  ['LOW_RISK_CHANGE', 3],
  ['DISRUPTIVE_CHANGE', 4],
  ['DESTRUCTIVE_CHANGE', 5],
]);
const EFFECT_DECISIONS = Object.freeze({
  PUBLIC_READ: ['allow', 'ALLOW_PUBLIC_READ'],
  SENSITIVE_READ: ['ask', 'ASK_SENSITIVE_READ'],
  INTERACTIVE_STATE: ['ask', 'ASK_INTERACTIVE_STATE'],
  LOW_RISK_CHANGE: ['ask', 'ASK_CHANGE'],
  DISRUPTIVE_CHANGE: ['ask', 'ASK_CHANGE'],
  DESTRUCTIVE_CHANGE: ['ask', 'ASK_DESTRUCTIVE'],
  SENSITIVE_ARTIFACT: ['ask', 'ASK_SENSITIVE_ARTIFACT'],
});


function result(envelope, call, decision, reasonCode) {
  return Object.freeze({
    decision,
    effect: call?.effect ?? 'UNKNOWN',
    modifiers: Object.freeze([...(envelope?.modifiers ?? [])]),
    operationId: envelope?.operationId ?? null,
    reasonCode,
    risk: envelope?.risk ?? 'DESTRUCTIVE',
  });
}


function deny(envelope, call, reasonCode) {
  return result(envelope, call, 'deny', reasonCode);
}


function capabilityDecision(capability) {
  if (capability?.state === 'ACTIVE') return null;
  if (capability?.state === 'AVAILABLE_RECOGNIZED') return 'DENY_GUARD_UNPROVEN';
  return 'DENY_UNKNOWN_CAPABILITY';
}


function bindingMatches(event, envelope, capability, binding) {
  return binding?.active === true
    && binding.operationId === envelope.operationId
    && binding.sessionId === event.sessionId
    && binding.sessionId === envelope.sessionId
    && binding.role === event.role
    && binding.role === envelope.role
    && binding.operationFingerprint === operationFingerprint(envelope)
    && binding.adapterId === capability.adapterId
    && binding.routeClass === capability.routeClass
    && binding.settingsFingerprint === capability.settingsFingerprint
    && Array.isArray(binding.permissionModes)
    && binding.permissionModes.includes(event.permissionMode);
}


function roleAllows(role, effect) {
  if (EXECUTOR_ROLES.has(role)) return true;
  if (role === 'audit-evidence-collector') {
    return effect === 'PUBLIC_READ' || effect === 'SENSITIVE_READ';
  }
  if (REVIEW_ROLES.has(role)) return false;
  return false;
}


function effectWithinEnvelope(effect, expectedEffect, artifactPolicy) {
  if (effect === 'UNKNOWN') return false;
  if (effect === 'SENSITIVE_ARTIFACT') {
    return expectedEffect === 'SENSITIVE_ARTIFACT' && artifactPolicy?.enabled === true;
  }
  if (expectedEffect === 'SENSITIVE_ARTIFACT') return EFFECT_RANK.has(effect);
  return EFFECT_RANK.has(effect)
    && EFFECT_RANK.has(expectedEffect)
    && EFFECT_RANK.get(effect) <= EFFECT_RANK.get(expectedEffect);
}


function destinationAllowed(envelope, origin) {
  if (origin === null || origin === undefined) return true;
  return envelope.serviceOrigins.includes(origin) || envelope.authOrigins.includes(origin);
}


export function evaluateBrowserCall({ event, envelope, capability, binding, call, now = Date.now() }) {
  const capabilityReason = capabilityDecision(capability);
  if (capabilityReason) return deny(envelope, call, capabilityReason);
  if (!Number.isSafeInteger(now) || now >= envelope.expiresAt || now >= binding?.expiresAt) {
    return deny(envelope, call, 'DENY_EXPIRED');
  }
  if (!roleAllows(event?.role, call?.effect)) return deny(envelope, call, 'DENY_ROLE');
  if (binding?.outcome !== 'READY') return deny(envelope, call, 'DENY_OUTCOME_UNKNOWN');
  if (!bindingMatches(event, envelope, capability, binding)) {
    return deny(envelope, call, 'DENY_OPERATION_MISMATCH');
  }
  if (!call || !envelope.actions.includes(call.action)) {
    return deny(envelope, call, 'DENY_OPERATION_MISMATCH');
  }
  const sensitiveInput = Array.isArray(call.sensitiveInputKeys) && call.sensitiveInputKeys.length > 0;
  if (sensitiveInput && (
    call.action !== 'authenticate'
    || !call.destinationOrigin
    || !envelope.authOrigins.includes(call.destinationOrigin)
  )) return deny(envelope, call, 'DENY_SECRET_DESTINATION');

  if (!destinationAllowed(envelope, call.destinationOrigin)) {
    return deny(envelope, call, 'DENY_ORIGIN_ESCAPE');
  }
  if (!effectWithinEnvelope(call.effect, envelope.expectedEffect, envelope.artifactPolicy)) {
    return deny(envelope, call, call.effect === 'UNKNOWN'
      ? 'DENY_UNKNOWN_CAPABILITY' : 'DENY_OPERATION_MISMATCH');
  }

  const [decision, reasonCode] = EFFECT_DECISIONS[call.effect];
  return result(envelope, call, decision, reasonCode);
}
