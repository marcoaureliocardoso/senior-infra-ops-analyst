#!/usr/bin/env node

import { pathToFileURL } from 'node:url';

import { activatePendingBinding } from './command-guard/binding-store.mjs';
import { LIMITS } from './command-guard/limits.mjs';

function requiredString(value, field) {
  if (typeof value !== 'string' || value.length === 0 || value.length > LIMITS.commandChars) {
    throw new Error(`invalid post hook field:${field}`);
  }
  return value;
}

export function evaluateApprovalHook(raw, env = process.env, now = Date.now()) {
  if (typeof raw !== 'string' || Buffer.byteLength(raw, 'utf8') > LIMITS.inputBytes) throw new Error('post hook input exceeds limit');
  const value = JSON.parse(raw);
  if (value === null || Array.isArray(value) || typeof value !== 'object') throw new Error('post hook must be an object');
  if (value.hook_event_name !== 'PostToolUse' || value.tool_name !== 'Bash') throw new Error('post hook identity mismatch');
  const binding = {
    sessionId: requiredString(value.session_id, 'session_id'),
    toolUseId: requiredString(value.tool_use_id, 'tool_use_id'),
  };
  return activatePendingBinding(binding, env, now);
}

async function readInput(stream) {
  const chunks = [];
  let size = 0;
  for await (const chunk of stream) {
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += bytes.length;
    if (size > LIMITS.inputBytes) throw new Error('post hook input exceeds limit');
    chunks.push(bytes);
  }
  return new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks));
}

export async function main({ input = process.stdin, error = process.stderr, env = process.env } = {}) {
  try {
    evaluateApprovalHook(await readInput(input), env);
    return 0;
  } catch {
    error.write('Command guard did not activate credential reuse.\n');
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await main();
}
