import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

import { validEvent } from './helpers.mjs';

function moduleUrl(root, mutationId, file) {
  void mutationId;
  return pathToFileURL(path.join(root, 'command-guard', file)).href;
}

async function policyFixture({ root, mutationId }, command, permissionMode = 'bypassPermissions', extra = {}) {
  const { parseHookEvent } = await import(moduleUrl(root, mutationId, 'contract.mjs'));
  const { analyzeCommand } = await import(moduleUrl(root, mutationId, 'policy.mjs'));
  const event = parseHookEvent(JSON.stringify(validEvent({
    permission_mode: permissionMode, ...(extra.cwd ? { cwd: extra.cwd } : {}), tool_input: { command },
  })));
  return analyzeCommand(event, extra.env ?? {});
}

async function catalogueFixture({ root, mutationId }, argv) {
  const { lookupFamily } = await import(moduleUrl(root, mutationId, 'catalogue.mjs'));
  return lookupFamily({ argv });
}

async function postgresEnvironmentFixture(context, name, value) {
  const result = await policyFixture(
    context,
    'psql -h db.example.invalid -p 5432 -U appuser -d app -c "SELECT 1"',
    'bypassPermissions',
    { env: { [name]: value } },
  );
  assert.equal(result.decision, 'deny');
}

const witnesses = {
  async CONTRACT_BACKGROUND_REJECT(context) {
    const { parseHookEvent } = await import(moduleUrl(context.root, context.mutationId, 'contract.mjs'));
    assert.throws(
      () => parseHookEvent(JSON.stringify(validEvent({ tool_input: { command: 'uname', run_in_background: true } }))),
      /background execution is denied/,
    );
  },
  async CONTRACT_COMMAND_BOUND(context) {
    const { LIMITS } = await import(moduleUrl(context.root, context.mutationId, 'limits.mjs'));
    const { parseHookEvent } = await import(moduleUrl(context.root, context.mutationId, 'contract.mjs'));
    assert.throws(() => parseHookEvent(JSON.stringify(validEvent({ tool_input: { command: 'x'.repeat(LIMITS.commandChars + 1) } }))));
  },
  async LEXER_DYNAMIC_REJECT(context) {
    const { lexBash } = await import(moduleUrl(context.root, context.mutationId, 'bash-lexer.mjs'));
    assert.throws(() => lexBash('echo $(id)'));
  },
  async POLICY_UNKNOWN_REJECT(context) {
    assert.equal((await policyFixture(context, 'unknown-command')).decision, 'deny');
  },
  async POLICY_TARGET_REQUIRED(context) {
    assert.equal((await policyFixture(context, 'kubectl scale deployment api --replicas 0')).decision, 'deny');
  },
  async POLICY_DESTRUCTIVE_ALWAYS_ASK(context) {
    assert.equal((await policyFixture(context, 'kubectl --context lab --namespace demo delete pod demo-0')).decision, 'ask');
  },
  async POLICY_RISK_ESCALATION(context) {
    assert.equal((await policyFixture(context, 'uname | kubectl --context lab --namespace demo delete pod demo-0')).decision, 'ask');
  },
  async CREDENTIAL_UNSAFE_SINK_REJECT(context) {
    const result = await policyFixture(context, 'TOKEN=SYNTH_SECRET_mutation echo $TOKEN');
    assert.equal(result.decision, 'deny');
    assert.equal(result.reasonCode, 'DENY_SECRET_OUTPUT');
  },
  async REDACTION_AUTHORIZATION(context) {
    const { detectSensitiveSpans, redactText } = await import(moduleUrl(context.root, context.mutationId, 'redaction.mjs'));
    const secret = 'SYNTH_SECRET_mutation';
    const input = `Authorization: Bearer ${secret}`;
    assert.doesNotMatch(redactText(input, detectSensitiveSpans(input)), new RegExp(secret));
  },
  async AUDIT_FORBIDDEN_FIELD_REJECT(context) {
    const { appendAudit } = await import(moduleUrl(context.root, context.mutationId, 'audit.mjs'));
    const temporary = await mkdtemp(path.join(os.tmpdir(), 'ops-guard-witness-audit-'));
    try {
      assert.throws(() => appendAudit(
        { decision: 'deny', reasonCode: 'x', credential: { token: 'synthetic' } },
        { sessionId: 's', agentType: 'diagnostic-operator', permissionMode: 'default' },
        { OPS_COMMAND_GUARD_AUDIT_PATH: path.join(temporary, 'audit.jsonl') },
      ));
    } finally {
      await rm(temporary, { recursive: true, force: true });
    }
  },
  async ENTRYPOINT_CATCH_EXIT(context) {
    const code = await new Promise((resolve, reject) => {
      const child = spawn(process.execPath, [path.join(context.root, 'validate-ops-command.mjs')], { stdio: ['pipe', 'ignore', 'ignore'] });
      child.on('error', reject);
      child.on('close', resolve);
      child.stdin.end('{');
    });
    assert.equal(code, 2);
  },
  async CATALOGUE_REDIS_EXPIRE_DELETE(context) {
    const result = await policyFixture(context, 'redis-cli EXPIRE cache:key 0');
    assert.equal(result.decision, 'ask');
    assert.equal(result.risk, 'DESTRUCTIVE');
  },
  async CATALOGUE_REDIS_LITERAL_OPERAND(context) {
    assert.equal(await catalogueFixture(context, ['redis-cli', 'EXPIRE', '$KEY', '60']), null);
  },
  async CATALOGUE_REDIS_CLIENT_KILL(context) {
    const result = await policyFixture(context, 'redis-cli CLIENT KILL ID 42');
    assert.equal(result.decision, 'allow');
    assert.equal(result.risk, 'DISRUPTIVE_CHANGE');
  },
  async CATALOGUE_REDIS_CANONICAL_ENVIRONMENT(context) {
    const result = await policyFixture(context, 'redis-cli --tls -h cache.example.invalid -p 6380 -n 1 --user app GET key');
    assert.equal(result.environment, 'redis+tls://app@cache.example.invalid:6380/1');
  },
  async CATALOGUE_REDIS_UNKNOWN_OPTION(context) {
    assert.equal((await policyFixture(context, 'redis-cli --unknown-option GET key')).decision, 'deny');
  },
  async CATALOGUE_HTTP_EXTERNAL_EFFECT(context) {
    const result = await policyFixture(context, 'curl -X POST https://api.example.invalid/restart');
    assert.equal(result.decision, 'ask');
    assert.ok(result.modifiers.includes('EXTERNAL_SIDE_EFFECT'));
  },
  async CATALOGUE_CURL_REMOTE_NAME_ARITY(context) {
    const result = await policyFixture(context, 'curl -O -d action=restart https://api.example.invalid/reload', 'bypassPermissions', { cwd: '/srv/ops' });
    assert.equal(result.decision, 'ask');
    assert.equal(result.target, 'POST /reload -> file:/srv/ops/reload');
  },
  async CATALOGUE_HTTP_SINK_ALWAYS_ASK(context) {
    const result = await policyFixture(context, 'curl -o report.json https://api.example.invalid/report', 'bypassPermissions', { cwd: '/srv/ops' });
    assert.equal(result.decision, 'ask');
    assert.ok(result.modifiers.includes('ALWAYS_ASK'));
  },
  async CATALOGUE_DATABASE_SELECTOR_UNIQUENESS(context) {
    assert.equal((await policyFixture(context, 'psql -h audited.invalid -h effective.invalid -p 5432 -U appuser -d app -c "SELECT 1"')).decision, 'deny');
  },
  async CATALOGUE_DATABASE_CANONICAL_ENVIRONMENT(context) {
    const result = await policyFixture(context, 'mysql -h db.invalid -P 3307 -u appuser -D app -e "SHOW STATUS"');
    assert.equal(result.environment, 'mysql://appuser@db.invalid:3307/app');
  },
  async CATALOGUE_GIT_LONG_DELETE(context) {
    const result = await policyFixture(context, 'git branch --delete --force release');
    assert.equal(result.decision, 'ask');
    assert.equal(result.risk, 'DESTRUCTIVE');
  },
  async OUTPUT_PATH_ALLOWLIST(context) {
    const { resolveOutputPath } = await import(moduleUrl(context.root, context.mutationId, 'output-path.mjs'));
    assert.equal(resolveOutputPath('$DEST/report.json', {
      env: {
        OPS_COMMAND_GUARD_OUTPUT_VARIABLES: 'OPS_OUTPUT_DIR',
        OPS_OUTPUT_DIR: '/srv/output',
        DEST: '/tmp/unapproved',
      },
    }), null);
  },
  async CATALOGUE_HTTP_ROUTING_HEADER_REJECT(context) {
    const result = await policyFixture(context, 'curl -H "Host: alternate.invalid" https://api.example.invalid/health');
    assert.equal(result.decision, 'deny');
  },
  async CATALOGUE_DATABASE_EXPLICIT_DOMAIN(context) {
    const result = await policyFixture(context, 'psql -c "SELECT 1"');
    assert.equal(result.decision, 'deny');
  },
  async CATALOGUE_HTTP_STDOUT_SENSITIVE(context) {
    const result = await policyFixture(context, 'curl -i https://api.example.invalid/health', 'bypassPermissions');
    assert.equal(result.decision, 'ask');
    assert.ok(result.modifiers.includes('SENSITIVE_OUTPUT'));
  },
  async OUTPUT_PATH_TILDE_REJECT(context) {
    const { resolveOutputPath } = await import(moduleUrl(context.root, context.mutationId, 'output-path.mjs'));
    assert.equal(resolveOutputPath('~/report.json', { cwd: '/srv/ops' }), null);
  },
  async CATALOGUE_POSTGRES_ENVIRONMENT_REJECT(context) {
    const result = await policyFixture(
      context,
      'psql -h db.example.invalid -p 5432 -U appuser -d app -c "SELECT 1"',
      'bypassPermissions',
      { env: { PGHOSTADDR: '203.0.113.77' } },
    );
    assert.equal(result.decision, 'deny');
  },
  async CATALOGUE_MYSQL_SOCKET_HOST_REJECT(context) {
    const result = await policyFixture(context, 'mysql -h localhost -P 3306 -u appuser -D app -e "SELECT 1"');
    assert.equal(result.decision, 'deny');
  },
  async CATALOGUE_CREDENTIAL_TRACE_DISCLOSURE(context) {
    const secret = 'SYNTH_SECRET_trace_mutation';
    const stdout = await policyFixture(context, `curl -H "Authorization: Bearer ${secret}" --trace - https://api.example.invalid/health`);
    const file = await policyFixture(context, `curl -H "Authorization: Bearer ${secret}" --trace trace.log https://api.example.invalid/health`, 'bypassPermissions', { cwd: '/srv/ops' });
    assert.equal(stdout.reasonCode, 'DENY_SECRET_OUTPUT');
    assert.equal(file.reasonCode, 'DENY_SECRET_PERSISTENCE');
  },
  async CATALOGUE_POSTGRES_SSL_NEGOTIATION_ENV(context) {
    await postgresEnvironmentFixture(context, 'PGSSLNEGOTIATION', 'direct');
  },
  async CATALOGUE_POSTGRES_REQUIRE_AUTH_ENV(context) {
    await postgresEnvironmentFixture(context, 'PGREQUIREAUTH', 'scram-sha-256');
  },
  async CATALOGUE_POSTGRES_SSL_CERT_MODE_ENV(context) {
    await postgresEnvironmentFixture(context, 'PGSSLCERTMODE', 'require');
  },
  async CATALOGUE_POSTGRES_SSL_MIN_PROTOCOL_ENV(context) {
    await postgresEnvironmentFixture(context, 'PGSSLMINPROTOCOLVERSION', 'TLSv1.3');
  },
  async CATALOGUE_POSTGRES_SSL_MAX_PROTOCOL_ENV(context) {
    await postgresEnvironmentFixture(context, 'PGSSLMAXPROTOCOLVERSION', 'TLSv1.3');
  },
  async CATALOGUE_POSTGRES_GSS_DELEGATION_ENV(context) {
    await postgresEnvironmentFixture(context, 'PGGSSDELEGATION', '1');
  },
  async CATALOGUE_POSTGRES_MIN_PROTOCOL_ENV(context) {
    await postgresEnvironmentFixture(context, 'PGMINPROTOCOLVERSION', '3.0');
  },
  async CATALOGUE_POSTGRES_MAX_PROTOCOL_ENV(context) {
    await postgresEnvironmentFixture(context, 'PGMAXPROTOCOLVERSION', '3.0');
  },
  async POLICY_CREDENTIAL_CONSUMER_BINDING(context) {
    const result = await policyFixture(
      context,
      'kubectl --context prod label pod/foo x=y ; OPS_CREDENTIAL_IDENTITY=operator curl -H "Authorization: Bearer SYNTH_SECRET_binding_mutation" https://api.example.invalid/health',
    );
    assert.equal(result.credentialBinding.domain, 'https://api.example.invalid');
    assert.equal(result.credentialBinding.family, 'HTTP');
  },
  async CATALOGUE_MONGOSH_SINGLE_EVAL(context) {
    assert.equal((await policyFixture(context, 'mongosh mongodb://db.example.invalid/app --eval "db.serverStatus()" --eval "db.users.drop()"')).decision, 'deny');
  },
  async CATALOGUE_IP_BATCH_REJECT(context) {
    assert.equal((await policyFixture(context, 'ip -batch route')).decision, 'deny');
  },
  async CATALOGUE_REMOTE_EXECUTOR_REJECT(context) {
    assert.equal((await policyFixture(context, 'scp -S /tmp/payload local.txt ops@example.invalid:/tmp/remote.txt')).decision, 'deny');
  },
  async CATALOGUE_PACKET_SINK_EFFECT(context) {
    const result = await policyFixture(context, 'tcpdump -i eth0 -c 10 -w /var/tmp/capture.pcap host 192.0.2.1');
    assert.equal(result.decision, 'ask');
    assert.equal(result.risk, 'LOW_RISK_CHANGE');
    assert.ok(result.modifiers.includes('FILE_WRITE'));
  },
  async CATALOGUE_CTR_NESTED_RISK(context) {
    assert.equal((await policyFixture(context, 'ctr images pull docker.io/library/nginx:latest')).risk, 'LOW_RISK_CHANGE');
  },
  async CATALOGUE_GIT_OUTPUT_EFFECT(context) {
    const result = await policyFixture(context, 'git diff --output=/var/tmp/review.patch');
    assert.equal(result.decision, 'ask');
    assert.ok(result.modifiers.includes('FILE_WRITE'));
  },
  async CATALOGUE_DMESG_CONTROL_RISK(context) {
    const result = await policyFixture(context, 'dmesg --read-clear --level err');
    assert.equal(result.decision, 'ask');
    assert.equal(result.risk, 'DESTRUCTIVE');
  },
  async POLICY_CREDENTIAL_STAGE_OWNERSHIP(context) {
    const firstStage = await policyFixture(
      context,
      'OPS_CREDENTIAL_IDENTITY=operator curl -H "Authorization: Bearer SYNTH_SECRET_stage_witness" https://api.example.invalid/health ; gh pr view 25 --repo example/project',
    );
    assert.equal(firstStage.decision, 'ask');
    assert.equal(firstStage.credentialBinding?.domain, 'https://api.example.invalid');
    const distributed = await policyFixture(
      context,
      'OPS_CREDENTIAL_IDENTITY=operator curl -H "Authorization: Bearer SYNTH_SECRET_stage_a" https://api.example.invalid/a ; OPS_CREDENTIAL_IDENTITY=operator curl -H "Authorization: Bearer SYNTH_SECRET_stage_b" https://api.example.invalid/b',
    );
    assert.equal(distributed.decision, 'deny');
  },
  async CATALOGUE_REMOTE_ENDPOINT_IDENTITY(context) {
    const result = await policyFixture(
      context,
      'scp -P 2222 -J jump@bastion.invalid -l 512 -i keys/ops artifact.txt ops@files.example.invalid:/tmp/artifact.txt',
    );
    assert.equal(result.environment, 'ssh://ops@files.example.invalid:2222;via=jump%40bastion.invalid;limitKbps=512;identityFile=keys%2Fops');
  },
  async CATALOGUE_PACKET_STDOUT_IDENTITY(context) {
    const result = await policyFixture(context, 'tcpdump -i eth0 -c 10 -w - host 192.0.2.1');
    assert.equal(result.decision, 'ask');
    assert.equal(result.risk, 'SAFE_READ_ONLY');
    assert.equal(result.target, 'eth0 -> stdout:pcap');
    assert.ok(!result.modifiers.includes('FILE_WRITE'));
  },
  async CATALOGUE_PACKET_SELECTOR_UNIQUENESS(context) {
    const result = await policyFixture(context, 'tshark -i eth0 -c 10 -s 64 --snapshot-length=128 host 192.0.2.1');
    assert.equal(result.decision, 'deny');
  },
  async POLICY_CREDENTIAL_EFFECTIVE_CONSUMER(context) {
    const result = await policyFixture(
      context,
      'OPS_CREDENTIAL_IDENTITY=operator SSHPASS=SYNTH_SECRET_consumer_witness sudo systemctl restart nginx',
    );
    assert.equal(result.decision, 'deny');
    assert.equal(result.reasonCode, 'DENY_UNKNOWN_CREDENTIAL_CONSUMER');
    const wrongVariable = await policyFixture(
      context,
      'GH_TOKEN=SYNTH_SECRET_selector_witness aws --profile ops --region us-east-1 ec2 describe-instances --max-items 20',
    );
    assert.equal(wrongVariable.decision, 'deny');
  },
  async CATALOGUE_REMOTE_ADDRESS_FAMILY_IDENTITY(context) {
    const accepted = await policyFixture(
      context,
      'scp -4 artifact.txt ops@files.example.invalid:/tmp/artifact.txt',
    );
    assert.equal(accepted.environment, 'ssh://ops@files.example.invalid:22;addressFamily=inet');
    const conflict = await policyFixture(
      context,
      'scp -4 -o AddressFamily=inet6 artifact.txt ops@files.example.invalid:/tmp/artifact.txt',
    );
    assert.equal(conflict.decision, 'deny');
  },
  async CATALOGUE_REMOTE_ADDRESS_FAMILY_CANONICAL(context) {
    const result = await policyFixture(
      context,
      'scp -o AddressFamily=INET artifact.txt ops@files.example.invalid:/tmp/artifact.txt',
    );
    assert.equal(result.environment, 'ssh://ops@files.example.invalid:22;addressFamily=inet');
  },
  async CATALOGUE_GIT_PUSH_EXEC_REJECT(context) {
    assert.equal((await policyFixture(context, 'git push --exec=/tmp/payload https://git.example.invalid/ops/repo.git main')).decision, 'deny');
  },
  async CATALOGUE_GIT_PUSH_DESTINATION_BINDING(context) {
    const result = await policyFixture(context, 'git push https://github.com/example/project.git main');
    assert.equal(result.environment, 'https://github.com/example/project.git');
    assert.equal(result.target, 'main');
  },
  async CATALOGUE_JOURNAL_FOLLOW_REJECT(context) {
    assert.equal((await policyFixture(context, 'journalctl -u nginx -n 10 --follow')).decision, 'deny');
  },
  async CATALOGUE_CONTAINER_FOLLOW_REJECT(context) {
    assert.equal((await policyFixture(context, 'docker logs --tail 10 --follow web')).decision, 'deny');
  },
  async CATALOGUE_GH_WATCH_REJECT(context) {
    assert.equal((await policyFixture(context, 'gh pr checks 25 --watch --repo example/project')).decision, 'deny');
  },
  async CATALOGUE_GH_LIMIT_BOUND(context) {
    assert.equal((await policyFixture(context, 'gh pr list --limit 1001 --repo example/project')).decision, 'deny');
  },
  async CATALOGUE_GH_LOG_APPROVAL(context) {
    const result = await policyFixture(context, 'gh run view 123 --log --repo example/project');
    assert.equal(result.decision, 'ask');
    assert.ok(result.modifiers.includes('SENSITIVE_OUTPUT'));
    assert.ok(result.modifiers.includes('RESOURCE_INTENSIVE'));
    assert.ok(result.modifiers.includes('ALWAYS_ASK'));
  },
  async CATALOGUE_KUBECTL_DUMP_REJECT(context) {
    assert.equal((await policyFixture(context, 'kubectl --context lab cluster-info dump')).decision, 'deny');
    assert.equal((await policyFixture(context, 'k3s kubectl --context lab cluster-info dump')).decision, 'deny');
  },
  async CATALOGUE_GIT_PUSH_REPOSITORY_TRANSPORT(context) {
    assert.equal((await policyFixture(context, "git push 'ext::/tmp/review-helper %S repo' main")).decision, 'deny');
    assert.equal((await policyFixture(context, "git push --repo='ext::/tmp/review-helper %S repo' main")).decision, 'deny');
    assert.equal((await policyFixture(context, 'git push 1helper::opaque-address main')).decision, 'deny');
    assert.equal((await policyFixture(context, 'git push --repo=1helper::opaque-address main')).decision, 'deny');
    assert.equal((await policyFixture(context, 'git push --repo 1helper::opaque-address main')).decision, 'deny');
  },
  async CATALOGUE_GH_REPOSITORY_BINDING(context) {
    const result = await policyFixture(
      context,
      'OPS_CREDENTIAL_IDENTITY=operator GH_TOKEN=SYNTH_SECRET_gh_binding gh pr view 25',
      'bypassPermissions',
      { cwd: '/srv/repo-a' },
    );
    assert.equal(result.decision, 'deny');
    assert.equal(result.credentialBinding, undefined);
  },
  async CATALOGUE_CONTAINER_LOG_TARGET(context) {
    const result = await policyFixture(context, 'docker --context lab logs --tail 10 web');
    assert.equal(result.target, 'web');
    assert.equal(result.environment, 'lab');
  },
  async CATALOGUE_GIT_PUSH_URL_TRANSPORT(context) {
    assert.equal((await policyFixture(context, 'git push helper://opaque-address main')).decision, 'deny');
    assert.equal((await policyFixture(context, 'git push --repo=helper://opaque-address main')).decision, 'deny');
  },
  async CATALOGUE_GIT_PUSH_URL_SCHEME_CASE(context) {
    assert.equal((await policyFixture(context, 'git push HTTPS://git.example.invalid/ops/repo.git main')).decision, 'deny');
    assert.equal((await policyFixture(context, 'git push --repo=HtTpS://git.example.invalid/ops/repo.git main')).decision, 'deny');
    assert.equal((await policyFixture(context, 'git push --repo HtTpS://git.example.invalid/ops/repo.git main')).decision, 'deny');
  },
  async CATALOGUE_GIT_PUSH_LITERAL_ADDRESS(context) {
    assert.equal((await policyFixture(context, 'git push origin main')).decision, 'deny');
    assert.equal((await policyFixture(context, 'git push --repo=review HEAD:main')).decision, 'deny');
    assert.equal((await policyFixture(context, 'git push --repo review HEAD:main')).decision, 'deny');
  },
  async CATALOGUE_GIT_PUSH_ALWAYS_ASK(context) {
    const result = await policyFixture(context, 'git push https://git.example.invalid/ops/repo.git main');
    assert.equal(result.decision, 'ask');
    assert.ok(result.modifiers.includes('ALWAYS_ASK'));
    assert.equal(result.target, 'main');
    assert.equal(result.environment, 'https://git.example.invalid/ops/repo.git');
  },
  async CATALOGUE_HTTP_REDIRECT_REJECT(context) {
    const result = await policyFixture(context, 'curl -LsS https://origin.example.invalid/start');
    assert.equal(result.decision, 'deny');
    assert.equal(result.reasonCode, 'DENY_UNBOUND_HTTP_REDIRECT');
  },
  async CATALOGUE_POWERSHELL_REDIRECT_ZERO(context) {
    const deniedResult = await policyFixture(context, 'Invoke-WebRequest -Uri https://origin.example.invalid/start');
    assert.equal(deniedResult.reasonCode, 'DENY_UNBOUND_HTTP_REDIRECT');
    const allowedResult = await policyFixture(context, 'Invoke-WebRequest -Uri https://api.example.invalid/health -MaximumRedirection 0');
    assert.equal(allowedResult.decision, 'allow');
  },
  async CATALOGUE_POWERSHELL_HEADER_BINDING(context) {
    const result = await policyFixture(
      context,
      'Invoke-WebRequest -Uri https://api.example.invalid/health -MaximumRedirection 0 -Headers malformed',
    );
    assert.equal(result.decision, 'deny');
  },
  async REDACTION_SECRET_HEADER(context) {
    const { detectSensitiveSpans, redactText } = await import(moduleUrl(context.root, context.mutationId, 'redaction.mjs'));
    const secret = 'SYNTH_SECRET_header_mutation';
    const input = `X-Vault-Token: ${secret}`;
    assert.doesNotMatch(redactText(input, detectSensitiveSpans(input)), new RegExp(secret));
  },
  async POLICY_CATALOGUE_REJECTION(context) {
    const result = await policyFixture(context, 'curl -L https://origin.example.invalid/start');
    assert.equal(result.decision, 'deny');
    assert.equal(result.reasonCode, 'DENY_UNBOUND_HTTP_REDIRECT');
  },
  async CATALOGUE_GIT_LOCAL_CLOSED_GRAMMAR(context) {
    const result = await policyFixture(context, 'git commit -F message.txt');
    assert.equal(result.decision, 'deny');
    assert.equal(result.reasonCode, 'DENY_UNSUPPORTED_GIT_FORM');
  },
  async CATALOGUE_GIT_COMMIT_AMEND_RISK(context) {
    const result = await policyFixture(context, 'git commit --amend -m change');
    assert.equal(result.decision, 'ask');
    assert.equal(result.risk, 'DESTRUCTIVE');
  },
  async CATALOGUE_GIT_TAG_FORCE_RISK(context) {
    const result = await policyFixture(context, 'git tag --force v1.2.3');
    assert.equal(result.decision, 'ask');
    assert.equal(result.risk, 'DESTRUCTIVE');
  },
  async CATALOGUE_GIT_TAG_DELETE_RISK(context) {
    const result = await policyFixture(context, 'git tag --delete v1.2.3');
    assert.equal(result.decision, 'ask');
    assert.equal(result.risk, 'DESTRUCTIVE');
  },
  async POLICY_GIT_UNSUPPORTED_FORM_GUIDANCE(context) {
    const result = await policyFixture(context, 'git tag --list');
    assert.equal(result.reasonCode, 'DENY_UNSUPPORTED_GIT_FORM');
    assert.match(result.message, /git add, commit, or tag/u);
    assert.doesNotMatch(result.message, /--list/u);
  },
  async CATALOGUE_KUBECTL_PRUNE_RISK(context) {
    for (const prefix of ['kubectl', 'k3s kubectl']) {
      const result = await policyFixture(
        context,
        `${prefix} --context prod --namespace app apply --prune -l app=demo -f manifest.yaml`,
      );
      assert.equal(result.decision, 'ask');
      assert.equal(result.risk, 'DESTRUCTIVE');
    }
  },
  async POLICY_POWERSHELL_NOPROFILE_REQUIRED(context) {
    const deniedResult = await policyFixture(context, 'pwsh -Command "Get-Service"');
    assert.equal(deniedResult.decision, 'deny');
    assert.equal(deniedResult.reasonCode, 'DENY_POWERSHELL_PROFILE');
    assert.equal((await policyFixture(context, 'pwsh -NoProfile -Command "Get-Service"')).decision, 'allow');
  },
};

export const MUTATION_WITNESSES = Object.freeze(witnesses);
