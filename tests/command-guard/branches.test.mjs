import assert from 'node:assert/strict';
import { Readable, Writable } from 'node:stream';
import path from 'node:path';
import test from 'node:test';

import { appendAudit, resolveAuditPath, sanitizeAuditValue, structuralActionIdentity } from '../../skills/command-driven-operations/scripts/command-guard/audit.mjs';
import { BASH_OPERATORS, lexBash } from '../../skills/command-driven-operations/scripts/command-guard/bash-lexer.mjs';
import { lookupFamily } from '../../skills/command-driven-operations/scripts/command-guard/catalogue.mjs';
import { buildComposition } from '../../skills/command-driven-operations/scripts/command-guard/composition.mjs';
import { parseHookEvent } from '../../skills/command-driven-operations/scripts/command-guard/contract.mjs';
import { classifyCredentials, credentialFlowErrors } from '../../skills/command-driven-operations/scripts/command-guard/credential-flow.mjs';
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

function family(command) {
  return lookupFamily(buildComposition(lexBash(command)).stages[0]);
}

test('contract rejects every malformed field branch and accepts exact boundaries', () => {
  const invalid = [
    [null, /size/],
    ['x'.repeat(LIMITS.inputBytes + 1), /size/],
    ['{', /JSON/],
    ['[]', /object/],
    [event({ extra: {} }), /unexpected hook field/],
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
    assert.match(record.actionId, /^[a-f0-9]{64}$/u);
    assert.equal('fingerprint' in record, false);
  } finally {
    if (previous === undefined) delete process.env.OPS_COMMAND_GUARD_AUDIT_PATH;
    else process.env.OPS_COMMAND_GUARD_AUDIT_PATH = previous;
    await temporary.cleanup();
  }
});

