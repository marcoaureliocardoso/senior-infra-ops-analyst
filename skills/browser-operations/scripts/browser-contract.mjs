import { createHash } from 'node:crypto';


export const CAPABILITY_STATES = Object.freeze([
  'AVAILABLE_RECOGNIZED',
  'AVAILABLE_UNRECOGNIZED',
  'UNAVAILABLE',
  'CONFLICT',
  'ACTIVE',
]);

export const EFFECT_CLASSES = Object.freeze([
  'PUBLIC_READ',
  'SENSITIVE_READ',
  'INTERACTIVE_STATE',
  'LOW_RISK_CHANGE',
  'DISRUPTIVE_CHANGE',
  'DESTRUCTIVE_CHANGE',
  'SENSITIVE_ARTIFACT',
  'UNKNOWN',
]);

export const ROUTE_CLASSES = Object.freeze([
  'TYPED_API_MCP',
  'NATIVE_BROWSER',
  'CONTROLLED_BROWSER_MCP',
  'PROTECTED_RUNNER',
  'PUBLIC_FETCH',
  'COMPUTER_USE',
]);

const ENVELOPE_FIELDS = Object.freeze([
  'version', 'operationId', 'sessionId', 'role', 'objectiveRef', 'target',
  'environment', 'serviceOrigins', 'authOrigins', 'identityRef',
  'credentialTransport', 'permissionModeAtApproval', 'actions',
  'expectedEffect', 'risk', 'modifiers', 'preconditionRef', 'validationRef',
  'compensationRef', 'artifactPolicy', 'expiresAt',
]);
const ARTIFACT_FIELDS = Object.freeze([
  'enabled', 'types', 'purposeRef', 'sourceClasses', 'destinationClasses',
  'maxItems', 'maxBytes', 'redaction', 'retentionSeconds',
]);
const ROLES = new Set([
  'audit-evidence-collector', 'change-manager', 'cloud-platform-operator',
  'database-operator', 'diagnostic-operator', 'incident-commander',
  'kubernetes-operator', 'network-edge-operator', 'observability-sre',
  'rca-facilitator', 'release-cicd-operator', 'security-operations-reviewer',
]);
const RISKS = new Set([
  'SAFE_READ_ONLY', 'LOW_RISK_CHANGE', 'DISRUPTIVE_CHANGE', 'DESTRUCTIVE',
]);
const MODIFIERS = new Set([
  'SENSITIVE_OUTPUT', 'RESOURCE_INTENSIVE', 'ACTIVE_PROBE', 'PRIVILEGED',
  'REMOTE_SESSION_RISK', 'EXTERNAL_SIDE_EFFECT',
]);
const PERMISSION_MODES = new Set([
  'normal', 'default', 'acceptEdits', 'plan', 'bypassPermissions', 'dontAsk',
]);
const TRANSPORT_PREFIXES = new Map([
  ['profile', 'profile:'],
  ['vault', 'vault:'],
  ['keychain', 'keychain:'],
  ['helper', 'helper:'],
  ['secret-manager', 'secret-manager:'],
  ['fd', 'fd:'],
  ['direct-protected-reference', 'direct-protected-reference:'],
  ['operator-provided-protected-channel', 'operator-provided-protected-channel:'],
]);
const ARTIFACT_TYPES = new Set(['upload', 'download', 'screenshot', 'trace']);
const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$/u;
const ACTION = /^[a-z0-9][a-z0-9-]{0,95}$/u;
const ASCII = /^[\x20-\x7e]+$/u;
const MAX_ORIGINS = 8;
const MAX_ACTIONS = 16;
const MAX_EXPIRY_MS = 24 * 60 * 60 * 1000;


export class BrowserContractError extends Error {
  constructor(code) {
    super(code);
    this.name = 'BrowserContractError';
    this.code = code;
  }
}


function fail(code) {
  throw new BrowserContractError(code);
}


function exactFields(value, fields, invalidCode, missingCode) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(invalidCode);
  const expected = new Set(fields);
  for (const key of Object.keys(value)) {
    if (!expected.has(key)) fail(invalidCode);
  }
  for (const key of fields) {
    if (!Object.hasOwn(value, key)) fail(missingCode);
  }
}


