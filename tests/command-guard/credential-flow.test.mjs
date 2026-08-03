import assert from 'node:assert/strict';
import test from 'node:test';

import { analyzeCommand } from '../../skills/command-driven-operations/scripts/command-guard/policy.mjs';
import { parseHookEvent } from '../../skills/command-driven-operations/scripts/command-guard/contract.mjs';
import { redactText } from '../../skills/command-driven-operations/scripts/command-guard/redaction.mjs';
import { validEvent } from './helpers.mjs';

const SECRET = 'SYNTH_SECRET_c8a22e';

function analyze(command, permissionMode = 'default') {
  return analyzeCommand(parseHookEvent(JSON.stringify(validEvent({
    permission_mode: permissionMode,
    tool_input: { command },
  }))));
}

test('first literal credential use asks in every permission mode', () => {
  const command = `curl -H "Authorization: Bearer ${SECRET}" https://api.example.invalid/health`;
  assert.equal(analyze(command).decision, 'ask');
  assert.equal(analyze(command, 'bypassPermissions').decision, 'ask');
});

test('credential printing, persistence, background, and unknown consumer deny', () => {
  for (const command of [
    `TOKEN=${SECRET} echo $TOKEN`,
    `TOKEN=${SECRET} printenv TOKEN`,
    `TOKEN=${SECRET} tee /tmp/token`,
    `TOKEN=${SECRET} mystery-consumer`,
  ]) assert.equal(analyze(command, 'bypassPermissions').decision, 'deny');
});

test('literal credential ownership requires the catalogued invocation to consume its transport', () => {
  for (const command of [
    `OPS_CREDENTIAL_IDENTITY=operator SSHPASS=${SECRET} sudo systemctl restart nginx`,
    `OPS_CREDENTIAL_IDENTITY=operator SSHPASS=${SECRET} sudo -S systemctl restart nginx`,
    `GH_TOKEN=${SECRET} gpg --decrypt credential.gpg`,
    `GH_TOKEN=${SECRET} age --decrypt credential.age`,
    `GH_TOKEN=${SECRET} curl https://api.example.invalid/health`,
    `GH_TOKEN=${SECRET} aws --profile ops --region us-east-1 ec2 describe-instances --max-items 20`,
    `AWS_SECRET_ACCESS_KEY=${SECRET} gh repo view --repo owner/project`,
    `PGPASSWORD=${SECRET} mysql -h db.example.invalid -P 3306 -u appuser -D app -e "SHOW STATUS"`,
    `MYSQL_PWD=${SECRET} psql -h db.example.invalid -p 5432 -U appuser -d app -c "SELECT 1"`,
  ]) {
    const result = analyze(command, 'bypassPermissions');
    assert.equal(result.decision, 'deny', command);
    assert.equal(result.reasonCode, 'DENY_UNKNOWN_CREDENTIAL_CONSUMER', command);
    assert.doesNotMatch(JSON.stringify(result), new RegExp(SECRET), command);
  }
});

test('literal credentials distributed across composition stages deny', () => {
  const command =
    'OPS_CREDENTIAL_IDENTITY=operator curl -H "Authorization: Bearer SYNTH_SECRET_stage_a" https://api.example.invalid/a ; ' +
    'OPS_CREDENTIAL_IDENTITY=operator curl -H "Authorization: Bearer SYNTH_SECRET_stage_b" https://api.example.invalid/b';
  const result = analyze(command, 'bypassPermissions');
  assert.equal(result.decision, 'deny');
  assert.equal(result.reasonCode, 'DENY_UNKNOWN_CREDENTIAL_CONSUMER');
  assert.doesNotMatch(JSON.stringify(result), /SYNTH_SECRET_/u);
});

