import { createHash } from 'node:crypto';
import { TextDecoder } from 'node:util';

import { EFFECT_CLASSES, normalizeOrigin } from './browser-contract.mjs';


const MAX_TOKEN_BYTES = 2048;
const MAX_RECORD_BYTES = 1536;
const MAX_EXECUTION_STEPS = 16;
const MAX_VALIDATION_STEPS = 12;
const ACTION = /^[a-z0-9][a-z0-9-]{0,95}$/u;
const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$/u;
const PROTECTED_REFERENCE = /^env:OPS_BROWSER_VALUE_[A-Z0-9_]+$/u;
const PREDICATES = new Set([
  'present', 'text-equals', 'value-equals', 'checked', 'selected-value-equals',
]);
const EXECUTION_STEPS = new Set([
  'inspect', 'navigate', 'fill', 'select', 'click', 'submit',
  'upload', 'download', 'screenshot', 'trace',
]);
const VALIDATION_STEPS = new Set(['navigate', 'fill', 'select', 'click']);
const DECODER = new TextDecoder('utf-8', { fatal: true });


export class BrowserWorkflowError extends Error {
  constructor(code) {
    super(code);
    this.name = 'BrowserWorkflowError';
    this.code = code;
  }
}


function fail(code) {
  throw new BrowserWorkflowError(code);
}


function freeze(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    for (const child of Object.values(value)) freeze(child);
    Object.freeze(value);
  }
  return value;
}


function parseJson(source) {
  let index = 0;

  function whitespace() {
    while (/[ \t\n\r]/u.test(source[index] ?? '')) index += 1;
  }

  function string() {
    if (source[index] !== '"') fail('INVALID_JSON');
    const start = index;
    index += 1;
    while (index < source.length) {
      const character = source[index];
      if (character === '"') {
        index += 1;
        try {
          return JSON.parse(source.slice(start, index));
        } catch {
          fail('INVALID_JSON');
        }
      }
      if (character === '\\') {
        index += 1;
        if (source[index] === 'u') index += 4;
        index += 1;
      } else {
        if (character < ' ') fail('INVALID_JSON');
        index += 1;
      }
    }
    fail('INVALID_JSON');
  }

  function value() {
    whitespace();
    const character = source[index];
    if (character === '"') return string();
    if (character === '{') return object();
    if (character === '[') return array();
    for (const [literal, result] of [['true', true], ['false', false], ['null', null]]) {
      if (source.startsWith(literal, index)) {
        index += literal.length;
        return result;
      }
    }
    const match = /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/u.exec(source.slice(index));
    if (!match) fail('INVALID_JSON');
    index += match[0].length;
    return Number(match[0]);
  }

  function object() {
    const result = Object.create(null);
    const keys = new Set();
    index += 1;
    whitespace();
    if (source[index] === '}') {
      index += 1;
      return result;
    }
    while (true) {
      whitespace();
      const key = string();
      if (keys.has(key)) fail('DUPLICATE_JSON_KEY');
      keys.add(key);
      whitespace();
      if (source[index] !== ':') fail('INVALID_JSON');
      index += 1;
      const parsed = value();
      Object.defineProperty(result, key, { value: parsed, enumerable: true });
      whitespace();
      if (source[index] === '}') {
        index += 1;
        return result;
      }
      if (source[index] !== ',') fail('INVALID_JSON');
      index += 1;
    }
  }

  function array() {
    const result = [];
    index += 1;
    whitespace();
    if (source[index] === ']') {
      index += 1;
      return result;
    }
    while (true) {
      result.push(value());
      whitespace();
      if (source[index] === ']') {
        index += 1;
        return result;
      }
      if (source[index] !== ',') fail('INVALID_JSON');
      index += 1;
    }
  }

  const result = value();
  whitespace();
  if (index !== source.length || !result || typeof result !== 'object' || Array.isArray(result)) fail('INVALID_JSON');
  return result;
}


function decodeToken(token) {
  if (typeof token !== 'string' || token.length < 1) fail('INVALID_TOKEN');
  if (!/^[A-Za-z0-9_-]+$/u.test(token)) fail(token.includes('=') ? 'NON_CANONICAL_TOKEN' : 'INVALID_TOKEN');
  const remainder = token.length % 4;
  const decodedUpperBound = Math.floor(token.length / 4) * 3
    + (remainder === 2 ? 1 : remainder === 3 ? 2 : 0);
  if (decodedUpperBound > MAX_RECORD_BYTES) fail('RECORD_TOO_LARGE');
  if (token.length > MAX_TOKEN_BYTES) fail('TOKEN_TOO_LARGE');
  let decoded;
  try {
    decoded = Buffer.from(token, 'base64url');
  } catch {
    fail('INVALID_TOKEN');
  }
  if (decoded.toString('base64url') !== token) fail('NON_CANONICAL_TOKEN');
  if (decoded.length > MAX_RECORD_BYTES) fail('RECORD_TOO_LARGE');
  try {
    return DECODER.decode(decoded);
  } catch {
    fail('INVALID_UTF8');
  }
}


function exactKeys(record, fields) {
  const allowed = new Set(fields);
  for (const [key, value] of Object.entries(record)) {
    if (!allowed.has(key)) fail('UNKNOWN_STEP_FIELD');
    if (value && typeof value === 'object') fail('INVALID_STEP_FIELD');
  }
  for (const field of fields) if (!Object.hasOwn(record, field)) fail('MISSING_STEP_FIELD');
}


function optionalKeys(record, required, optional = []) {
  const fields = [...required, ...optional];
  const allowed = new Set(fields);
  for (const [key, value] of Object.entries(record)) {
    if (!allowed.has(key)) fail('UNKNOWN_STEP_FIELD');
    if (value && typeof value === 'object') fail('INVALID_STEP_FIELD');
  }
  for (const field of required) if (!Object.hasOwn(record, field)) fail('MISSING_STEP_FIELD');
}


