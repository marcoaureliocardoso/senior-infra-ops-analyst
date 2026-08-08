import assert from 'node:assert/strict';
import test from 'node:test';

import { lexBash } from '../../skills/command-driven-operations/scripts/command-guard/bash-lexer.mjs';
import { parseHookEvent } from '../../skills/command-driven-operations/scripts/command-guard/contract.mjs';
import { analyzeCommand } from '../../skills/command-driven-operations/scripts/command-guard/policy.mjs';
import { detectSensitiveSpans, redactText } from '../../skills/command-driven-operations/scripts/command-guard/redaction.mjs';
import { validEvent } from './helpers.mjs';

export const PROPERTY_SEEDS = Object.freeze([0x04c0ffee, 0x51a7e001, 0x7f00aa55, 0xd15ea5ed]);

function generator(seed) {
  let state = seed >>> 0;
  return () => {
    state ^= state << 13; state ^= state >>> 17; state ^= state << 5;
    return state >>> 0;
  };
}

function analyze(command) {
  return analyzeCommand(parseHookEvent(JSON.stringify(validEvent({ tool_input: { command } }))));
}

test('recorded seeds preserve deterministic fail-closed properties', () => {
  for (const seed of PROPERTY_SEEDS) {
    const next = generator(seed);
    for (let index = 0; index < 64; index += 1) {
      const suffix = (next() >>> 0).toString(16);
      const valid = `uname -a | head -n ${(next() % 20) + 1}`;
      assert.deepEqual(lexBash(valid), lexBash(valid), `seed:${seed}:iteration:${index}`);
      assert.equal(analyze(`${valid} | unknown_${suffix}`).decision, 'deny');
      assert.throws(() => lexBash(`echo $(unknown_${suffix})`), /unsupported/);
      const secret = `SYNTH_SECRET_${suffix}`;
      const source = `TOKEN=${secret} curl -q --token ${secret} https://example.invalid`;
      const redacted = redactText(source, detectSensitiveSpans(source));
      assert.equal(redactText(redacted), redacted);
      assert.doesNotMatch(JSON.stringify(analyze(source)), new RegExp(secret));
    }
  }
});

test('real separators remain operators and quoted separators remain arguments', () => {
  assert.equal(lexBash('uname | head').tokens.some(({ kind }) => kind === 'operator'), true);
  assert.equal(lexBash("printf 'a|b'").tokens.some(({ kind }) => kind === 'operator'), false);
});
