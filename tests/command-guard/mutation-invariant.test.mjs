import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import test from 'node:test';

import { validEvent } from './helpers.mjs';

const root = process.env.COMMAND_GUARD_MUTANT_ROOT;
const mutationId = process.env.COMMAND_GUARD_MUTATION_ID;

function moduleUrl(file) {
  return `${pathToFileURL(path.join(root, 'command-guard', file)).href}?mutation=${mutationId}`;
}

async function policyFixture(command, permissionMode = 'bypassPermissions') {
  const { parseHookEvent } = await import(moduleUrl('contract.mjs'));
  const { analyzeCommand } = await import(moduleUrl('policy.mjs'));
  return analyzeCommand(parseHookEvent(JSON.stringify(validEvent({ permission_mode: permissionMode, tool_input: { command } }))));
}

test('registered mutation is killed by its dedicated security invariant', { skip: !root }, async () => {
  switch (mutationId) {
    case 'CONTRACT_BACKGROUND_REJECT': {
      const { parseHookEvent } = await import(moduleUrl('contract.mjs'));
      assert.throws(
        () => parseHookEvent(JSON.stringify(validEvent({ tool_input: { command: 'uname', run_in_background: true } }))),
        /background execution is denied/,
      );
      break;
    }
    case 'CONTRACT_COMMAND_BOUND': {
      const { LIMITS } = await import(moduleUrl('limits.mjs'));
      const { parseHookEvent } = await import(moduleUrl('contract.mjs'));
      assert.throws(() => parseHookEvent(JSON.stringify(validEvent({ tool_input: { command: 'x'.repeat(LIMITS.commandChars + 1) } }))));
      break;
    }
    case 'LEXER_DYNAMIC_REJECT': {
      const { lexBash } = await import(moduleUrl('bash-lexer.mjs'));
      assert.throws(() => lexBash('echo $(id)'));
      break;
    }
    case 'POLICY_UNKNOWN_REJECT':
      assert.equal((await policyFixture('unknown-command')).decision, 'deny');
      break;
    case 'POLICY_TARGET_REQUIRED':
      assert.equal((await policyFixture('kubectl scale deployment api --replicas 0')).decision, 'deny');
      break;
    case 'POLICY_DESTRUCTIVE_ALWAYS_ASK':
      assert.equal((await policyFixture('kubectl --context lab --namespace demo delete pod demo-0')).decision, 'ask');
      break;
    case 'POLICY_RISK_ESCALATION':
      assert.equal((await policyFixture('uname | kubectl --context lab --namespace demo delete pod demo-0')).decision, 'ask');
      break;
    case 'CREDENTIAL_UNSAFE_SINK_REJECT': {
      const result = await policyFixture('TOKEN=SYNTH_SECRET_mutation echo $TOKEN');
      assert.equal(result.decision, 'deny');
      assert.equal(result.reasonCode, 'DENY_SECRET_OUTPUT');
      break;
    }
    case 'REDACTION_AUTHORIZATION': {
      const { detectSensitiveSpans, redactText } = await import(moduleUrl('redaction.mjs'));
      const secret = 'SYNTH_SECRET_mutation';
      assert.doesNotMatch(redactText(`Authorization: Bearer ${secret}`, detectSensitiveSpans(`Authorization: Bearer ${secret}`)), new RegExp(secret));
      break;
    }
    case 'AUDIT_FORBIDDEN_FIELD_REJECT': {
      const { appendAudit } = await import(moduleUrl('audit.mjs'));
      assert.throws(() => appendAudit({ decision: 'deny', reasonCode: 'x', credential: { token: 'synthetic' } }, { sessionId: 's', agentType: 'diagnostic-operator', permissionMode: 'default' }, { OPS_COMMAND_GUARD_AUDIT_PATH: path.join(root, 'audit.jsonl') }));
      break;
    }
    case 'ENTRYPOINT_CATCH_EXIT': {
      const code = await new Promise((resolve, reject) => {
        const child = spawn(process.execPath, [path.join(root, 'validate-ops-command.mjs')], { stdio: ['pipe', 'ignore', 'ignore'] });
        child.on('error', reject); child.on('close', resolve); child.stdin.end('{');
      });
      assert.equal(code, 2);
      break;
    }
    default:
      assert.fail(`unknown mutation: ${mutationId}`);
  }
});