test('structural action identity excludes credential values and raw commands', () => {
  const first = policy('curl -H "Authorization: Bearer SYNTH_SECRET_first" https://api.example.invalid/health');
  const second = policy('curl -H "Authorization: Bearer SYNTH_SECRET_second" https://api.example.invalid/health');
  assert.equal(structuralActionIdentity(first), structuralActionIdentity(second));
  assert.doesNotMatch(structuralActionIdentity(first), /SYNTH_SECRET/u);
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

test('credential spans outside every lexical stage fail closed', () => {
  const composition = buildComposition(lexBash('curl https://api.example.invalid'));
  const analysis = classifyCredentials(composition, 'synthetic', [
    { start: 100, end: 109, kind: 'FLAG' },
  ]);
  assert.equal(analysis.metadata.stage, null);
  assert.deepEqual(credentialFlowErrors(composition, analysis), [
    { reasonCode: 'DENY_UNKNOWN_CREDENTIAL_CONSUMER', stage: 1 },
  ]);
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
  assert.deepEqual(detectSensitiveSpans('unterminated "'), []);
  assert.deepEqual(detectSensitiveSpans('curl -b'), []);
  assert.deepEqual(detectSensitiveSpans(';'), []);
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

test('catalogue filter and Git schemas distinguish bounded operations from file or unknown inputs', () => {
  assert.equal(family('ip addr show')?.policyId, 'POSIX_HOST_READ');
  assert.equal(family('curl -s https://api.example.invalid/health')?.policyId, 'HTTP');
  for (const command of [
    'grep pattern', 'grep -e pattern', 'rg --regexp=pattern', 'head -n 1',
    'tail --lines=1', 'cut -d : -f 1', 'sort', 'uniq', 'wc', 'sed -n 1p',
    "awk '{print $1}'", "jq '.name'", 'Where-Object Status -eq Running',
  ]) assert.equal(family(command)?.policyId, 'FILTER', command);

  for (const command of [
    'grep pattern /etc/passwd', 'grep -r pattern', 'rg --glob *.js pattern',
    'head -n 1 file', 'tail file', 'cut -f 1 file', 'sort file', 'uniq file',
    'wc file', 'sed 1p', "awk 'system(\"id\")'", 'jq --from-file filter.jq',
  ]) assert.equal(family(command), null, command);

  const gitCases = [
    ['git status', 'SAFE_READ_ONLY'], ['git branch --list', 'SAFE_READ_ONLY'],
    ['git reset --hard', 'DESTRUCTIVE'], ['git clean -fd', 'DESTRUCTIVE'],
    ['git push origin main --force-with-lease', 'DESTRUCTIVE'], ['git branch -d old', 'DESTRUCTIVE'],
    ['git tag -d old', 'DESTRUCTIVE'], ['git add file', 'LOW_RISK_CHANGE'],
    ['git commit -m change', 'LOW_RISK_CHANGE'], ['git push origin main', 'LOW_RISK_CHANGE'],
    ['gh repo view --repo owner/project', 'SAFE_READ_ONLY'], ['gh pr checks owner/project', 'SAFE_READ_ONLY'],
    ['gh repo delete owner/project --repo owner/project', 'DESTRUCTIVE'],
    ['gh release delete v1 --repo owner/project', 'DESTRUCTIVE'],
    ['gh pr merge 1 --repo owner/project', 'DESTRUCTIVE'],
    ['gh workflow run deploy.yml --repo owner/project', 'DISRUPTIVE_CHANGE'],
    ['gh issue create --repo owner/project --title issue', 'LOW_RISK_CHANGE'],
  ];
  for (const [command, risk] of gitCases) assert.equal(family(command)?.risk, risk, command);
  assert.equal(family('git frobnicate'), null);
  assert.equal(family('gh api /repos/owner/project'), null);
});

test('catalogue SSH schema accepts only literal finite transport options and one nested operation', () => {
  for (const command of [
    'ssh -4 -q -v -T ops@example.invalid "uname -a"',
    'ssh -o BatchMode=yes ops@example.invalid "uname -a"',
    'ssh -oIdentitiesOnly=yes ops@example.invalid "uname -a"',
    'ssh -o=StrictHostKeyChecking=accept-new ops@example.invalid "uname -a"',
    'ssh -o ConnectTimeout=0 ops@example.invalid "uname -a"',
    'ssh -o ServerAliveInterval=300 ops@example.invalid "uname -a"',
    'ssh -o ConnectionAttempts=10 ops@example.invalid "uname -a"',
    'ssh -o ServerAliveCountMax=10 ops@example.invalid "uname -a"',
    'ssh -o Port=22 ops@example.invalid "uname -a"',
    'ssh -o AddressFamily=inet6 ops@example.invalid "uname -a"',
    'ssh -o LogLevel=debug3 ops@example.invalid "uname -a"',
    'ssh -o User=operator ops@example.invalid "uname -a"',
    'ssh -o ProxyJump=jump@example.invalid ops@example.invalid "uname -a"',
    'ssh -p 22 -l ops -i key.pem -J jump.example.invalid ops@example.invalid "uname -a"',
    'ssh -p22 -lops -ikey.pem -Jjump.example.invalid ops@example.invalid "uname -a"',
  ]) assert.equal(family(command)?.policyId, 'REMOTE', command);

  for (const command of [
    'ssh -o BatchMode=no ops@example.invalid "uname -a"',
    'ssh -o StrictHostKeyChecking=no ops@example.invalid "uname -a"',
    'ssh -o ConnectTimeout=301 ops@example.invalid "uname -a"',
    'ssh -o ConnectionAttempts=11 ops@example.invalid "uname -a"',
    'ssh -o Port=0 ops@example.invalid "uname -a"',
    'ssh -o AddressFamily=other ops@example.invalid "uname -a"',
    'ssh -o LogLevel=trace ops@example.invalid "uname -a"',
    'ssh -o User=$USER ops@example.invalid "uname -a"',
    'ssh -o ProxyJump=$JUMP ops@example.invalid "uname -a"',
    'ssh -o Unknown=value ops@example.invalid "uname -a"',
    'ssh -o invalid ops@example.invalid "uname -a"',
    'ssh -o',
    'ssh -p ops@example.invalid "uname -a"',
    'ssh -p 0 ops@example.invalid "uname -a"',
    'ssh -Z value ops@example.invalid "uname -a"',
    'ssh -p$PORT ops@example.invalid "uname -a"',
    'ssh ops@example.invalid "uname -a" trailing',
    'ssh $HOST "uname -a"',
    'ssh ops@example.invalid "uname -a | head -n 1"',
    'ssh ops@example.invalid "mysteryctl status"',
    'ssh ops@example.invalid "ssh other.example.invalid uname"',
  ]) assert.equal(family(command), null, command);
});

test('catalogue Kubernetes schemas consume every supported option form', () => {
  const accepted = [
    'kubectl --context=lab --namespace demo get pods -o yaml --selector app=api --watch false --chunk-size 20',
    'kubectl --context lab describe pod api --show-events',
    'kubectl --context lab logs pod/api --tail=20 --timestamps --follow=false',
    'kubectl --context lab events --for pod/api --types Warning --watch-only false --chunk-size=20',
    'kubectl --context lab version --client --short',
    'kubectl --context lab cluster-info',
    'kubectl --context lab --namespace demo label pod api env=prod --overwrite',
    'kubectl --context lab --namespace demo annotate pod api owner=ops --local',
    'kubectl --context lab --namespace demo apply -f manifest.yaml --server-side',
    'kubectl --context lab --namespace demo patch deployment api -p {} --type merge --local',
    'kubectl --context lab --namespace demo scale deployment api --replicas=2',
    'kubectl --context lab cordon node-a --dry-run',
    'kubectl --context lab uncordon node-a --selector role=worker',
    'kubectl --context lab --namespace demo delete pod api --wait false --force',
    'kubectl --context lab drain node-a --ignore-daemonsets --grace-period 30',
    'kubectl --context lab --namespace demo replace -f manifest.yaml --force',
    'k3s kubectl --context lab get pods --chunk-size=20',
  ];
  for (const command of accepted) assert.equal(family(command)?.policyId, 'KUBERNETES', command);

  for (const command of [
    'kubectl --context get pods',
    'kubectl --context= get pods',
    'kubectl --context lab get pods --watch=maybe',
    'kubectl --context lab get pods --unknown',
    'kubectl --context lab logs pod/api --tail',
    'kubectl --context lab',
    'kubectl --context lab frobnicate pods',
  ]) assert.equal(family(command), null, command);
});

test('catalogue families exercise finite risk and option boundaries', () => {
  const risks = [
    ['ps aux', 'SAFE_READ_ONLY'], ['ss -l', 'SAFE_READ_ONLY'], ['ss -K dst 192.0.2.1', 'DESTRUCTIVE'],
    ['mount -l', 'SAFE_READ_ONLY'], ['journalctl -n 10', 'SAFE_READ_ONLY'],
    ['journalctl -n 10 --rotate', 'DESTRUCTIVE'], ['Test-Connection example.invalid -Count=3', 'SAFE_READ_ONLY'],
    ['gpg --decrypt credential.gpg', 'SAFE_READ_ONLY'], ['sudo systemctl status nginx', 'SAFE_READ_ONLY'],
    ['service nginx restart', 'DISRUPTIVE_CHANGE'], ['systemctl enable nginx', 'LOW_RISK_CHANGE'],
    ['systemctl restart nginx', 'DISRUPTIVE_CHANGE'],
    ['docker ps', 'SAFE_READ_ONLY'], ['docker inspect web', 'SAFE_READ_ONLY'],
    ['docker logs --tail 20 web', 'SAFE_READ_ONLY'], ['docker stats --no-stream web', 'SAFE_READ_ONLY'],
    ['docker pull image:latest', 'LOW_RISK_CHANGE'], ['docker restart web', 'DISRUPTIVE_CHANGE'],
    ['docker rm web', 'DESTRUCTIVE'], ['aws --profile ops --region us-east-1 ec2 get-console-output --instance-ids i-1', 'SAFE_READ_ONLY'],
    ['aws --profile ops --region us-east-1 ec2 create-tags --resources i-1', 'LOW_RISK_CHANGE'],
    ['aws --profile ops --region us-east-1 ec2 start-instances --instance-ids i-1', 'DISRUPTIVE_CHANGE'],
    ['aws --profile ops --region us-east-1 ec2 terminate-instances --instance-ids i-1', 'DESTRUCTIVE'],
    ['az vm show --subscription lab --name vm1', 'SAFE_READ_ONLY'],
    ['az tag create --subscription lab --name tag1', 'LOW_RISK_CHANGE'],
    ['az vm restart --subscription lab --name vm1', 'DISRUPTIVE_CHANGE'],
    ['az vm purge --subscription lab --name vm1', 'DESTRUCTIVE'],
    ['gcloud compute instances describe vm1 --project lab', 'SAFE_READ_ONLY'],
    ['gcloud projects add-labels project1 --project lab', 'LOW_RISK_CHANGE'],
    ['gcloud compute instances reset vm1 --project lab', 'DISRUPTIVE_CHANGE'],
    ['gcloud compute instances delete vm1 --project lab', 'DESTRUCTIVE'],
    ['pg_isready', 'SAFE_READ_ONLY'], ['psql -h db.invalid -p 5432 -U appuser -d app -c "SET application_name = ops"', 'LOW_RISK_CHANGE'],
    ['psql -h db.invalid -p 5432 -U appuser -d app -c "VACUUM"', 'DISRUPTIVE_CHANGE'],
    ['psql -h db.invalid -p 5432 -U appuser -d app -c "DROP TABLE demo"', 'DESTRUCTIVE'],
    ['mysql -h db.invalid -P 3306 -u appuser -D app -e "SET sql_safe_updates = 1"', 'LOW_RISK_CHANGE'],
    ['mysqladmin -h db.invalid -P 3306 -u appuser FLUSH', 'DISRUPTIVE_CHANGE'], ['mysqladmin -h db.invalid -P 3306 -u appuser SHUTDOWN', 'DESTRUCTIVE'],
    ['mongosh mongodb://db.invalid/app --eval "db.serverStatus()"', 'SAFE_READ_ONLY'],
    ['mongosh mongodb://db.invalid/app --eval "db.reconfig()"', 'DISRUPTIVE_CHANGE'],
    ['mongosh mongodb://db.invalid/app --eval "db.demo.drop()"', 'DESTRUCTIVE'],
    ['Restart-Service -Name spooler', 'DISRUPTIVE_CHANGE'], ['Set-Service -Name spooler', 'LOW_RISK_CHANGE'],
  ];
  for (const [command, risk] of risks) assert.equal(family(command)?.risk, risk, command);

  for (const command of [
    'ps e', 'mount /dev/sda1 /mnt', 'ip link delete dev eth0', 'ip nonsense',
    'journalctl -n', 'journalctl --lines=', 'journalctl -n 10 --since [bad]',
    'Test-Connection example.invalid -Count',
    'Test-Connection example.invalid -Count=', 'gpg --encrypt plaintext', 'sshpass -d 1 ssh host uname',
    'sudo', 'sshpass -d 0 mysteryctl status', 'sshpass -d 0 uname -a',
    'systemctl --host remote status nginx', 'systemctl', 'systemctl frobnicate nginx',
    'docker stats web', 'docker logs web', 'docker --context lab --context prod ps',
    'docker --context [bad] logs --tail 10 web', 'docker logs --tail [bad] web',
    'gh pr view 25 --repo [bad]', 'gh pr checks [bad] --repo owner/project',
    'docker --context=$CONTEXT ps', 'aws --profile ops --profile prod ec2 describe-instances --max-items 1',
    'AWS_PROFILE=ops aws --profile prod --region us-east-1 ec2 describe-instances --max-items 1',
    'aws --profile ops', 'aws --profile ops --region us-east-1 ec2 unknown-action', 'az rest --subscription lab',
    'az nonsense --subscription lab', 'gcloud compute ssh vm1 --project lab',
    'gcloud compute instances unknown vm1 --project lab', 'psql -h db.invalid -d app',
    'mysql -h db.invalid -D app -e "SELECT * FROM events"', 'mysql -h db.invalid -D app -e "TABLE users"',
    'mongosh mongodb://db.invalid/app', 'mongosh mongodb://db.invalid/app --eval "db.unknown()"',
    'curl https://', 'curl -X', 'curl -X OPTIONS https://api.example.invalid/items',
  ]) assert.equal(family(command), null, command);

  assert.equal(family('mongosh mongodb://db.invalid --eval "db.serverStatus()"')?.target, 'server');
  assert.equal(family('Restart-Service spooler')?.target, 'spooler');
  assert.equal(lookupFamily({ argv: ['ssh', 'ops@example.invalid', 'echo $('] }), null);
  assert.equal(lookupFamily({ argv: ['ssh', '-p'] }), null);
});

test('native response covers allow, ask, deny, and invalid decisions', () => {
  for (const decision of ['allow', 'ask', 'deny']) {
    const response = decisionResponse({ decision, message: `${decision}: redacted` });
    assert.equal(response.hookSpecificOutput.permissionDecision, decision);
    assert.equal('systemMessage' in response, decision === 'deny');
  }
  assert.throws(() => decisionResponse({ decision: 'maybe', message: 'x' }), /invalid decision/);
});

test('multi-stage explanations and audit preserve every bounded stage finding', async () => {
  const result = policy('uname -a ; uptime');
  assert.equal(result.findings.length, 2);
  assert.match(result.message, /stage 1 POSIX_HOST_READ\/SAFE_READ_ONLY/u);
  assert.match(result.message, /stage 2 POSIX_HOST_READ\/SAFE_READ_ONLY/u);

  const temporary = await temporaryAudit();
  try {
    appendAudit(result, { sessionId: 's', agentType: 'diagnostic-operator', permissionMode: 'default' }, { OPS_COMMAND_GUARD_AUDIT_PATH: temporary.auditPath });
    const record = JSON.parse((await temporary.read()).trim());
    assert.deepEqual(record.findings.map(({ stage }) => stage), [1, 2]);
    assert.equal(record.findings.every(({ ruleId }) => ruleId === 'POSIX_HOST_READ'), true);
  } finally {
    await temporary.cleanup();
  }
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