test('encrypted credential may flow only directly to a catalogued consumer', () => {
  const direct = 'gpg --decrypt sudo-password.gpg | sudo -S systemctl restart nginx';
  assert.equal(analyze(direct, 'bypassPermissions').decision, 'allow');
  const remote = 'age --decrypt ssh-password.age | sshpass -d 0 ssh ops@example.invalid "uname -a"';
  assert.equal(analyze(remote, 'bypassPermissions').decision, 'allow');
  const passphrase = `gpg --batch --pinentry-mode loopback --passphrase ${SECRET} --decrypt sudo-password.gpg | sudo -S systemctl restart nginx`;
  const passphraseResult = analyze(passphrase, 'bypassPermissions');
  assert.equal(passphraseResult.decision, 'ask');
  assert.doesNotMatch(JSON.stringify(passphraseResult), new RegExp(SECRET));
  assert.equal(analyze('gpg --decrypt sudo-password.gpg | tee /tmp/password').decision, 'deny');
  assert.equal(analyze('gpg --encrypt plaintext | sudo -S systemctl restart nginx').decision, 'deny');
  for (const command of [
    'gpg --decrypt sudo-password.gpg ; sudo -S systemctl restart nginx',
    'gpg --decrypt sudo-password.gpg |& sudo -S systemctl restart nginx',
    'gpg --decrypt sudo-password.gpg | sudo -S systemctl restart nginx | head -n 1',
    'gpg --decrypt sudo-password.gpg > /tmp/password | sudo -S systemctl restart nginx',
    'sudo -S systemctl restart nginx | gpg --decrypt sudo-password.gpg',
  ]) assert.equal(analyze(command, 'bypassPermissions').decision, 'deny', command);
});

test('credential metadata and messages never contain the literal value', () => {
  const result = analyze(`curl --token ${SECRET} https://api.example.invalid/health`);
  assert.doesNotMatch(JSON.stringify(result), new RegExp(SECRET));
  assert.equal(result.credential.source, 'MODEL_VISIBLE_LITERAL');
});

test('supported literal transports ask on first use in every mode', () => {
  const commands = [
    `PGPASSWORD=${SECRET} psql -h db.example.invalid -p 5432 -U appuser -d app -c "SELECT 1"`,
    `mysql -h db.example.invalid -P 3306 -u appuser -D app --password=${SECRET} -e "SHOW STATUS"`,
    `mongosh mongodb://user:${SECRET}@db.example.invalid/app --eval "db.serverStatus()"`,
    `curl -u user:${SECRET} https://api.example.invalid/health`,
    `curl -H "Cookie: session=${SECRET}" https://api.example.invalid/health`,
    `GH_TOKEN=${SECRET} gh repo view --repo owner/project`,
    `AWS_SECRET_ACCESS_KEY=${SECRET} aws --profile ops --region us-east-1 ec2 describe-instances --max-items 20`,
  ];
  for (const command of commands) {
    assert.equal(analyze(command).decision, 'ask', command);
    assert.equal(analyze(command, 'bypassPermissions').decision, 'ask', command);
    assert.doesNotMatch(JSON.stringify(analyze(command)), new RegExp(SECRET), command);
  }
});

test('catalogued client credential spellings always ask and preserve transport', () => {
  const cases = [
    [`curl --oauth2-bearer ${SECRET} https://api.example.invalid/health`, 'FLAG'],
    [`curl -uuser:${SECRET} https://api.example.invalid/health`, 'BASIC_AUTH'],
    [`curl --user=user:${SECRET} https://api.example.invalid/health`, 'BASIC_AUTH'],
    [`curl -H "Authorization: Token ${SECRET}" https://api.example.invalid/health`, 'AUTHORIZATION'],
    [`redis-cli -h cache.example.invalid --pass ${SECRET} GET key`, 'FLAG'],
    [`redis-cli -h cache.example.invalid --pass=${SECRET} GET key`, 'FLAG'],
    [`redis-cli -h cache.example.invalid -a${SECRET} GET key`, 'FLAG'],
    [`redis-cli -h cache.example.invalid -a"${SECRET}" GET key`, 'FLAG'],
    [`redis-cli -h cache.example.invalid -a'${SECRET}' GET key`, 'FLAG'],
    [`redis-cli -h cache.example.invalid -a="${SECRET}" GET key`, 'FLAG'],
    [`redis-cli -h cache.example.invalid -a='${SECRET}' GET key`, 'FLAG'],
    [`curl -b session=${SECRET} https://api.example.invalid/health`, 'COOKIE'],
    [`curl -b"session=${SECRET}" https://api.example.invalid/health`, 'COOKIE'],
    [`curl --cookie session=${SECRET} https://api.example.invalid/health`, 'COOKIE'],
    [`curl --cookie=session=${SECRET} https://api.example.invalid/health`, 'COOKIE'],
    [`curl --cookie="session=${SECRET}" https://api.example.invalid/health`, 'COOKIE'],
  ];
  for (const [command, transport] of cases) {
    for (const mode of ['default', 'bypassPermissions']) {
      const result = analyze(command, mode);
      assert.equal(result.decision, 'ask', `${mode}: ${command}`);
      assert.equal(result.credential?.transport, transport, command);
      assert.doesNotMatch(JSON.stringify(result), new RegExp(SECRET), command);
      assert.doesNotMatch(redactText(command), new RegExp(SECRET), command);
    }
  }
});

