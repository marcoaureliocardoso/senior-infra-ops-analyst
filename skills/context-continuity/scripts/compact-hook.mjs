import { pathToFileURL } from 'node:url';

import {
  invalidateAllBindings,
  invalidateSessionBindings,
} from '../../command-driven-operations/scripts/command-guard/binding-store.mjs';
import { parseStrictObject } from './settings.mjs';


const MAX_INPUT_BYTES = 64 * 1024;
const SESSION_PATTERN = /^[A-Za-z0-9._:-]{1,512}$/u;
const PHASES = Object.freeze({ pre: 'PreCompact', post: 'PostCompact' });
const DEGRADED_WARNING = 'Context continuity degraded. Credential reuse requires fresh approval.\n';


function boundedIdentity(value, field) {
  if (typeof value !== 'string' || !SESSION_PATTERN.test(value)) {
    throw new Error(`invalid compact ${field}`);
  }
  return value;
}


export function parseCompactEnvelope(raw, expectedPhase) {
  if (!Object.values(PHASES).includes(expectedPhase)) throw new Error('invalid compact phase');
  if (typeof raw !== 'string' || Buffer.byteLength(raw, 'utf8') > MAX_INPUT_BYTES) {
    throw new Error('compact hook input exceeds limit');
  }
  const event = parseStrictObject(raw, 'compact hook input');
  if (event.hook_event_name !== expectedPhase) throw new Error('unexpected compact hook event');
  if (event.trigger !== 'manual' && event.trigger !== 'auto') throw new Error('invalid compact trigger');
  return Object.freeze({
    sessionId: boundedIdentity(event.session_id, 'session identity'),
    trigger: event.trigger,
  });
}


export function evaluateCompactHook(raw, phase, env = process.env) {
  const envelope = parseCompactEnvelope(raw, phase);
  invalidateSessionBindings(envelope.sessionId, env);
  return Object.freeze({ phase, invalidated: true, degraded: false });
}


async function readBounded(stream) {
  const chunks = [];
  let size = 0;
  for await (const chunk of stream) {
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += bytes.length;
    if (size > MAX_INPUT_BYTES) throw new Error('compact hook input exceeds limit');
    chunks.push(bytes);
  }
  return new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks));
}


export async function main({
  args = process.argv.slice(2),
  input = process.stdin,
  output: _output = process.stdout,
  error = process.stderr,
  env = process.env,
} = {}) {
  try {
    const phase = PHASES[args[0]];
    if (!phase || args.length !== 1) throw new Error('invalid compact hook invocation');
    evaluateCompactHook(await readBounded(input), phase, env);
  } catch {
    try {
      invalidateAllBindings(env);
    } catch {
      // A failed fail-safe must not block Claude Code's own compaction.
    }
    error.write(DEGRADED_WARNING);
  }
  return 0;
}


if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await main();
}
