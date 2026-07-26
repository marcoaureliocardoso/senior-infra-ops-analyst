import assert from 'node:assert/strict';

import { lexBash } from '../../skills/command-driven-operations/scripts/command-guard/bash-lexer.mjs';
import { lookupFamily } from '../../skills/command-driven-operations/scripts/command-guard/catalogue.mjs';
import { buildComposition } from '../../skills/command-driven-operations/scripts/command-guard/composition.mjs';
import { parseHookEvent } from '../../skills/command-driven-operations/scripts/command-guard/contract.mjs';
import { classifyCredentials } from '../../skills/command-driven-operations/scripts/command-guard/credential-flow.mjs';
import { LIMITS } from '../../skills/command-driven-operations/scripts/command-guard/limits.mjs';
import { analyzeCommand } from '../../skills/command-driven-operations/scripts/command-guard/policy.mjs';
import { lexPowerShell } from '../../skills/command-driven-operations/scripts/command-guard/powershell-lexer.mjs';
import { detectSensitiveSpans } from '../../skills/command-driven-operations/scripts/command-guard/redaction.mjs';
import { validEvent } from './helpers.mjs';
import { REVIEW_REGRESSION_FIXTURES } from './review-regression-fixtures.mjs';

function analyze(command, permissionMode = 'bypassPermissions') {
  return analyzeCommand(parseHookEvent(JSON.stringify(validEvent({
    permission_mode: permissionMode,
    tool_input: { command },
  }))));
}

function stage(command) {
  return buildComposition(lexBash(command)).stages[0];
}

const GRAMMAR = Object.freeze({
  stage: ['uname -a', ''],
  pipeline: ['uname -a | head -n 1', 'uname -a |'],
  and: ['uname -a && uptime', 'uname -a &&'],
  or: ['uname -a || uptime', 'uname -a ||'],
  sequence: ['uname -a ; uptime', 'uname -a ;'],
  redirect: ['uname -a > /dev/null', 'uname -a >'],
});

const FAMILY = Object.freeze({
  POSIX_HOST_READ: ['uname -a', 'ip link delete dev eth0'],
  LOG_READ: ['journalctl -u nginx -n 10', 'journalctl -u nginx'],
  SERVICE_CONTROL: ['systemctl status nginx', 'systemctl frobnicate nginx'],
  KUBERNETES: ['kubectl --context lab --namespace demo get pods', 'kubectl --context lab exec pod -- id'],
  CONTAINER: ['docker ps', 'docker exec web id'],
  AWS: ['aws --profile ops --region us-east-1 ec2 describe-instances --max-items 10', 'aws ec2 describe-instances'],
  AZURE: ['az vm list --subscription lab --top 10', 'az vm list --subscription lab'],
  GCP: ['gcloud compute instances list --project lab --limit 10', 'gcloud compute instances list --project lab'],
  POSTGRES: ['psql -h db.example.invalid -d app -c "SELECT 1"', 'psql -h db.example.invalid -d app -c "SELECT * FROM events"'],
  MYSQL: ['mysql -h db.example.invalid -D app -e "SHOW STATUS"', 'mysql -h db.example.invalid -D app -e "SELECT * FROM events"'],
  MONGODB: ['mongosh mongodb://db.example.invalid/app --eval "db.serverStatus()"', 'mongosh mongodb://db.example.invalid/app --eval "runProgram(\'sh\')"'],
  REDIS: ['redis-cli -h cache.example.invalid INFO', 'redis-cli -h cache.example.invalid FROBNICATE'],
  NETWORK_READ: ['ping -c 3 192.0.2.1', 'ping 192.0.2.1'],
  PACKET_CAPTURE: ['tcpdump -i eth0 -c 10 host 192.0.2.1', 'tcpdump -i eth0 host 192.0.2.1'],
  HTTP: ['curl https://api.example.invalid/health', 'curl --unknown-option value https://api.example.invalid/health'],
  REMOTE: ['ssh ops@example.invalid "uname -a"', 'ssh -o ProxyCommand=bad ops@example.invalid "uname -a"'],
  PRIVILEGE: ['sudo systemctl status nginx', 'sudo mysteryctl status'],
  GIT_CI: ['git status', 'git frobnicate'],
  POWERSHELL_READ: ['Get-Service', 'Get-Content secret.txt'],
  WINDOWS_CONTROL: ['Restart-Service -Name spooler', 'Set-Item x y'],
  FILTER: ['grep Linux', 'grep root /etc/passwd'],
  DECRYPTOR: ['gpg --decrypt credential.gpg', 'gpg --encrypt plaintext'],
});

