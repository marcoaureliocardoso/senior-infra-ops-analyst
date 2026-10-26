import assert from 'node:assert/strict';
import path from 'node:path';
import test from 'node:test';

import { analyzeCommand } from '../../skills/command-driven-operations/scripts/command-guard/policy.mjs';
import { parseHookEvent } from '../../skills/command-driven-operations/scripts/command-guard/contract.mjs';
import { validEvent } from './helpers.mjs';

function analyze(command, permissionMode = 'default', native = {}) {
  return analyzeCommand(parseHookEvent(JSON.stringify(validEvent({
    permission_mode: permissionMode,
    ...native,
    tool_input: { command },
  }))));
}

const BROWSER_RUNNER = path.resolve('skills/browser-operations/scripts/browser-runner.mjs');
const browserCommand = (args) => `node ${JSON.stringify(BROWSER_RUNNER)} ${args.join(' ')}`;
const workflowCommand = () => browserCommand([
  '--step workflow --operation-id op-workflow-123 --session-id session-workflow-123',
  '--role network-edge-operator --objective-ref change-42 --target edge-router-1',
  '--environment production --service-origin http://127.0.0.1:43111',
  '--identity-ref vault:network-admin --credential-transport vault --permission-mode normal',
  '--action navigate --action submit --action inspect --effect LOW_RISK_CHANGE',
  '--risk LOW_RISK_CHANGE --precondition-ref reachable --validation-ref interface-state',
  '--compensation-ref restore-interface --expires-in-seconds 600',
  '--workflow-step eyJzdGVwIjoibmF2aWdhdGUiLCJvcmlnaW4iOiJodHRwOi8vMTI3LjAuMC4xOjQzMTExIn0',
  '--workflow-step eyJzdGVwIjoic3VibWl0Iiwib3JpZ2luIjoiaHR0cDovLzEyNy4wLjAuMTo0MzExMSIsImxvY2F0b3JSb2xlIjoiYnV0dG9uIiwiZWZmZWN0IjoiTE9XX1JJU0tfQ0hBTkdFIn0',
  '--validation-step eyJzdGVwIjoiaW5zcGVjdCIsIm9yaWdpbiI6Imh0dHA6Ly8xMjcuMC4wLjE6NDMxMTEiLCJsb2NhdG9yUm9sZSI6InN0YXR1cyIsInByZWRpY2F0ZSI6InByZXNlbnQiLCJleHBlY3RlZFJlZiI6ImVudjpPUFNfQlJPV1NFUl9WQUxVRV9FWFBFQ1RFRCIsImV4cGVjdFJlZiI6ImludGVyZmFjZS1zdGF0ZSJ9',
]);


test('protected browser runner is an exact always-confirmed command family', () => {
  const open = browserCommand([
    '--step open --operation-id op-123 --session-id session-123 --role network-edge-operator',
    '--objective-ref change-42 --target edge-router-1 --environment production',
    '--service-origin https://router.example.invalid --identity-ref vault:network-admin',
    '--credential-transport vault --permission-mode normal --action inspect --action validate',
    '--effect LOW_RISK_CHANGE --risk LOW_RISK_CHANGE --precondition-ref reachable',
    '--validation-ref interface-state --compensation-ref restore-interface --expires-in-seconds 600',
  ]);
  for (const mode of ['default', 'bypassPermissions']) {
    const result = analyze(open.replace('--permission-mode normal', `--permission-mode ${mode}`), mode,
      { session_id: 'session-123', agent_type: 'network-edge-operator' });
    assert.equal(result.policyId, 'BROWSER_PROTECTED_RUNNER');
    assert.equal(result.risk, 'LOW_RISK_CHANGE');
    assert.equal(result.decision, 'ask');
    assert.equal(result.reasonCode, 'ASK_SENSITIVE_OPERATION');
  }
  const inspect = analyze(browserCommand([
    '--operation-id op-123 --step inspect --origin https://router.example.invalid',
    '--locator-role status --expect-ref status-readable',
  ]));
  assert.equal(inspect.reasonCode, 'DENY_BROWSER_BINDING');
  assert.equal(inspect.decision, 'deny');
});


test('one-shot browser workflows always ask even in bypassPermissions', () => {
  for (const mode of ['default', 'bypassPermissions']) {
    const result = analyze(workflowCommand().replace('--permission-mode normal', `--permission-mode ${mode}`), mode,
      { session_id: 'session-workflow-123', agent_type: 'network-edge-operator' });
    assert.equal(result.policyId, 'BROWSER_PROTECTED_RUNNER');
    assert.equal(result.decision, 'ask');
    assert.equal(result.reasonCode, 'ASK_SENSITIVE_OPERATION');
  }
});


