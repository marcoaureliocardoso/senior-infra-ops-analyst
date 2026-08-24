import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

import {
  EXECUTOR_AGENTS,
  LIMITS,
} from '../../skills/command-driven-operations/scripts/command-guard/limits.mjs';
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

test('ordinary main-session payload is identified by absent optional agent fields', () => {
  const payload = validEvent({ permission_mode: 'default' });
  delete payload.agent_type;
  delete payload.agent_id;
  const event = parseHookEvent(JSON.stringify(payload));
  assert.equal(event.agentType, null);
  assert.equal(event.permissionMode, 'default');

  payload.permission_mode = 'bypassPermissions';
  assert.equal(parseHookEvent(JSON.stringify(payload)).agentType, null);
});

test('partial synthetic and unknown agent identities fail closed', () => {
  const mainWithAgentId = validEvent({ agent_id: 'agent-main' });
  delete mainWithAgentId.agent_type;
  assert.throws(
    () => parseHookEvent(JSON.stringify(mainWithAgentId)),
    /agent identity fields must both be present or both be absent/,
  );
  for (const agentType of EXECUTOR_AGENTS) {
    const executorWithoutAgentId = validEvent({ agent_type: agentType });
    delete executorWithoutAgentId.agent_id;
    assert.throws(
      () => parseHookEvent(JSON.stringify(executorWithoutAgentId)),
      /agent identity fields must both be present or both be absent/,
    );
  }
  for (const agentType of ['main-session', 'ordinary-main-session', 'unknown-executor']) {
    assert.throws(
      () => parseHookEvent(JSON.stringify(validEvent({ agent_type: agentType }))),
      /agent is not an executor/,
    );
  }
});

test('live-stage audit nonce is exact, bounded, and content-free', async () => {
  const temporary = await temporaryAudit();
  try {
    appendAudit(
      {
        policyId: null, risk: null, modifiers: [], target: null,
        environment: null, scope: null, credential: null,
        decision: 'deny', reasonCode: 'DENY_UNKNOWN_COMMAND', stage: 1, findings: [],
      },
      { sessionId: 'session', agentType: null, permissionMode: 'default' },
      {
        OPS_COMMAND_GUARD_AUDIT_PATH: temporary.auditPath,
        P005_LIVE_STAGE_NONCE: '0123456789abcdef0123456789abcdef',
      },
    );
    const record = JSON.parse(await readFile(temporary.auditPath, 'utf8'));
    assert.equal(record.probeNonce, '0123456789abcdef0123456789abcdef');
    for (const invalid of ['', 'A'.repeat(32), 'a'.repeat(31), 'a'.repeat(33), 'not-a-nonce']) {
      assert.throws(
        () => appendAudit(
          {
            policyId: null, risk: null, modifiers: [], target: null,
            environment: null, scope: null, credential: null,
            decision: 'deny', reasonCode: 'DENY_UNKNOWN_COMMAND', stage: 1, findings: [],
          },
          { sessionId: 'session', agentType: null, permissionMode: 'default' },
          {
            OPS_COMMAND_GUARD_AUDIT_PATH: temporary.auditPath,
            P005_LIVE_STAGE_NONCE: invalid,
          },
        ),
        /invalid live stage nonce/,
      );
    }
  } finally {
    await temporary.cleanup();
  }
});

test('all catalogued executor identities retain the existing native contract', () => {
  for (const agentType of EXECUTOR_AGENTS) {
    const parsed = parseHookEvent(JSON.stringify(validEvent({ agent_type: agentType })));
    assert.equal(parsed.agentType, agentType);
  }
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