function text(value) {
  if (typeof value !== 'string' || value.length < 1 || value.length > 255 || /[\x00-\x1f\x7f]/u.test(value)) {
    fail('INVALID_SEMANTIC_LOCATOR');
  }
  return value;
}


function action(value) {
  if (typeof value !== 'string' || !ACTION.test(value)) fail('INVALID_SEMANTIC_LOCATOR');
  return value;
}


function protectedReference(value) {
  if (typeof value !== 'string' || !PROTECTED_REFERENCE.test(value)) fail('INVALID_PROTECTED_REFERENCE');
  return value;
}


function reference(value) {
  if (typeof value !== 'string' || !IDENTIFIER.test(value)) fail('INVALID_REFERENCE');
  return value;
}


function normalizedOrigin(value) {
  try {
    return normalizeOrigin(value);
  } catch {
    fail('INVALID_ORIGIN');
  }
}


function normalizedStep(record) {
  if (typeof record.step !== 'string') fail('INVALID_STEP');
  const step = record.step;
  if (!EXECUTION_STEPS.has(step)) fail('INVALID_EXECUTION_STEP');
  if (step === 'navigate') {
    exactKeys(record, ['step', 'origin']);
    return freeze(Object.assign(Object.create(null), { step, origin: normalizedOrigin(record.origin) }));
  }
  if (['fill', 'select'].includes(step)) {
    optionalKeys(record, ['step', 'origin', 'locatorRole', 'valueRef'], ['locatorName']);
    return freeze(Object.assign(Object.create(null), {
      step, origin: normalizedOrigin(record.origin), locatorRole: action(record.locatorRole),
      ...(Object.hasOwn(record, 'locatorName') ? { locatorName: text(record.locatorName) } : {}),
      valueRef: protectedReference(record.valueRef),
    }));
  }
  if (['click', 'submit'].includes(step)) {
    optionalKeys(record, ['step', 'origin', 'locatorRole', 'effect'], ['locatorName']);
    if (typeof record.effect !== 'string' || !EFFECT_CLASSES.includes(record.effect) || record.effect === 'UNKNOWN') {
      fail('INVALID_EFFECT');
    }
    return freeze(Object.assign(Object.create(null), {
      step, origin: normalizedOrigin(record.origin), locatorRole: action(record.locatorRole),
      ...(Object.hasOwn(record, 'locatorName') ? { locatorName: text(record.locatorName) } : {}), effect: record.effect,
    }));
  }
  if (step === 'inspect') {
    optionalKeys(record, ['step', 'origin', 'locatorRole', 'predicate', 'expectedRef', 'expectRef'], ['locatorName']);
    if (typeof record.predicate !== 'string' || !PREDICATES.has(record.predicate)) fail('INVALID_PREDICATE');
    return freeze(Object.assign(Object.create(null), {
      step, origin: normalizedOrigin(record.origin), locatorRole: action(record.locatorRole),
      ...(Object.hasOwn(record, 'locatorName') ? { locatorName: text(record.locatorName) } : {}),
      predicate: record.predicate, expectedRef: protectedReference(record.expectedRef), expectRef: reference(record.expectRef),
    }));
  }
  exactKeys(record, ['step', 'origin', 'artifactRef']);
  return freeze(Object.assign(Object.create(null), {
    step, origin: normalizedOrigin(record.origin), artifactRef: reference(record.artifactRef),
  }));
}


export function decodeWorkflowStep(token) {
  return normalizedStep(parseJson(decodeToken(token)));
}


function boundedSteps(tokens, maximum, countCode) {
  if (!Array.isArray(tokens) || tokens.length < 1 || tokens.length > maximum) fail(countCode);
  return tokens.map(decodeWorkflowStep);
}


export function parseWorkflowSteps(executionTokens, validationTokens) {
  const executionSteps = boundedSteps(executionTokens, MAX_EXECUTION_STEPS, 'INVALID_EXECUTION_COUNT');
  const validationSteps = boundedSteps(validationTokens, MAX_VALIDATION_STEPS, 'INVALID_VALIDATION_COUNT');
  const inspections = validationSteps.filter((step) => step.step === 'inspect');
  if (inspections.length !== 1) fail('INVALID_VALIDATION_INSPECT');
  if (validationSteps.at(-1).step !== 'inspect') fail('MISSING_FINAL_INSPECT');
  for (const step of validationSteps.slice(0, -1)) {
    if (!VALIDATION_STEPS.has(step.step)) fail('INVALID_VALIDATION_STEP');
    if (step.step === 'click' && step.effect !== 'INTERACTIVE_STATE') fail('INVALID_VALIDATION_EFFECT');
  }
  return freeze({ executionSteps: freeze(executionSteps), validationSteps: freeze(validationSteps) });
}


function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}


export function workflowFingerprint(request) {
  if (!request || typeof request !== 'object' || !request.envelope
      || !Array.isArray(request.executionSteps) || !Array.isArray(request.validationSteps)
      || !Number.isSafeInteger(request.expiresInSeconds)
      || request.expiresInSeconds < 1 || request.expiresInSeconds > 86_400) {
    fail('INVALID_FINGERPRINT_REQUEST');
  }
  const { expiresAt, ...envelope } = request.envelope;
  const canonical = canonicalJson({
    envelope: { ...envelope, expiresInSeconds: request.expiresInSeconds },
    executionSteps: request.executionSteps,
    validationSteps: request.validationSteps,
  });
  return createHash('sha256').update(canonical, 'utf8').digest('hex');
}
