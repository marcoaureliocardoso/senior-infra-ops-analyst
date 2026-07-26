import assert from 'node:assert/strict';
import { Readable, Writable } from 'node:stream';
import path from 'node:path';
import test from 'node:test';

import { appendAudit, resolveAuditPath, sanitizeAuditValue } from '../../skills/command-driven-operations/scripts/command-guard/audit.mjs';
import { BASH_OPERATORS, lexBash } from '../../skills/command-driven-operations/scripts/command-guard/bash-lexer.mjs';
import { buildComposition } from '../../skills/command-driven-operations/scripts/command-guard/composition.mjs';
import { parseHookEvent } from '../../skills/command-driven-operations/scripts/command-guard/contract.mjs';
import { LIMITS } from '../../skills/command-driven-operations/scripts/command-guard/limits.mjs';
import { analyzeCommand } from '../../skills/command-driven-operations/scripts/command-guard/policy.mjs';
import { POWERSHELL_OPERATORS, lexPowerShell } from '../../skills/command-driven-operations/scripts/command-guard/powershell-lexer.mjs';
import { detectSensitiveSpans, normalizeAndFingerprint, redactText } from '../../skills/command-driven-operations/scripts/command-guard/redaction.mjs';
import { decisionResponse } from '../../skills/command-driven-operations/scripts/command-guard/response.mjs';
import { main } from '../../skills/command-driven-operations/scripts/validate-ops-command.mjs';
import { temporaryAudit, validEvent } from './helpers.mjs';

function event(overrides = {}) {
  return JSON.stringify(validEvent(overrides));
}

function policy(command, permissionMode = 'default') {
  return analyzeCommand(parseHookEvent(event({ permission_mode: permissionMode, tool_input: { command } })));
}

test('contract rejects every malformed field branch and accepts exact boundaries', () => {
  const invalid = [
    [null, /size/],
    ['x'.repeat(LIMITS.inputBytes + 1), /size/],
    ['{', /JSON/],
    ['[]', /object/],
    [event({ extra: true }), /unexpected hook field/],
    [event({ hook_event_name: 'PostToolUse' }), /PreToolUse/],
    [event({ tool_name: 'Read' }), /Bash/],
    [event({ session_id: '' }), /session_id/],
    [event({ session_id: 'x'.repeat(LIMITS.auditFieldChars + 1) }), /session_id/],
    [event({ agent_type: 'analysis-reasoning-specialist' }), /executor/],
    [event({ permission_mode: '' }), /permission_mode/],
    [event({ tool_input: null }), /tool_input.*object/],
    [event({ tool_input: [] }), /tool_input.*object/],
    [event({ tool_input: { command: 'uname', extra: true } }), /unexpected tool_input/],
    [event({ tool_input: { command: '' } }), /command/],
    [event({ tool_input: { command: 1 } }), /command/],
    [event({ tool_input: { command: 'uname', run_in_background: 'false' } }), /run_in_background/],
    [event({ tool_input: { command: 'uname', timeout: 1.5 } }), /timeout/],
    [event({ tool_input: { command: 'uname', timeout: -1 } }), /timeout/],
  ];
  for (const [raw, message] of invalid) assert.throws(() => parseHookEvent(raw), message);
  assert.equal(parseHookEvent(event({ tool_input: { command: 'uname', timeout: LIMITS.timeoutMs, run_in_background: false } })).timeoutMs, LIMITS.timeoutMs);
});

test('audit sanitizer covers primitives, arrays, forbidden keys, and both path branches', () => {
  assert.equal(sanitizeAuditValue(undefined), null);
  assert.equal(sanitizeAuditValue(null), null);
  assert.deepEqual(sanitizeAuditValue([1, null, { safe: true }]), [1, null, { safe: true }]);
  assert.throws(() => sanitizeAuditValue({ nested: { authorization: 'synthetic' } }), /forbidden audit field/);
  assert.equal(resolveAuditPath({ OPS_COMMAND_GUARD_AUDIT_PATH: './audit.jsonl' }), path.resolve('audit.jsonl'));
  assert.equal(resolveAuditPath({}, 'C:\\synthetic-home'), path.join('C:\\synthetic-home', '.claude', 'senior-infra-ops-analyst', 'command-guard-audit.jsonl'));
});