const REASONS = Object.freeze({
  ALLOW_NARROW_READ: ['uname -a', 'default'],
  ALLOW_BYPASS_BOUNDED_READ: ['ping -c 3 192.0.2.1', 'bypassPermissions'],
  ALLOW_BYPASS_CATALOGUED_CHANGE: ['systemctl restart nginx', 'bypassPermissions'],
  ASK_BOUNDED_READ: ['ping -c 3 192.0.2.1', 'default'],
  ASK_NORMAL_MODE_CHANGE: ['systemctl restart nginx', 'default'],
  ASK_DESTRUCTIVE: ['kubectl --context lab --namespace demo delete pod demo-0', 'default'],
  ASK_LITERAL_CREDENTIAL_NORMAL: ['curl --token SYNTH_SECRET_coverage https://api.example.invalid/health', 'default'],
  ASK_EXTERNAL_SIDE_EFFECT: ['gh issue create --repo owner/project --title coverage --body coverage', 'bypassPermissions'],
  ASK_SENSITIVE_OPERATION: ['docker inspect web', 'bypassPermissions'],
  DENY_UNSUPPORTED_SYNTAX: ['echo $(id)', 'default'],
  DENY_SECRET_PERSISTENCE: ['TOKEN=SYNTH_SECRET_coverage curl https://api.example.invalid/health > output.log', 'default'],
  DENY_SECRET_OUTPUT: ['TOKEN=SYNTH_SECRET_coverage echo $TOKEN', 'default'],
  DENY_AUTHENTICATED_REDIRECT: ['curl -L -H "Authorization: Bearer SYNTH_SECRET_coverage" https://api.example.invalid/health', 'default'],
  DENY_PROVIDER_CONTROL_CREDENTIAL_ACCESS: ['curl -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" https://api.example.invalid/health', 'default'],
  DENY_UNKNOWN_CREDENTIAL_CONSUMER: ['TOKEN=SYNTH_SECRET_coverage mystery-consumer', 'default'],
  DENY_UNKNOWN_COMMAND: ['mysteryctl deploy production', 'default'],
  DENY_AMBIGUOUS_TARGET: ['docker restart web', 'default'],
});

const CREDENTIALS = Object.freeze({
  AUTHORIZATION: 'curl -H "Authorization: Bearer SYNTH_SECRET_coverage" https://api.example.invalid',
  COOKIE: 'curl -H "Cookie: session=SYNTH_SECRET_coverage" https://api.example.invalid',
  VARIABLE: 'TOKEN=SYNTH_SECRET_coverage curl https://api.example.invalid',
  FLAG: 'curl --token SYNTH_SECRET_coverage https://api.example.invalid',
  BASIC_AUTH: 'curl -u user:SYNTH_SECRET_coverage https://api.example.invalid',
  POWERSHELL_PLAINTEXT: "ConvertTo-SecureString 'SYNTH_SECRET_coverage' -AsPlainText",
  URI_USERINFO: 'curl https://user:SYNTH_SECRET_coverage@api.example.invalid',
  STDIN_DIRECT: 'gpg --decrypt credential.gpg | sudo -S systemctl status nginx',
  PROVIDER_CACHE: 'AWS_PROFILE=ops aws --profile ops --region us-east-1 ec2 describe-instances --max-items 10',
  PROTECTED_FILE: 'curl --cert /secure/client.pem https://api.example.invalid',
});

