#!/usr/bin/env node

import { pathToFileURL } from 'node:url';

import { activatePendingBinding } from './command-guard/binding-store.mjs';
import { lexBash } from './command-guard/bash-lexer.mjs';
import { lookupFamily } from './command-guard/catalogue.mjs';
import { buildComposition } from './command-guard/composition.mjs';
import { LIMITS } from './command-guard/limits.mjs';
import {
  activateOperation, writePendingOperation,
} from '../../browser-operations/scripts/browser-binding-store.mjs';
import { parseRunnerArgs } from '../../browser-operations/scripts/browser-runner.mjs';

function requiredString(value, field) {
  if (typeof value !== 'string' || value.length === 0 || value.length > LIMITS.commandChars) {
    throw new Error(`invalid post hook field:${field}`);
  }
  return value;
}


function browserOpenRequest(value, now) {
  const command = value.tool_input?.command;
  if (command === undefined) return null;
  if (typeof command !== 'string' || command.length < 1 || command.length > LIMITS.commandChars) {
    throw new Error('invalid post hook command');
  }
  try {
    const composition = buildComposition(lexBash(command));
    if (composition.stages.length !== 1) return null;
    const match = lookupFamily(composition.stages[0]);
    if (match?.policyId !== 'BROWSER_PROTECTED_RUNNER' || !Array.isArray(match.browserArgs)) return null;
    const request = parseRunnerArgs(match.browserArgs, now);
    return request.step === 'open' ? request : null;
  } catch {
    return null;
  }
}


function activateBrowserOpen(value, binding, env, now) {
  const request = browserOpenRequest(value, now);
  if (!request) return false;
  if (request.envelope.sessionId !== binding.sessionId
      || (value.permission_mode !== undefined
        && value.permission_mode !== request.envelope.permissionModeAtApproval)) {
    throw new Error('browser post hook binding mismatch');
  }
  const permissionModes = [...new Set([
    request.envelope.permissionModeAtApproval, 'bypassPermissions',
  ])];
  const capability = {
    state: 'ACTIVE', reasonCode: 'CAPABILITY_ACTIVE', adapterId: 'protected-runner',
    routeClass: 'PROTECTED_RUNNER', settingsFingerprint: 'browser-runner-v1',
    descriptorId: 'protected-runner-v1', serverName: null, toolPrefix: null,
    effects: ['PUBLIC_READ', 'SENSITIVE_READ', 'INTERACTIVE_STATE', 'LOW_RISK_CHANGE',
      'DISRUPTIVE_CHANGE', 'DESTRUCTIVE_CHANGE', 'SENSITIVE_ARTIFACT'],
    enforcement: {
      preCall: true, topLevelOrigin: true, redirects: true, popups: true, artifacts: true,
    },
  };
  writePendingOperation(request.envelope, {
    toolUseId: binding.toolUseId, adapterId: capability.adapterId,
    routeClass: capability.routeClass, settingsFingerprint: capability.settingsFingerprint,
    permissionModes, capability,
  }, env, now);
  return activateOperation({
    sessionId: binding.sessionId, operationId: request.operationId,
    toolUseId: binding.toolUseId,
  }, env, now);
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
  const commandBinding = activatePendingBinding(binding, env, now);
  const browserBinding = activateBrowserOpen(value, binding, env, now);
  return commandBinding || browserBinding;
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
