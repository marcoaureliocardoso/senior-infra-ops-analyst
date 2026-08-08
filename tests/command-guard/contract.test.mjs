import assert from 'node:assert/strict';
import test from 'node:test';

import { LIMITS } from '../../skills/command-driven-operations/scripts/command-guard/limits.mjs';
import { parseHookEvent } from '../../skills/command-driven-operations/scripts/command-guard/contract.mjs';
import {
  detectSensitiveSpans,
  normalizeAndFingerprint,
  redactText,
} from '../../skills/command-driven-operations/scripts/command-guard/redaction.mjs';
import { decisionResponse } from '../../skills/command-driven-operations/scripts/command-guard/response.mjs';
import { appendAudit } from '../../skills/command-driven-operations/scripts/command-guard/audit.mjs';
import { temporaryAudit, validEvent } from './helpers.mjs';

test('valid hook event is normalized to the guard contract', () => {
  const parsed = parseHookEvent(JSON.stringify(validEvent()));
  assert.deepEqual(parsed, {
    sessionId: 'session-synthetic-001',
    agentType: 'diagnostic-operator',
    permissionMode: 'default',
    command: 'uname -a',
    cwd: null,
    toolUseId: null,
    timeoutMs: null,
    runInBackground: false,
  });
});

test('hook contract preserves bounded cwd for effect binding', () => {
  assert.equal(parseHookEvent(JSON.stringify(validEvent({ cwd: '/srv/project' }))).cwd, '/srv/project');
  assert.equal(parseHookEvent(JSON.stringify(validEvent())).cwd, null);
});

test('current native PreToolUse Bash payload accepts documented common fields', () => {
  const event = parseHookEvent(JSON.stringify({
    session_id: 'session-native',
    transcript_path: '/tmp/transcript.jsonl',
    cwd: '/srv/project',
    prompt_id: 'prompt-42',
    permission_mode: 'bypassPermissions',
    effort: { level: 'high' },
    agent_id: 'agent-17',
    agent_type: 'diagnostic-operator',
    hook_event_name: 'PreToolUse',
    tool_name: 'Bash',
    tool_use_id: 'toolu_01ABC',
    tool_input: {
      command: 'uname -a',
      description: 'Inspect kernel identity',
      timeout: 5000,
      run_in_background: false,
    },
  }));
  assert.equal(event.command, 'uname -a');
  assert.equal(event.agentType, 'diagnostic-operator');
});

test('current and future observational metadata is bounded without gating execution', () => {
  for (const level of ['low', 'medium', 'high', 'xhigh', 'max', 'ultra', 'future-effort']) {
    assert.doesNotThrow(() => parseHookEvent(JSON.stringify(validEvent({
      prompt_id: 'prompt-bounded',
      effort: { level },
      future_string: 'bounded',
      future_boolean: true,
      future_number: 42,
    }))));
  }
  const invalid = [
    { prompt_id: '' },
    { prompt_id: 42 },
    { prompt_id: 'x'.repeat(LIMITS.auditFieldChars + 1) },
    { effort: null },
    { effort: [] },
    { effort: {} },
    { effort: { level: 'high', extra: true } },
    { future_object: {} },
    { future_array: [] },
    { future_null: null },
    { future_number: Number.POSITIVE_INFINITY },
    { future_string: 'x'.repeat(LIMITS.auditFieldChars + 1) },
  ];
  for (const extra of invalid) {
    assert.throws(() => parseHookEvent(JSON.stringify(validEvent(extra))), /prompt_id|effort|unexpected hook field/);
  }
});

test('duplicate security key is rejected before JSON semantics can overwrite it', () => {
  const raw = '{"session_id":"a","session_id":"b","hook_event_name":"PreToolUse","agent_type":"diagnostic-operator","permission_mode":"default","tool_name":"Bash","tool_input":{"command":"uname"}}';
  assert.throws(() => parseHookEvent(raw), /duplicate key: session_id/);
});

test('background and over-limit commands are rejected', () => {
  assert.throws(
    () => parseHookEvent(JSON.stringify(validEvent({ tool_input: { command: 'uname', run_in_background: true } }))),
    /background execution/,
  );
  assert.throws(
    () => parseHookEvent(JSON.stringify(validEvent({ tool_input: { command: 'x'.repeat(LIMITS.commandChars + 1) } }))),
    /command length/,
  );
});

test('JSON depth, timeout, and redirect bounds fail closed at n plus one', () => {
  let nested = {};
  for (let index = 0; index <= LIMITS.jsonDepth; index += 1) nested = { child: nested };
  assert.throws(() => parseHookEvent(JSON.stringify(nested)), /depth/);
  assert.throws(
    () => parseHookEvent(JSON.stringify(validEvent({ tool_input: { command: 'uname', timeout: LIMITS.timeoutMs + 1 } }))),
    /timeout/,
  );
});

test('literal credential is redacted before normalization and fingerprinting', () => {
  const secret = 'SYNTH_SECRET_4f0a7c';
  const command = `curl -q -H "Authorization: Bearer ${secret}" https://example.invalid`;
  const spans = detectSensitiveSpans(command);
  const redacted = redactText(command, spans);
  const normalized = normalizeAndFingerprint(command, spans);
  assert.match(redacted, /<redacted:AUTHORIZATION>/);
  assert.doesNotMatch(redacted, new RegExp(secret));
  assert.doesNotMatch(normalized.normalized, new RegExp(secret));
  assert.match(normalized.fingerprint, /^[a-f0-9]{64}$/);
});

test('deny response is operator-visible and contains no raw command field', () => {
  const response = decisionResponse({
    decision: 'deny',
    reasonCode: 'DENY_UNKNOWN_COMMAND',
    message: 'DENY_UNKNOWN_COMMAND: stage 1 is not catalogued.',
  });
  assert.equal(response.systemMessage, 'DENY_UNKNOWN_COMMAND: stage 1 is not catalogued.');
  assert.equal(response.hookSpecificOutput.permissionDecision, 'deny');
  assert.equal(response.hookSpecificOutput.hookEventName, 'PreToolUse');
  assert.equal('command' in response, false);
});

test('audit is append-only minimal metadata without a synthetic secret', async () => {
  const temporary = await temporaryAudit();
  try {
    appendAudit(
      {
        decision: 'ask', reasonCode: 'ASK_LITERAL_CREDENTIAL_NORMAL',
        message: 'redacted', risk: 'LOW_RISK_CHANGE', modifiers: ['SENSITIVE_OUTPUT'],
        policyId: 'HTTP', target: 'https://example.invalid', environment: null,
        scope: 'one-origin', credential: { source: 'MODEL_VISIBLE_LITERAL', type: 'TOKEN', transport: 'HEADER' },
        fingerprint: 'a'.repeat(64), stage: 1,
      },
      parseHookEvent(JSON.stringify(validEvent())),
      { OPS_COMMAND_GUARD_AUDIT_PATH: temporary.auditPath },
    );
    const audit = await temporary.read();
    assert.match(audit, /ASK_LITERAL_CREDENTIAL_NORMAL/);
    assert.doesNotMatch(audit, /SYNTH_SECRET/);
    assert.doesNotMatch(audit, /"command"/);
  } finally {
    await temporary.cleanup();
  }
});