function runGrammar(item) {
  const [positive, negative] = GRAMMAR[item];
  assert.doesNotThrow(() => buildComposition(lexBash(positive)));
  assert.throws(() => buildComposition(lexBash(negative)));
}

function operatorCommand(operator) {
  if (operator === '2>&1') return `a ${operator}`;
  return operator.includes('>') || operator === '<' ? `a ${operator} sink` : `a ${operator} b`;
}

function runOperator(item, lexer) {
  assert.ok(lexer(operatorCommand(item)).tokens.some(({ cooked }) => cooked === item));
  assert.equal(lexer(`a '${item}'`).tokens.some(({ kind, cooked }) => kind === 'operator' && cooked === item), false);
}

function runFamily(item) {
  const [positive, negative] = FAMILY[item];
  assert.equal(lookupFamily(stage(positive))?.policyId, item);
  assert.notEqual(lookupFamily(stage(negative))?.policyId, item);
}

function runReason(item) {
  const [command, mode] = REASONS[item];
  assert.equal(analyze(command, mode).reasonCode, item);
  const contrast = item === 'ALLOW_NARROW_READ' ? analyze('mysteryctl', 'default') : analyze('uname -a', 'default');
  assert.notEqual(contrast.reasonCode, item);
}

function rawAtBytes(target) {
  const base = JSON.stringify(validEvent());
  assert.ok(Buffer.byteLength(base, 'utf8') < target);
  return `${base}${' '.repeat(target - Buffer.byteLength(base, 'utf8'))}`;
}

function nestedEvent(depth) {
  const value = validEvent();
  let nested = true;
  for (let index = 0; index < depth - 2; index += 1) nested = { child: nested };
  value.future = nested;
  return JSON.stringify(value);
}

function repeatedPipeline(stages) {
  return Array(stages).fill('uname').join(' | ');
}

function repeatedRedirects(count) {
  return `uname ${Array(count).fill('> /dev/null').join(' ')}`;
}

function assertParses(raw) {
  assert.doesNotThrow(() => parseHookEvent(raw));
}

function runLimit(item) {
  const n = LIMITS[item];
  if (item === 'inputBytes') {
    assertParses(rawAtBytes(n - 1));
    assertParses(rawAtBytes(n));
    assert.throws(() => parseHookEvent(rawAtBytes(n + 1)), /size/u);
  } else if (item === 'jsonDepth') {
    for (const value of [n - 1, n]) assert.throws(() => parseHookEvent(nestedEvent(value)), (error) => !/depth/u.test(error.message));
    assert.throws(() => parseHookEvent(nestedEvent(n + 1)), /depth/u);
  } else if (item === 'commandChars') {
    for (const value of [n - 1, n]) assertParses(JSON.stringify(validEvent({ tool_input: { command: 'x'.repeat(value) } })));
    assert.throws(() => parseHookEvent(JSON.stringify(validEvent({ tool_input: { command: 'x'.repeat(n + 1) } }))), /length/u);
  } else if (item === 'timeoutMs') {
    for (const value of [n - 1, n]) assertParses(JSON.stringify(validEvent({ tool_input: { command: 'uname', timeout: value } })));
    assert.throws(() => parseHookEvent(JSON.stringify(validEvent({ tool_input: { command: 'uname', timeout: n + 1 } }))), /timeout/u);
  } else if (item === 'stages') {
    for (const value of [n - 1, n]) assert.doesNotThrow(() => lexBash(repeatedPipeline(value)));
    assert.throws(() => lexBash(repeatedPipeline(n + 1)), /stage/u);
  } else if (item === 'redirects') {
    for (const value of [n - 1, n]) assert.doesNotThrow(() => buildComposition(lexBash(repeatedRedirects(value))));
    assert.throws(() => buildComposition(lexBash(repeatedRedirects(n + 1))), /redirect/u);
  } else if (item === 'tokens') {
    for (const value of [n - 1, n]) assert.doesNotThrow(() => lexBash(Array(value).fill('x').join(' ')));
    assert.throws(() => lexBash(Array(n + 1).fill('x').join(' ')), /token/u);
  } else if (item === 'tokenChars') {
    for (const value of [n - 1, n]) assert.doesNotThrow(() => lexBash('x'.repeat(value)));
    assert.throws(() => lexBash('x'.repeat(n + 1)), /token/u);
  } else if (item === 'outputRows') {
    for (const value of [n - 1, n]) assert.notEqual(analyze(`journalctl -n ${value}`).decision, 'deny');
    assert.equal(analyze(`journalctl -n ${n + 1}`).decision, 'deny');
  } else if (item === 'fanOut') {
    for (const value of [n - 1, n]) assert.notEqual(analyze(`ping -c ${value} 192.0.2.1`).decision, 'deny');
    assert.equal(analyze(`ping -c ${n + 1} 192.0.2.1`).decision, 'deny');
  } else if (item === 'auditFieldChars') {
    for (const value of [n - 1, n]) assertParses(JSON.stringify(validEvent({ session_id: 's'.repeat(value) })));
    assert.throws(() => parseHookEvent(JSON.stringify(validEvent({ session_id: 's'.repeat(n + 1) }))), /session_id/u);
  } else {
    assert.fail(`unhandled limit:${item}`);
  }
}

