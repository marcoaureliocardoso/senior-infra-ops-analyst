import { pathToFileURL } from 'node:url';

import {
  completeBrowserCall,
  failBrowserCall,
  readSingleActiveOperation,
  stageBrowserCall,
} from './browser-binding-store.mjs';
import { mapBrowserMcpCall } from './browser-mcp-registry.mjs';
import { evaluateBrowserCall } from './browser-policy.mjs';


const MAX_INPUT_BYTES = 1024 * 1024;
const MAX_DEPTH = 20;
const MAX_FIELD = 512;
const MODES = new Set(['pre', 'post', 'failure']);
const SECURITY_KEYS = new Set([
  'session_id', 'hook_event_name', 'permission_mode', 'tool_name', 'tool_input',
  'tool_use_id', '__proto__', 'prototype', 'constructor',
]);


function requiredString(value, label) {
  if (typeof value !== 'string' || value.length < 1 || value.length > MAX_FIELD) {
    throw new Error(`INVALID_${label.toUpperCase()}`);
  }
  return value;
}


function uniqueSecurityKeys(raw) {
  const seen = new Set();
  const pattern = /"((?:\\.|[^"\\])*)"\s*:/gu;
  for (const match of raw.matchAll(pattern)) {
    const key = JSON.parse(`"${match[1]}"`);
    if (SECURITY_KEYS.has(key) && seen.has(key)) throw new Error('DUPLICATE_SECURITY_KEY');
    if (SECURITY_KEYS.has(key)) seen.add(key);
  }
}


function boundedDepth(value) {
  const pending = [[value, 1]];
  while (pending.length) {
    const [current, depth] = pending.pop();
    if (depth > MAX_DEPTH) throw new Error('HOOK_DEPTH_EXCEEDED');
    if (current && typeof current === 'object') {
      for (const child of Object.values(current)) pending.push([child, depth + 1]);
    }
  }
}


function parseEvent(raw, mode) {
  if (!MODES.has(mode)) throw new Error('INVALID_HOOK_MODE');
  if (typeof raw !== 'string' || Buffer.byteLength(raw, 'utf8') > MAX_INPUT_BYTES) {
    throw new Error('HOOK_INPUT_TOO_LARGE');
  }
  uniqueSecurityKeys(raw);
  let value;
  try {
    value = JSON.parse(raw);
  } catch {
    throw new Error('INVALID_HOOK_JSON');
  }
  boundedDepth(value);
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('INVALID_HOOK_EVENT');
  const expected = mode === 'pre' ? 'PreToolUse'
    : mode === 'post' ? 'PostToolUse' : 'PostToolUseFailure';
  if (value.hook_event_name !== expected) throw new Error('INVALID_HOOK_EVENT');
  if (!value.tool_input || typeof value.tool_input !== 'object' || Array.isArray(value.tool_input)) {
    throw new Error('INVALID_TOOL_INPUT');
  }
  return Object.freeze({
    sessionId: requiredString(value.session_id, 'session'),
    toolUseId: requiredString(value.tool_use_id, 'tool_use'),
    permissionMode: mode === 'pre' ? requiredString(value.permission_mode, 'permission_mode') : null,
    toolName: requiredString(value.tool_name, 'tool_name'),
    input: value.tool_input,
  });
}


function response(decision, reasonCode) {
  return Object.freeze({
    hookSpecificOutput: Object.freeze({
      hookEventName: 'PreToolUse',
      permissionDecision: decision,
      permissionDecisionReason: reasonCode,
    }),
  });
}


export function evaluateHookEvent(raw, mode, env = process.env, now = Date.now()) {
  const event = parseEvent(raw, mode);
  if (mode === 'post') {
    completeBrowserCall(event.sessionId, event.toolUseId, env, now);
    return null;
  }
  if (mode === 'failure') {
    failBrowserCall(event.sessionId, event.toolUseId, 'TOOL_FAILURE', env, now);
    return null;
  }

  const active = readSingleActiveOperation(event.sessionId, env, now);
  if (!active) return response('deny', 'DENY_OPERATION_MISMATCH');
  let call;
  try {
    call = mapBrowserMcpCall(active.capability, {
      toolName: event.toolName,
      input: event.input,
    });
  } catch {
    return response('deny', 'DENY_UNKNOWN_CAPABILITY');
  }
  const policy = evaluateBrowserCall({
    event: {
      sessionId: event.sessionId,
      toolUseId: event.toolUseId,
      role: active.role,
      permissionMode: event.permissionMode,
    },
    envelope: active.envelope,
    capability: active.capability,
    binding: active,
    call,
    now,
  });
  if (policy.decision !== 'deny') {
    const staged = stageBrowserCall(event.sessionId, active.operationId, {
      toolUseId: event.toolUseId,
      action: call.action,
      effect: call.effect,
    }, env, now);
    if (!staged) return response('deny', 'DENY_OPERATION_MISMATCH');
  }
  return response(policy.decision, policy.reasonCode);
}


async function readBounded(input) {
  const chunks = [];
  let total = 0;
  for await (const chunk of input) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    total += buffer.length;
    if (total > MAX_INPUT_BYTES) throw new Error('HOOK_INPUT_TOO_LARGE');
    chunks.push(buffer);
  }
  return Buffer.concat(chunks).toString('utf8');
}


export async function main({
  mode = process.argv[2],
  input = process.stdin,
  output = process.stdout,
  error = process.stderr,
  env = process.env,
  now = Date.now(),
} = {}) {
  try {
    const raw = await readBounded(input);
    const decision = evaluateHookEvent(raw, mode, env, now);
    if (decision !== null) output.write(`${JSON.stringify(decision)}\n`);
    return 0;
  } catch {
    error.write('Browser guard denied execution because validation failed.\n');
    return 2;
  }
}


if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await main();
}