function boundedString(value) {
  if (typeof value !== 'string' || !IDENTIFIER.test(value)) fail('INVALID_BOUNDED_STRING');
  return value;
}


function boundedStringList(value, { maximum, pattern = IDENTIFIER, duplicateCode }) {
  if (!Array.isArray(value) || value.length > maximum) fail('INVALID_BOUNDED_LIST');
  const result = value.map((entry) => {
    if (typeof entry !== 'string' || !pattern.test(entry)) fail('INVALID_BOUNDED_STRING');
    return entry;
  });
  if (new Set(result).size !== result.length) fail(duplicateCode);
  return Object.freeze(result);
}


function freezeRecord(value) {
  for (const item of Object.values(value)) {
    if (item && typeof item === 'object' && !Object.isFrozen(item)) freezeRecord(item);
  }
  return Object.freeze(value);
}


export function normalizeOrigin(value) {
  if (typeof value !== 'string' || value.length < 1 || value.length > 2048 || !ASCII.test(value)) {
    if (typeof value === 'string' && /[^\x00-\x7f]/u.test(value)) fail('ORIGIN_IDN_FORBIDDEN');
    fail('INVALID_ORIGIN');
  }
  if (value.includes('*')) fail('ORIGIN_WILDCARD_FORBIDDEN');

  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    fail('INVALID_ORIGIN');
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') fail('INVALID_ORIGIN_SCHEME');
  if (parsed.username || parsed.password) fail('ORIGIN_CREDENTIALS_FORBIDDEN');
  if (parsed.hostname.toLowerCase().split('.').some((label) => label.startsWith('xn--'))) {
    fail('ORIGIN_IDN_FORBIDDEN');
  }
  if (!parsed.hostname) fail('INVALID_ORIGIN');
  const port = parsed.port || (parsed.protocol === 'https:' ? '443' : '80');
  return `${parsed.protocol}//${parsed.hostname.toLowerCase()}:${port}`;
}


function normalizedOrigins(value, minimum) {
  if (!Array.isArray(value) || value.length < minimum || value.length > MAX_ORIGINS) {
    fail('INVALID_ORIGIN_LIST');
  }
  const result = value.map(normalizeOrigin);
  if (new Set(result).size !== result.length) fail('DUPLICATE_ORIGIN');
  return Object.freeze(result);
}


function parseArtifactPolicy(value) {
  exactFields(value, ARTIFACT_FIELDS, 'INVALID_ARTIFACT_FIELD', 'MISSING_ARTIFACT_FIELD');
  if (typeof value.enabled !== 'boolean') fail('INVALID_ARTIFACT_POLICY');
  const types = boundedStringList(value.types, {
    maximum: 4, pattern: ACTION, duplicateCode: 'DUPLICATE_ARTIFACT_TYPE',
  });
  const sourceClasses = boundedStringList(value.sourceClasses, {
    maximum: 8, pattern: ACTION, duplicateCode: 'DUPLICATE_ARTIFACT_SOURCE',
  });
  const destinationClasses = boundedStringList(value.destinationClasses, {
    maximum: 8, pattern: ACTION, duplicateCode: 'DUPLICATE_ARTIFACT_DESTINATION',
  });
  for (const type of types) if (!ARTIFACT_TYPES.has(type)) fail('INVALID_ARTIFACT_TYPE');
  const purposeRef = boundedString(value.purposeRef);
  if (!Number.isSafeInteger(value.maxItems) || !Number.isSafeInteger(value.maxBytes)
      || !Number.isSafeInteger(value.retentionSeconds)) fail('INVALID_ARTIFACT_POLICY');
  if (!['none', 'required', 'structured'].includes(value.redaction)) fail('INVALID_ARTIFACT_POLICY');

  if (!value.enabled) {
    if (types.length || sourceClasses.length || destinationClasses.length
        || purposeRef !== 'none' || value.maxItems !== 0 || value.maxBytes !== 0
        || value.redaction !== 'none' || value.retentionSeconds !== 0) {
      fail('INVALID_DISABLED_ARTIFACT_POLICY');
    }
  } else if (
    types.length < 1 || sourceClasses.length < 1 || destinationClasses.length < 1
    || purposeRef === 'none' || value.maxItems < 1 || value.maxItems > 16
    || value.maxBytes < 1 || value.maxBytes > 50_000_000
    || value.redaction === 'none'
    || value.retentionSeconds < 1 || value.retentionSeconds > 3600
  ) {
    fail('INVALID_ARTIFACT_POLICY');
  }
  return freezeRecord({
    enabled: value.enabled,
    types,
    purposeRef,
    sourceClasses,
    destinationClasses,
    maxItems: value.maxItems,
    maxBytes: value.maxBytes,
    redaction: value.redaction,
    retentionSeconds: value.retentionSeconds,
  });
}