test('browser runner catalogue rejects path and grammar escape hatches', () => {
  const rejected = [
    `node ./skills/browser-operations/scripts/browser-runner.mjs --operation-id op-123 --step close`,
    `node ${JSON.stringify(`${BROWSER_RUNNER}.copy`)} --operation-id op-123 --step close`,
    'node -e "process.exit(0)"',
    browserCommand(['--operation-id op-123 --step fill --origin https://router.example.invalid --locator-role textbox --value literal']),
    browserCommand(['--operation-id op-123 --step navigate --origin javascript:alert(1)']),
    browserCommand(['--operation-id op-123 --step navigate --origin https://']),
    browserCommand(['--operation-id op-123 --step inspect --origin https://router.example.invalid --locator-role status --expect-ref ok --unknown x']),
  ];
  for (const command of rejected) {
    assert.equal(analyze(command).decision, 'deny', command);
  }
});

test('narrow read and bounded read pipeline allow in normal mode', () => {
  assert.equal(analyze('uname -a').decision, 'allow');
  assert.equal(analyze('journalctl -u nginx -n 20 | grep error | head -n 5').decision, 'allow');
});

test('catalogued change asks normally and allows in bypassPermissions', () => {
  assert.equal(analyze('systemctl restart nginx').decision, 'ask');
  assert.equal(analyze('systemctl restart nginx', 'bypassPermissions').decision, 'allow');
  assert.equal(analyze('service nginx status').decision, 'allow');
  assert.equal(analyze('service nginx restart').decision, 'ask');
  assert.equal(analyze('service nginx restart', 'bypassPermissions').decision, 'allow');
});

test('destructive action asks in every permission mode', () => {
  const command = 'kubectl --context lab --namespace demo delete pod demo-0';
  assert.equal(analyze(command).decision, 'ask');
  assert.equal(analyze(command, 'bypassPermissions').decision, 'ask');
});

test('unknown, unsupported, and ambiguous mutations deny', () => {
  assert.equal(analyze('mysteryctl deploy production').decision, 'deny');
  assert.equal(analyze('kubectl scale deployment api --replicas 0').reasonCode, 'DENY_AMBIGUOUS_TARGET');
  assert.equal(analyze('echo ok > /tmp/result').decision, 'deny');
});

test('unknown future mode uses conservative normal semantics', () => {
  const result = analyze('systemctl restart nginx', 'futureAutonomy');
  assert.equal(result.decision, 'ask');
  assert.ok(result.modifiers.includes('UNKNOWN_MODE_CONSERVATIVE'));
});

test('explicit literal PowerShell read pipeline is analyzed separately', () => {
  const command = `pwsh -NoProfile -Command "Get-Service | Where-Object Status -eq 'Running'"`;
  assert.equal(analyze(command).decision, 'allow');
});

test('PowerShell wrappers require one canonical profile-free option set', () => {
  for (const command of [
    'pwsh -Command "Get-Service"',
    'powershell -Command "Get-Service"',
    'pwsh -NoProfile -NoProfile -Command "Get-Service"',
  ]) {
    assert.equal(analyze(command).reasonCode, 'DENY_POWERSHELL_PROFILE', command);
  }

  for (const command of [
    'pwsh -NoP -Command "Get-Service"',
    'pwsh -NoLog -NoProfile -Command "Get-Service"',
    'pwsh -NoProfile -NoLogo -NoLogo -Command "Get-Service"',
    'pwsh -Sta -Mta -NoProfile -Command "Get-Service"',
    'pwsh -NoProfile -Command "Get-Service" ignored',
    'pwsh -NoProfile -Command "Get-Service" -Command "Get-Process"',
  ]) {
    assert.equal(analyze(command).reasonCode, 'DENY_UNSUPPORTED_SYNTAX', command);
  }

  for (const command of [
    'pwsh -NoProfile -Command "Get-Service"',
    'powershell -NoProfile -NonInteractive -NoLogo -Command "Get-Service"',
    'pwsh -noprofile -sta -command "Get-Service"',
    'pwsh -NoProfile -Mta -Command "Get-Service"',
  ]) {
    assert.equal(analyze(command).decision, 'allow', command);
  }
});