test('audit fallbacks and default environment contain only the minimal schema', async () => {
  const temporary = await temporaryAudit();
  const previous = process.env.OPS_COMMAND_GUARD_AUDIT_PATH;
  process.env.OPS_COMMAND_GUARD_AUDIT_PATH = temporary.auditPath;
  try {
    appendAudit(
      { decision: 'deny', reasonCode: 'DENY_SYNTHETIC' },
      { sessionId: 's', agentType: 'diagnostic-operator', permissionMode: 'default' },
    );
    const record = JSON.parse((await temporary.read()).trim());
    assert.equal(record.risk, null);
    assert.deepEqual(record.modifiers, []);
    assert.equal(record.credential, null);
  } finally {
    if (previous === undefined) delete process.env.OPS_COMMAND_GUARD_AUDIT_PATH;
    else process.env.OPS_COMMAND_GUARD_AUDIT_PATH = previous;
    await temporary.cleanup();
  }
});

test('Bash lexer covers every operator, escape, quote, and finite bound branch', () => {
  for (const operator of BASH_OPERATORS) {
    const command = operator === '2>&1' ? `a ${operator}` : operator.includes('>') || operator === '<' ? `a ${operator} sink` : `a ${operator} b`;
    assert.ok(lexBash(command).tokens.some(({ cooked }) => cooked === operator), JSON.stringify(operator));
  }
  assert.equal(lexBash('  echo a\\ b').tokens.at(-1).cooked, 'a b');
  assert.equal(lexBash("echo 'a\\b'").tokens.at(-1).cooked, 'a\\b');
  assert.equal(lexBash(`echo "a'b"`).tokens.at(-1).cooked, "a'b");
  assert.throws(() => lexBash('echo trailing\\'), /unmatched/);
  assert.throws(() => lexBash('ab', { ...LIMITS, tokenChars: 1 }), /token limit/);
  assert.throws(() => lexBash('a b', { ...LIMITS, tokens: 1 }), /token limit/);
});

test('PowerShell lexer covers every operator, escape, quote, control, and bound branch', () => {
  for (const operator of POWERSHELL_OPERATORS) {
    const command = operator.includes('>') ? `a ${operator} sink` : `a ${operator} b`;
    assert.ok(lexPowerShell(command).tokens.some(({ cooked }) => cooked === operator), JSON.stringify(operator));
  }
  for (const command of ['$(Get-Item x)', 'Invoke-Expression x', 'pwsh -EncodedCommand eA==', 'a --% b', '{x}', 'a & b']) assert.throws(() => lexPowerShell(command), /unsupported/);
  assert.throws(() => lexPowerShell('a\u0000b'), /control/);
  assert.equal(lexPowerShell('  echo a` b').tokens.at(-1).cooked, 'a b');
  assert.equal(lexPowerShell("echo 'a`b'").tokens.at(-1).cooked, 'a`b');
  assert.equal(lexPowerShell(`echo "a'b"`).tokens.at(-1).cooked, "a'b");
  assert.throws(() => lexPowerShell('echo trailing`'), /unmatched/);
  assert.throws(() => lexPowerShell('a b', { ...LIMITS, tokens: 1 }), /token limit/);
  assert.throws(() => lexPowerShell('a|b|c', { ...LIMITS, stages: 2 }), /stage limit/);
});

test('composition covers empty, missing redirect, words, redirects, and sequence edges', () => {
  assert.throws(() => buildComposition(lexBash('')), /empty command stage/);
  assert.throws(() => buildComposition(lexBash('uname >')), /destination/);
  const graph = buildComposition(lexBash('uname > /dev/null ; uptime'));
  assert.equal(graph.stages.length, 2);
  assert.equal(graph.redirects.length, 1);
  assert.deepEqual(graph.edges, [{ from: 1, to: 2, operator: ';' }]);
});

