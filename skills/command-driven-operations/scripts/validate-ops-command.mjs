#!/usr/bin/env node

import { pathToFileURL } from 'node:url';

import { appendAudit } from './command-guard/audit.mjs';
import {
  bindingFromResult, hasActiveBinding, writePendingBinding,
} from './command-guard/binding-store.mjs';
import { parseHookEvent } from './command-guard/contract.mjs';
import { LIMITS } from './command-guard/limits.mjs';
import { analyzeCommand } from './command-guard/policy.mjs';
import { decisionResponse } from './command-guard/response.mjs';

async function readBoundedInput(stream) {
  const chunks = [];
  let length = 0;
  for await (const chunk of stream) {
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    length += bytes.length;
    if (length > LIMITS.inputBytes) throw new Error('hook input size exceeds limit');
    chunks.push(bytes);
  }
  return new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks));
}

export function evaluateHook(raw, env = process.env) {
  const event = parseHookEvent(raw);
  let result = analyzeCommand(event);
  const binding = bindingFromResult(result, event);
  if (binding && event.permissionMode === 'bypassPermissions' && hasActiveBinding(binding, env)) {
    const cannotReuse = result.risk === 'DESTRUCTIVE' ||
      result.modifiers.includes('EXTERNAL_SIDE_EFFECT') || result.modifiers.includes('ALWAYS_ASK');
    if (!cannotReuse) {
      result = {
        ...result,
        decision: 'allow',
        reasonCode: result.risk === 'SAFE_READ_ONLY' ? 'ALLOW_NARROW_READ' : 'ALLOW_BYPASS_CATALOGUED_CHANGE',
        message: `ALLOW_APPROVED_CREDENTIAL_BINDING: ${result.policyId} uses an active non-secret session binding. Sensitive values are redacted.`,
      };
    }
  } else if (binding && result.decision === 'ask') {
    writePendingBinding(binding, env);
  }
  appendAudit(result, event, env);
  return decisionResponse(result);
}

export async function main({ input = process.stdin, output = process.stdout, error = process.stderr, env = process.env } = {}) {
  try {
    const raw = await readBoundedInput(input);
    output.write(`${JSON.stringify(evaluateHook(raw, env))}\n`);
    return 0;
  } catch {
    error.write('Command guard denied execution because validation or audit failed.\n');
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await main();
}