test('initial operational catalogue covers documented infrastructure families', () => {
  const reads = [
    ['docker ps', 'CONTAINER'],
    ['aws --profile ops --region us-east-1 ec2 describe-instances --max-items 20', 'AWS'],
    ['az account show --subscription lab', 'AZURE'],
    ['gcloud compute instances list --project lab --limit 20', 'GCP'],
    ['psql -h db.example.invalid -p 5432 -U appuser -d app -c "SELECT 1"', 'POSTGRES'],
    ['mysql -h db.example.invalid -P 3306 -u appuser -D app -e "SHOW STATUS"', 'MYSQL'],
    ['mongosh mongodb://db.example.invalid/app --eval "db.serverStatus()"', 'MONGODB'],
    ['redis-cli -h cache.example.invalid INFO', 'REDIS'],
    ['git status', 'GIT_CI'],
    ['gh repo view --repo owner/project', 'GIT_CI'],
  ];
  for (const [command, policyId] of reads) {
    const result = analyze(command);
    assert.equal(result.decision, 'allow', command);
    assert.equal(result.policyId, policyId, command);
  }
});

test('bounded probes and packet captures ask normally and allow in bypass mode', () => {
  for (const command of [
    'ping -c 3 192.0.2.10',
    'tcpdump -i eth0 -c 20 host 192.0.2.10',
  ]) {
    assert.equal(analyze(command).decision, 'ask', command);
    assert.equal(analyze(command, 'bypassPermissions').decision, 'allow', command);
  }
});

test('catalogued remote and platform mutations require explicit binding', () => {
  const mutations = [
    'docker --context lab restart web',
    'aws --profile ops --region us-east-1 ec2 stop-instances --instance-ids i-123',
    'az vm restart --subscription lab --resource-group rg --name vm1',
    'gcloud compute instances stop vm1 --project lab --zone us-central1-a',
    'Restart-Service -Name spooler',
  ];
  for (const command of mutations) {
    assert.equal(analyze(command).decision, 'ask', command);
    assert.equal(analyze(command, 'bypassPermissions').decision, 'allow', command);
  }
  assert.equal(analyze('docker restart web').reasonCode, 'DENY_AMBIGUOUS_TARGET');
  assert.equal(analyze('aws ec2 stop-instances --instance-ids i-123').reasonCode, 'DENY_AMBIGUOUS_TARGET');
});

test('uncatalogued mutable HTTP operations always ask as external effects', () => {
  for (const mode of ['default', 'bypassPermissions']) {
    const result = analyze('curl -q -X POST https://api.example.invalid/v1/reload', mode);
    assert.equal(result.decision, 'ask', mode);
    assert.equal(result.risk, 'DISRUPTIVE_CHANGE', mode);
    assert.ok(result.modifiers.includes('EXTERNAL_SIDE_EFFECT'), mode);
  }
});

test('Git workflow controls always ask as external effects', () => {
  for (const mode of ['default', 'bypassPermissions']) {
    const result = analyze('gh workflow run deploy.yml --repo owner/project', mode);
    assert.equal(result.decision, 'ask', mode);
    assert.equal(result.risk, 'DISRUPTIVE_CHANGE', mode);
    assert.ok(result.modifiers.includes('EXTERNAL_SIDE_EFFECT'), mode);
  }
});

test('destructive database, container, cloud, HTTP, and Git operations always ask', () => {
  const destructive = [
    'docker --context lab rm web',
    'aws --profile ops --region us-east-1 ec2 terminate-instances --instance-ids i-123',
    'psql -h db.example.invalid -p 5432 -U appuser -d app -c "DROP TABLE demo"',
    'redis-cli -h cache.example.invalid DEL key',
    'curl -q -X DELETE https://api.example.invalid/v1/resource/1',
    'gh repo delete owner/project --yes --repo owner/project',
  ];
  for (const command of destructive) {
    assert.equal(analyze(command).decision, 'ask', command);
    assert.equal(analyze(command, 'bypassPermissions').decision, 'ask', command);
  }
});

test('SSH accepts only an explicit host and one literal catalogued remote stage', () => {
  assert.equal(analyze('ssh ops@example.invalid "uname -a"').decision, 'allow');
  assert.equal(analyze('ssh ops@example.invalid "systemctl restart nginx"').decision, 'ask');
  assert.equal(analyze('ssh ops@example.invalid "systemctl restart nginx"', 'bypassPermissions').decision, 'allow');
  assert.equal(analyze('ssh ops@example.invalid "uname; id"').decision, 'deny');
  assert.equal(analyze('ssh "$HOST" "uname -a"').decision, 'deny');
});