export function parseOperationEnvelope(value, now = Date.now()) {
  exactFields(value, ENVELOPE_FIELDS, 'INVALID_ENVELOPE_FIELD', 'MISSING_ENVELOPE_FIELD');
  if (value.version !== 1) fail('INVALID_ENVELOPE_VERSION');
  if (!Number.isSafeInteger(now) || now < 0) fail('INVALID_CLOCK');

  const operationId = boundedString(value.operationId);
  const sessionId = boundedString(value.sessionId);
  if (!ROLES.has(value.role)) fail('INVALID_ROLE');
  const role = value.role;
  const objectiveRef = boundedString(value.objectiveRef);
  const target = boundedString(value.target);
  const environment = boundedString(value.environment);
  const serviceOrigins = normalizedOrigins(value.serviceOrigins, 1);
  const authOrigins = normalizedOrigins(value.authOrigins, 0);

  if (!TRANSPORT_PREFIXES.has(value.credentialTransport)
      || typeof value.identityRef !== 'string'
      || !value.identityRef.startsWith(TRANSPORT_PREFIXES.get(value.credentialTransport))
      || !IDENTIFIER.test(value.identityRef)) fail('CREDENTIAL_REFERENCE_REQUIRED');
  if (!PERMISSION_MODES.has(value.permissionModeAtApproval)) fail('INVALID_PERMISSION_MODE');
  const actions = boundedStringList(value.actions, {
    maximum: MAX_ACTIONS, pattern: ACTION, duplicateCode: 'DUPLICATE_ACTION',
  });
  if (actions.length < 1) fail('INVALID_BOUNDED_LIST');
  if (!EFFECT_CLASSES.includes(value.expectedEffect)) fail('INVALID_EFFECT');
  if (!RISKS.has(value.risk)) fail('INVALID_RISK');
  const modifiers = boundedStringList(value.modifiers, {
    maximum: MODIFIERS.size, pattern: /^[A-Z][A-Z_]{0,63}$/u,
    duplicateCode: 'DUPLICATE_MODIFIER',
  });
  for (const modifier of modifiers) if (!MODIFIERS.has(modifier)) fail('INVALID_MODIFIER');
  const preconditionRef = boundedString(value.preconditionRef);
  const validationRef = boundedString(value.validationRef);
  const compensationRef = boundedString(value.compensationRef);
  const artifactPolicy = parseArtifactPolicy(value.artifactPolicy);
  if (artifactPolicy.enabled && value.expectedEffect !== 'SENSITIVE_ARTIFACT') {
    fail('ARTIFACT_EFFECT_REQUIRED');
  }
  if (!Number.isSafeInteger(value.expiresAt) || value.expiresAt <= now) fail('ENVELOPE_EXPIRED');
  if (value.expiresAt - now > MAX_EXPIRY_MS) fail('INVALID_EXPIRY');

  return freezeRecord({
    version: 1,
    operationId,
    sessionId,
    role,
    objectiveRef,
    target,
    environment,
    serviceOrigins,
    authOrigins,
    identityRef: value.identityRef,
    credentialTransport: value.credentialTransport,
    permissionModeAtApproval: value.permissionModeAtApproval,
    actions,
    expectedEffect: value.expectedEffect,
    risk: value.risk,
    modifiers,
    preconditionRef,
    validationRef,
    compensationRef,
    artifactPolicy,
    expiresAt: value.expiresAt,
  });
}


function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) =>
      `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}


export function operationFingerprint(envelope) {
  const canonical = parseOperationEnvelope(envelope, envelope.expiresAt - 1);
  return createHash('sha256').update(canonicalJson(canonical), 'utf8').digest('hex');
}
