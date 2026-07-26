import assert from 'node:assert/strict';
import test from 'node:test';

import { lexBash } from '../../skills/command-driven-operations/scripts/command-guard/bash-lexer.mjs';
import { lexPowerShell } from '../../skills/command-driven-operations/scripts/command-guard/powershell-lexer.mjs';

test('bash lexer distinguishes quoted separators from pipeline operators', () => {
  const result = lexBash(`printf 'a|b' | grep b && echo done`);
  assert.deepEqual(
    result.tokens.map(({ kind, cooked }) => [kind, cooked]),
    [
      ['word', 'printf'], ['word', 'a|b'], ['operator', '|'],
      ['word', 'grep'], ['word', 'b'], ['operator', '&&'],
      ['word', 'echo'], ['word', 'done'],
    ],
  );
});

test('bash lexer rejects substitutions, background, dynamic interpreters, and controls', () => {
  for (const command of ['echo $(id)', 'echo `id`', 'sleep 1 &', 'eval whoami', 'sh -c whoami', 'xargs sh', 'echo\u0000x']) {
    assert.throws(() => lexBash(command), /unsupported|background|control/);
  }
});

test('bash lexer rejects unmatched quotes and excessive stages', () => {
  assert.throws(() => lexBash(`echo 'open`), /unmatched quote/);
  assert.throws(() => lexBash('a|b|c|d|e|f|g|h|i'), /stage limit/);
});

test('powershell lexer recognizes literal pipelines and rejects dynamic execution', () => {
  const result = lexPowerShell(`Get-Service | Where-Object Status -eq 'Running'`);
  assert.equal(result.profile, 'powershell');
  assert.equal(result.tokens.filter(({ kind }) => kind === 'operator').length, 1);
  for (const command of ['Invoke-Expression $x', 'Write-Output $(Get-Item x)', 'pwsh -EncodedCommand ZQBjAGgAbwA=']) {
    assert.throws(() => lexPowerShell(command), /unsupported/);
  }
});

test('lexing is deterministic and never expands variables or globs', () => {
  const command = 'printf "$PATH" *.log';
  assert.deepEqual(lexBash(command), lexBash(command));
  assert.equal(lexBash(command).tokens.at(-1).cooked, '*.log');
});
