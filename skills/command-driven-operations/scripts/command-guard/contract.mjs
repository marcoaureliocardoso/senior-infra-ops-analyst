import { EXECUTOR_AGENTS, LIMITS } from './limits.mjs';

const TOP_KEYS = new Set([
  'session_id', 'hook_event_name', 'agent_type', 'permission_mode',
  'tool_name', 'tool_input', 'transcript_path', 'cwd', 'agent_id', 'tool_use_id',
  'prompt_id', 'effort',
]);
const TOOL_KEYS = new Set(['command', 'description', 'timeout', 'run_in_background']);
const SECURITY_KEYS = new Set([...TOP_KEYS, ...TOOL_KEYS, '__proto__', 'prototype', 'constructor']);

function assertObject(value, label) {
  if (value === null || Array.isArray(value) || typeof value !== 'object') {
    throw new Error(`${label} must be an object`);
  }
}

function assertBoundedDepth(value) {
  const pending = [[value, 1]];
  while (pending.length) {
    const [current, depth] = pending.pop();
    if (depth > LIMITS.jsonDepth) throw new Error('hook JSON depth exceeds limit');
    if (current !== null && typeof current === 'object') {
      for (const child of Object.values(current)) pending.push([child, depth + 1]);
    }
  }
}

function assertUniqueSecurityKeys(raw) {
  const seen = new Set();
  const pattern = /"((?:\\.|[^"\\])*)"\s*:/g;
  for (const match of raw.matchAll(pattern)) {
    const key = JSON.parse(`"${match[1]}"`);
    if (SECURITY_KEYS.has(key) && seen.has(key)) {
      throw new Error(`duplicate key: ${key}`);
    }
    if (SECURITY_KEYS.has(key)) seen.add(key);
  }
}

function requiredString(value, label, maximum = LIMITS.auditFieldChars) {
  if (typeof value !== 'string' || value.length === 0 || value.length > maximum) {
    throw new Error(`${label} must be a non-empty bounded string`);
  }
  return value;
}

function assertObservationalScalar(value, key) {
  if (typeof value === 'string') {
    if (value.length > 0 && value.length <= LIMITS.auditFieldChars) return;
  } else if (typeof value === 'boolean') {
    return;
  } else if (typeof value === 'number' && Number.isFinite(value)) {
    return;
  }
  throw new Error(`unexpected hook field: ${key}`);
}

export function parseHookEvent(raw) {
  if (typeof raw !== 'string' || Buffer.byteLength(raw, 'utf8') > LIMITS.inputBytes) {
    throw new Error('hook input size exceeds limit');
  }
  assertUniqueSecurityKeys(raw);
  let value;
  try { value = JSON.parse(raw); } catch { throw new Error('invalid hook JSON'); }
  assertBoundedDepth(value);
  assertObject(value, 'hook event');
  for (const key of Object.keys(value)) {
    if (!TOP_KEYS.has(key)) assertObservationalScalar(value[key], key);
  }
  if (value.hook_event_name !== 'PreToolUse') throw new Error('hook event must be PreToolUse');
  if (value.tool_name !== 'Bash') throw new Error('tool name must be Bash');
  const sessionId = requiredString(value.session_id, 'session_id');
  const hasAgentType = Object.hasOwn(value, 'agent_type');
  const hasAgentId = Object.hasOwn(value, 'agent_id');
  if (!hasAgentType && hasAgentId) {
    throw new Error('agent identity fields must both be absent for the main session');
  }
  const agentType = hasAgentType ? requiredString(value.agent_type, 'agent_type') : null;
  if (agentType !== null && !EXECUTOR_AGENTS.includes(agentType)) {
    throw new Error('agent is not an executor');
  }
  const permissionMode = requiredString(value.permission_mode, 'permission_mode');
  for (const key of ['transcript_path', 'cwd', 'agent_id', 'tool_use_id']) {
    if (value[key] !== undefined) requiredString(value[key], key, LIMITS.commandChars);
  }
  if (value.prompt_id !== undefined) requiredString(value.prompt_id, 'prompt_id');
  if (value.effort !== undefined) {
    assertObject(value.effort, 'effort');
    for (const key of Object.keys(value.effort)) {
      if (key !== 'level') throw new Error(`unexpected effort field: ${key}`);
    }
    requiredString(value.effort.level, 'effort level');
  }
  assertObject(value.tool_input, 'tool_input');
  for (const key of Object.keys(value.tool_input)) {
    if (!TOOL_KEYS.has(key)) throw new Error(`unexpected tool_input field: ${key}`);
  }
  const command = requiredString(value.tool_input.command, 'command', Number.MAX_SAFE_INTEGER);
  if (command.length > LIMITS.commandChars) throw new Error('command length exceeds limit');
  if (value.tool_input.description !== undefined) {
    requiredString(value.tool_input.description, 'description', LIMITS.auditFieldChars);
  }
  if (value.tool_input.run_in_background === true) throw new Error('background execution is denied');
  if (value.tool_input.run_in_background !== undefined && value.tool_input.run_in_background !== false) {
    throw new Error('run_in_background must be false');
  }
  let timeoutMs = null;
  if (value.tool_input.timeout !== undefined) {
    if (!Number.isInteger(value.tool_input.timeout) || value.tool_input.timeout < 0 || value.tool_input.timeout > LIMITS.timeoutMs) {
      throw new Error('timeout exceeds policy');
    }
    timeoutMs = value.tool_input.timeout;
  }
  return Object.freeze({
    sessionId, agentType, permissionMode, command,
    cwd: value.cwd ?? null,
    toolUseId: value.tool_use_id ?? null,
    timeoutMs, runInBackground: false,
  });
}
