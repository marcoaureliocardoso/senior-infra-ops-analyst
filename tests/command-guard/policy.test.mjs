import assert from 'node:assert/strict';
import test from 'node:test';

import { analyzeCommand } from '../../skills/command-driven-operations/scripts/command-guard/policy.mjs';
import { parseHookEvent } from '../../skills/command-driven-operations/scripts/command-guard/contract.mjs';
import { validEvent } from './helpers.mjs';

function analyze(command, permissionMode = 'default') {
  return analyzeCommand(parseHookEvent(JSON.stringify(validEvent({
    permission_mode: permissionMode,
    tool_input: { command },
  }))));
}

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

test('initial operational catalogue covers documented infrastructure families', () => {
  const reads = [
    ['docker ps', 'CONTAINER'],
    ['aws --profile ops --region us-east-1 ec2 describe-instances --max-items 20', 'AWS'],
    ['az account show --subscription lab', 'AZURE'],
    ['gcloud compute instances list --project lab --limit 20', 'GCP'],
    ['psql -h db.example.invalid -d app -c "SELECT 1"', 'POSTGRES'],
    ['mysql -h db.example.invalid -D app -e "SHOW STATUS"', 'MYSQL'],
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
    'curl -X POST https://api.example.invalid/v1/reload',
    'Restart-Service -Name spooler',
  ];
  for (const command of mutations) {
    assert.equal(analyze(command).decision, 'ask', command);
    assert.equal(analyze(command, 'bypassPermissions').decision, 'allow', command);
  }
  assert.equal(analyze('docker restart web').reasonCode, 'DENY_AMBIGUOUS_TARGET');
  assert.equal(analyze('aws ec2 stop-instances --instance-ids i-123').reasonCode, 'DENY_AMBIGUOUS_TARGET');
});

test('destructive database, container, cloud, HTTP, and Git operations always ask', () => {
  const destructive = [
    'docker --context lab rm web',
    'aws --profile ops --region us-east-1 ec2 terminate-instances --instance-ids i-123',
    'psql -h db.example.invalid -d app -c "DROP TABLE demo"',
    'redis-cli -h cache.example.invalid DEL key',
    'curl -X DELETE https://api.example.invalid/v1/resource/1',
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
