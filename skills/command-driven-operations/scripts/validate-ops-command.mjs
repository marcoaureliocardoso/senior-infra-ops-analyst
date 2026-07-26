#!/usr/bin/env node

import { pathToFileURL } from 'node:url';

import { appendAudit } from './command-guard/audit.mjs';
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
  const result = analyzeCommand(event);
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