test('secret-like literal HTTP headers use authorization credential controls', () => {
  for (const name of ['X-Vault-Token', 'X-Auth-Token', 'X-Secret', 'X-Access-Key']) {
    const command = `curl -H "${name}: ${SECRET}" https://api.example.invalid/health`;
    for (const mode of ['default', 'bypassPermissions']) {
      const result = analyze(command, mode);
      assert.equal(result.decision, 'ask', `${mode}: ${name}`);
      assert.equal(result.credential?.transport, 'AUTHORIZATION', name);
      assert.doesNotMatch(JSON.stringify(result), new RegExp(SECRET), name);
      assert.doesNotMatch(redactText(command), new RegExp(SECRET), name);
    }
  }

  for (const header of ['Accept: application/json', 'Content-Type: application/json', 'X-Trace-Id: trace-123']) {
    const result = analyze(`curl -H "${header}" https://api.example.invalid/health`);
    assert.equal(result.decision, 'allow', header);
    assert.equal(result.credential, null, header);
  }
});

test('credential identity metadata is not itself a credential transport', () => {
  const identityOnly = analyze('OPS_CREDENTIAL_IDENTITY=operator curl https://api.example.invalid/health');
  assert.equal(identityOnly.decision, 'allow');
  assert.equal(identityOnly.credential, null);

  const authorization = analyze(`OPS_CREDENTIAL_IDENTITY=operator curl -H "Authorization: Bearer ${SECRET}" https://api.example.invalid/health`);
  assert.equal(authorization.credential?.transport, 'AUTHORIZATION');
});

test('catalogued provider references and protected files do not become model-visible literals', () => {
  for (const command of [
    'AWS_PROFILE=ops aws --profile ops --region us-east-1 ec2 describe-instances --max-items 20',
    'curl --cert /secure/client.pem https://api.example.invalid/health',
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

test('quoted, escaped, Unicode, repeated, and empty credential literals are handled', () => {
  const variants = [
    `TOKEN="${SECRET} com espaço ç" curl https://api.example.invalid/health`,
    `TOKEN='${SECRET} com espaço ç' curl https://api.example.invalid/health`,
    `TOKEN=${SECRET}\\ com\\ espaço curl https://api.example.invalid/health`,
    `curl -u "user:${SECRET} com espaço ç" https://api.example.invalid/health`,
    `curl --token '${SECRET} com espaço ç' https://api.example.invalid/health`,
    'TOKEN="" curl https://api.example.invalid/health',
    `TOKEN=${SECRET} GH_TOKEN=${SECRET}_again gh repo view --repo owner/project`,
  ];
  for (const command of variants.slice(3, 5)) {
    const result = analyze(command);
    assert.equal(result.credential?.literal, true, command);
    assert.equal(result.decision, 'ask', command);
    assert.doesNotMatch(JSON.stringify(result), /SYNTH_SECRET_/u, command);
  }
  for (const command of [...variants.slice(0, 3), ...variants.slice(5)]) {
    assert.equal(analyze(command).decision, 'deny', command);
  }
});

test('mixed-quote credential tokens are redacted through the complete raw token', () => {
  const tail = '_SYNTH_TAIL_5f19';
  for (const command of [
    `redis-cli -h cache.example.invalid -a="${SECRET}"'${tail}' GET key`,
    `curl -b "session=${SECRET}"'${tail}' https://api.example.invalid/health`,
  ]) {
    const redacted = redactText(command);
    assert.doesNotMatch(redacted, new RegExp(SECRET), command);
    assert.doesNotMatch(redacted, new RegExp(tail), command);
  }
});

test('only distinct literal credential transports are rejected as mixed', () => {
  const repeatedAuthorization = analyze(
    `OPS_CREDENTIAL_IDENTITY=operator curl -H "Authorization: Bearer ${SECRET}" -H "Authorization: Bearer ${SECRET}_replacement" https://api.example.invalid/health`,
  );
  assert.equal(repeatedAuthorization.decision, 'ask');
  assert.equal(repeatedAuthorization.credential?.transport, 'AUTHORIZATION');

  const mixed = analyze(
    `OPS_CREDENTIAL_IDENTITY=operator curl -u user:${SECRET} --token ${SECRET}_token https://api.example.invalid/health`,
  );
  assert.equal(mixed.decision, 'deny');
  assert.equal(mixed.reasonCode, 'DENY_MULTIPLE_CREDENTIAL_TRANSPORTS');
});