test('redaction covers every literal transport, overlap filtering, empty input, and idempotence', () => {
  const secret = 'SYNTH_SECRET_branch';
  const fixtures = [
    `Authorization: Bearer ${secret}`,
    `Cookie: session=${secret}`,
    `TOKEN=${secret}`,
    `--password=${secret}`,
    `-u user:${secret}`,
    `ConvertTo-SecureString '${secret}' -AsPlainText`,
    `https://user:${secret}@example.invalid`,
  ];
  for (const fixture of fixtures) assert.doesNotMatch(redactText(fixture), new RegExp(secret), fixture);
  assert.deepEqual(detectSensitiveSpans('MONKEY=banana'), []);
  assert.equal(detectSensitiveSpans(`Authorization: Bearer TOKEN=${secret}`).length, 1);
  assert.equal(redactText('plain', []), 'plain');
  const normalized = normalizeAndFingerprint('  uname   -a  ', []);
  assert.equal(normalized.normalized, 'uname -a');
  assert.match(normalized.fingerprint, /^[a-f0-9]{64}$/u);
});

test('policy covers discard redirects, first-stage filters, wrapper failure, and all normal modes', () => {
  assert.equal(policy('uname > /dev/null').decision, 'allow');
  assert.equal(policy('uname 2>&1').decision, 'allow');
  assert.equal(policy('grep x').decision, 'deny');
  assert.equal(policy('   ').decision, 'deny');
  assert.equal(policy('pwsh -NoProfile').decision, 'deny');
  assert.equal(policy('pwsh -Command').decision, 'deny');
  assert.equal(policy('TOKEN=synthetic curl https://example.invalid > output.log').reasonCode, 'DENY_SECRET_PERSISTENCE');
  for (const mode of ['default', 'plan', 'acceptEdits', 'auto', 'dontAsk']) assert.equal(policy('systemctl restart nginx', mode).decision, 'ask');
  const runtimeReference = policy('uname "$TOKEN"');
  assert.equal(runtimeReference.decision, 'allow');
  assert.equal(runtimeReference.credential.source, 'RUNTIME_VARIABLE');
  assert.equal(policy('uname | kubectl --context lab --namespace demo delete pod demo-0').decision, 'ask');
});

test('native response covers allow, ask, deny, and invalid decisions', () => {
  for (const decision of ['allow', 'ask', 'deny']) {
    const response = decisionResponse({ decision, message: `${decision}: redacted` });
    assert.equal(response.hookSpecificOutput.permissionDecision, decision);
    assert.equal('systemMessage' in response, decision === 'deny');
  }
  assert.throws(() => decisionResponse({ decision: 'maybe', message: 'x' }), /invalid decision/);
});

test('entrypoint main covers string chunks, bounded-reader failure, and injected streams', async () => {
  const temporary = await temporaryAudit();
  try {
    let stdout = ''; let stderr = '';
    const output = new Writable({ write(chunk, encoding, callback) { stdout += chunk.toString(); callback(); } });
    const error = new Writable({ write(chunk, encoding, callback) { stderr += chunk.toString(); callback(); } });
    assert.equal(await main({ input: Readable.from([event()]), output, error, env: { OPS_COMMAND_GUARD_AUDIT_PATH: temporary.auditPath } }), 0);
    assert.equal(JSON.parse(stdout).hookSpecificOutput.permissionDecision, 'allow');
    assert.equal(stderr, '');

    stdout = ''; stderr = '';
    assert.equal(await main({ input: Readable.from([Buffer.alloc(LIMITS.inputBytes + 1)]), output, error, env: { OPS_COMMAND_GUARD_AUDIT_PATH: temporary.auditPath } }), 2);
    assert.equal(stdout, '');
    assert.match(stderr, /denied/);
  } finally {
    await temporary.cleanup();
  }
});
