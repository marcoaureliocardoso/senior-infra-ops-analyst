import assert from 'node:assert/strict';
import test from 'node:test';

import { analyzeCommand } from '../../skills/command-driven-operations/scripts/command-guard/policy.mjs';
import { parseHookEvent } from '../../skills/command-driven-operations/scripts/command-guard/contract.mjs';
import { validEvent } from './helpers.mjs';

const SECRET = 'SYNTH_SECRET_c8a22e';

function analyze(command, permissionMode = 'default') {
  return analyzeCommand(parseHookEvent(JSON.stringify(validEvent({
    permission_mode: permissionMode,
    tool_input: { command },
  }))));
}

test('literal credential raises normal decision but follows bypass operation policy', () => {
  const command = `curl -H "Authorization: Bearer ${SECRET}" https://api.example.invalid/health`;
  assert.equal(analyze(command).decision, 'ask');
  assert.equal(analyze(command, 'bypassPermissions').decision, 'allow');
});

test('credential printing, persistence, background, and unknown consumer deny', () => {
  for (const command of [
    `TOKEN=${SECRET} echo $TOKEN`,
    `TOKEN=${SECRET} printenv TOKEN`,
    `TOKEN=${SECRET} tee /tmp/token`,
    `TOKEN=${SECRET} mystery-consumer`,
  ]) assert.equal(analyze(command, 'bypassPermissions').decision, 'deny');
});

test('encrypted credential may flow only directly to a catalogued consumer', () => {
  const direct = 'gpg --decrypt sudo-password.gpg | sudo -S systemctl restart nginx';
  assert.equal(analyze(direct, 'bypassPermissions').decision, 'allow');
  assert.equal(analyze('gpg --decrypt sudo-password.gpg | tee /tmp/password').decision, 'deny');
});

test('credential metadata and messages never contain the literal value', () => {
  const result = analyze(`curl --token ${SECRET} https://api.example.invalid/health`);
  assert.doesNotMatch(JSON.stringify(result), new RegExp(SECRET));
  assert.equal(result.credential.source, 'MODEL_VISIBLE_LITERAL');
});

test('supported literal transports ask normally and follow operation policy in bypass mode', () => {
  const commands = [
    `PGPASSWORD=${SECRET} psql -h db.example.invalid -d app -c "SELECT 1"`,
    `mysql -h db.example.invalid -D app --password=${SECRET} -e "SHOW STATUS"`,
    `mongosh mongodb://user:${SECRET}@db.example.invalid/app --eval "db.serverStatus()"`,
    `curl -u user:${SECRET} https://api.example.invalid/health`,
    `curl -H "Cookie: session=${SECRET}" https://api.example.invalid/health`,
    `GH_TOKEN=${SECRET} gh repo view --repo owner/project`,
    `AWS_SECRET_ACCESS_KEY=${SECRET} aws --profile ops --region us-east-1 ec2 describe-instances`,
  ];
  for (const command of commands) {
    assert.equal(analyze(command).decision, 'ask', command);
    assert.equal(analyze(command, 'bypassPermissions').decision, 'allow', command);
    assert.doesNotMatch(JSON.stringify(analyze(command)), new RegExp(SECRET), command);
  }
});

test('provider caches and protected credential references do not become model-visible literals', () => {
  for (const command of [
    'AWS_PROFILE=ops aws --profile ops --region us-east-1 ec2 describe-instances',
    'KUBECONFIG=/secure/kubeconfig kubectl --context lab --namespace demo get pods',
    'curl --cert /secure/client.pem https://api.example.invalid/health',
    'SSH_AUTH_SOCK=/run/user/1000/agent ssh ops@example.invalid "uname -a"',
  ]) {
    const result = analyze(command);
    assert.equal(result.decision, 'allow', command);
    assert.notEqual(result.credential?.source, 'MODEL_VISIBLE_LITERAL', command);
  }
});

test('benign lookalikes are not classified as literal credentials', () => {
  for (const command of [
    'MONKEY=banana uname -a',
    'KEYSPACE=cache uname -a',
    'TOKENIZATION=enabled uname -a',
  ]) assert.equal(analyze(command).credential, null, command);
});