function runCredential(item) {
  const command = CREDENTIALS[item];
  const composition = buildComposition(lexBash(command));
  const result = classifyCredentials(composition, command, detectSensitiveSpans(command));
  assert.equal(result.metadata?.transport, item);
  const plain = classifyCredentials(buildComposition(lexBash('uname -a')), 'uname -a');
  assert.equal(plain.metadata, null);
}

function runEdge(item) {
  const cases = {
    QUOTED_SEPARATOR: () => assert.equal(lexBash("echo ';'").tokens.some(({ kind }) => kind === 'operator'), false),
    UNMATCHED_QUOTE: () => assert.throws(() => lexBash("echo '"), /unmatched/u),
    DYNAMIC_SUBSTITUTION: () => assert.throws(() => lexBash('echo $(id)'), /unsupported/u),
    EMPTY_STAGE: () => assert.throws(() => buildComposition(lexBash('uname |')), /empty/u),
    REDIRECT_MISSING_TARGET: () => assert.throws(() => buildComposition(lexBash('uname >')), /destination/u),
    UNKNOWN_MODE: () => assert.equal(analyze('systemctl restart nginx', 'future-mode').decision, 'ask'),
    DUPLICATE_SECURITY_KEY: () => assert.throws(() => parseHookEvent(JSON.stringify(validEvent()).replace('"session_id"', '"session_id":"duplicate","session_id"')), /duplicate/u),
    AUDIT_FAILURE: () => assert.equal(analyze('uname -a').decision, 'allow'),
  };
  cases[item]();
}

function runReview(item) {
  const fixture = REVIEW_REGRESSION_FIXTURES.find(({ id }) => id === item);
  assert.ok(fixture);
  const result = analyze(fixture.command, fixture.permissionMode ?? 'bypassPermissions');
  assert.equal(result.decision, fixture.expectedDecision);
  if (fixture.expectedRisk) assert.equal(result.risk, fixture.expectedRisk);
}

export function executeCoverageFixture({ id, category, item }) {
  assert.equal(id, `${category}:${item}:executable`);
  const runners = {
    grammar: () => runGrammar(item),
    bashOperators: () => runOperator(item, lexBash),
    powershellOperators: () => runOperator(item, lexPowerShell),
    commandFamilies: () => runFamily(item),
    reasonCodes: () => runReason(item),
    limits: () => runLimit(item),
    credentialTransports: () => runCredential(item),
    edgeCases: () => runEdge(item),
    reviewRegressions: () => runReview(item),
  };
  assert.ok(runners[category], `unhandled category:${category}`);
  runners[category]();
}
