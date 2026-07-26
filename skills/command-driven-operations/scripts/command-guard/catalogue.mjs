import { lexBash } from './bash-lexer.mjs';
import { buildComposition } from './composition.mjs';
import { LIMITS } from './limits.mjs';

const POSIX_READ = new Set(['uname', 'uptime', 'free', 'df', 'lsblk', 'findmnt']);
const FILTER = new Set(['grep', 'rg', 'head', 'tail', 'cut', 'sort', 'uniq', 'wc']);
const PS_FILTER = new Set(['where-object', 'select-object', 'sort-object', 'group-object', 'measure-object', 'format-table']);
const CONTAINERS = new Set(['docker', 'podman', 'nerdctl', 'ctr', 'crictl']);
const PS_READ = new Set([
  'get-service', 'get-process', 'get-ciminstance', 'get-computerinfo',
  'get-hotfix', 'get-netadapter', 'get-netipconfiguration', 'get-netroute',
  'get-dnsclientcache', 'get-volume', 'get-disk', 'get-partition',
  'test-connection', 'test-netconnection', 'resolve-dnsname',
]);

export const POLICY_IDS = Object.freeze([
  'POSIX_HOST_READ', 'LOG_READ', 'SERVICE_CONTROL', 'KUBERNETES', 'CONTAINER',
  'AWS', 'AZURE', 'GCP', 'POSTGRES', 'MYSQL', 'MONGODB', 'REDIS',
  'NETWORK_READ', 'PACKET_CAPTURE', 'HTTP', 'REMOTE', 'PRIVILEGE', 'GIT_CI',
  'POWERSHELL_READ', 'WINDOWS_CONTROL', 'FILTER', 'DECRYPTOR',
]);
export const COMMAND_FAMILIES = Object.freeze(POLICY_IDS.filter((id) => id !== 'FILTER'));
export const FILTER_FAMILIES = Object.freeze(['FILTER']);

function executableIndex(argv) {
  const allowedAssignments = new Set([
    'AWS_PROFILE', 'AZURE_CONFIG_DIR', 'CLOUDSDK_CONFIG', 'KUBECONFIG',
    'SSH_AUTH_SOCK', 'GIT_ASKPASS', 'PGPASSWORD', 'MYSQL_PWD', 'SSHPASS',
    'GH_TOKEN', 'GITHUB_TOKEN', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
    'AWS_SESSION_TOKEN', 'OPS_CREDENTIAL_IDENTITY',
  ]);
  for (let index = 0; index < argv.length; index += 1) {
    const match = argv[index].match(/^([A-Za-z_][A-Za-z0-9_]*)=/u);
    if (!match) return index;
    if (!allowedAssignments.has(match[1])) return -1;
  }
  return -1;
}

function option(argv, ...names) {
  for (const name of names) {
    const index = argv.indexOf(name);
    if (index >= 0) return argv[index + 1] ?? null;
    const inline = argv.find((word) => word.startsWith(`${name}=`));
    if (inline) return inline.slice(name.length + 1) || null;
  }
  return null;
}

function optionCaseInsensitive(argv, ...names) {
  const lowered = names.map((name) => name.toLowerCase());
  for (let index = 0; index < argv.length; index += 1) {
    const word = argv[index];
    const lower = word.toLowerCase();
    const exact = lowered.indexOf(lower);
    if (exact >= 0) return argv[index + 1] ?? null;
    const inline = lowered.findIndex((name) => lower.startsWith(`${name}=`));
    if (inline >= 0) return word.slice(names[inline].length + 1) || null;
  }
  return null;
}

function result(policyId, risk, target, environment = null, modifiers = [], extra = {}) {
  return { policyId, risk, target: target ?? null, environment: environment ?? null, modifiers, ...extra };
}

function queryRisk(query, read, low, disruptive, destructive) {
  const normalized = query.trim().replace(/^["']|["']$/gu, '').trim().toUpperCase();
  if (destructive.some((pattern) => pattern.test(normalized))) return 'DESTRUCTIVE';
  if (disruptive.some((pattern) => pattern.test(normalized))) return 'DISRUPTIVE_CHANGE';
  if (low.some((pattern) => pattern.test(normalized))) return 'LOW_RISK_CHANGE';
  if (read.some((pattern) => pattern.test(normalized))) return 'SAFE_READ_ONLY';
  return null;
}

function boundedRelationalRead(query) {
  const normalized = query.trim().replace(/^["']|["']$/gu, '').trim().toUpperCase();
  const withoutTerminal = normalized.replace(/;\s*$/u, '');
  if (withoutTerminal.includes(';') || /--|\/\*|\*\//u.test(withoutTerminal)) return false;
  if (/\b(?:INTO\s+OUTFILE|INTO\s+DUMPFILE|FOR\s+UPDATE|PG_READ_FILE|LO_EXPORT|COPY|PG_TERMINATE_BACKEND|PG_CANCEL_BACKEND|DBMS_|SLEEP\s*\()\b/u.test(withoutTerminal)) return false;
  const safeFunctions = new Set(['AVG', 'COALESCE', 'COUNT', 'DATE_TRUNC', 'LOWER', 'MAX', 'MIN', 'NOW', 'SUM', 'UPPER']);
  const functions = [...withoutTerminal.matchAll(/\b([A-Z_][A-Z0-9_.]*)\s*\(/gu)].map((match) => match[1]);
  if (functions.some((name) => !safeFunctions.has(name))) return false;
  if (!/^SELECT\b/u.test(withoutTerminal) || !/\bFROM\b/u.test(withoutTerminal)) return true;
  const match = withoutTerminal.match(/\bLIMIT\s+(\d+)\b/u);
  return Boolean(match && boundedInteger(match[1], LIMITS.outputRows));
}

function commandPrefix(words) {
  const prefix = [];
  for (const word of words.slice(1)) {
    if (word.startsWith('-')) break;
    prefix.push(word.toLowerCase());
  }
  return prefix;
}

function cloudAction(argv, prefixes) {
  return argv.find((word) => prefixes.some((prefix) => word.toLowerCase().startsWith(prefix)))?.toLowerCase() ?? null;
}

function boundedInteger(value, maximum, minimum = 1) {
  return /^\d+$/u.test(value ?? '') && Number(value) >= minimum && Number(value) <= maximum;
}

function commandWord(words, start, valueOptions = []) {
  const values = new Set(valueOptions);
  for (let index = start; index < words.length; index += 1) {
    const word = words[index];
    if (values.has(word)) { index += 1; continue; }
    if ([...values].some((name) => word.startsWith(`${name}=`))) continue;
    if (word.startsWith('-')) continue;
    return { word, index };
  }
  return null;
}

function positionalOperands(words, valueOptions = []) {
  const values = new Set(valueOptions);
  const operands = [];
  for (let index = 1; index < words.length; index += 1) {
    const word = words[index];
    if (values.has(word)) { index += 1; continue; }
    if ([...values].some((name) => word.startsWith(`${name}=`))) continue;
    if (word.startsWith('-')) continue;
    operands.push(word);
  }
  return operands;
}

function operandsAfter(words, start, valueOptions = []) {
  const values = new Set(valueOptions);
  const operands = [];
  for (let index = start + 1; index < words.length; index += 1) {
    const word = words[index];
    if (values.has(word)) { index += 1; continue; }
    if ([...values].some((name) => word.startsWith(`${name}=`))) continue;
    if (word.startsWith('-')) continue;
    operands.push(word);
  }
  return operands;
}

function isBoundedFilter(words, lower) {
  if (lower === 'grep' || lower === 'rg') {
    if (words.some((word) => /^(?:-r|-R|--recursive|--files|--file|-f|--glob)(?:=|$)/u.test(word))) return false;
    const operands = positionalOperands(words, ['-e', '--regexp', '-m', '--max-count', '-A', '-B', '-C']);
    return operands.length === (words.includes('-e') || words.includes('--regexp') ? 0 : 1);
  }
  if (lower === 'head' || lower === 'tail') return positionalOperands(words, ['-n', '--lines', '-c', '--bytes']).length === 0;
  if (lower === 'cut') return positionalOperands(words, ['-b', '--bytes', '-c', '--characters', '-d', '--delimiter', '-f', '--fields']).length === 0;
  if (['sort', 'uniq', 'wc'].includes(lower)) return positionalOperands(words).length === 0;
  if (lower === 'sed') return words.includes('-n') && positionalOperands(words).length === 1;
  if (lower === 'awk') return positionalOperands(words).length === 1 && !words.some((word) => /system|getline|\|/iu.test(word));
  if (lower === 'jq') return positionalOperands(words, ['--arg', '--argjson']).length === 1 && !words.some((word) => /^(?:--from-file|-f|--run-tests)$/u.test(word));
  return true;
}

function gitCiFamily(words, lower) {
  const joined = words.slice(1).join(' ').toLowerCase();
  const remote = option(words, '--repo') ?? (lower === 'gh' ? words.find((word) => word.includes('/')) : 'local');
  if (lower === 'git') {
    if (/^(?:status|log|diff|show)(?:\s|$)/u.test(joined) || /^branch(?:\s+--list)?$/u.test(joined)) {
      return result('GIT_CI', 'SAFE_READ_ONLY', 'local', 'local');
    }
    if (/^(?:reset\s+--hard|clean\s+.*-[A-Za-z]*f|push\s+.*(?:--force(?:-with-lease)?|-f\b|--delete|--mirror|--prune|(?:^|\s):[^\s]+|(?:^|\s)\+[^\s]+)|branch\s+-(?:d|D)\b|tag\s+(?:-d|--delete)\b)/u.test(joined)) {
      return result('GIT_CI', 'DESTRUCTIVE', words.at(-1) ?? 'local', 'local');
    }
    if (/^(?:add|commit|tag|branch|push)(?:\s|$)/u.test(joined)) {
      return result('GIT_CI', 'LOW_RISK_CHANGE', words.at(-1) ?? 'local', 'local');
    }
    return null;
  }
  if (/^(?:repo view|pr (?:view|list|checks)|run (?:view|list)|workflow (?:view|list))(?:\s|$)/u.test(joined)) {
    return result('GIT_CI', 'SAFE_READ_ONLY', remote, remote ?? null, [], { credentialConsumer: true });
  }
  if (/^(?:repo delete|release delete|pr merge)(?:\s|$)/u.test(joined)) {
    return result('GIT_CI', 'DESTRUCTIVE', remote, remote ?? null, [], { requiresExplicitBinding: true, credentialConsumer: true });
  }
  if (/^(?:workflow (?:run|rerun|cancel)|run (?:rerun|cancel)|deployment)(?:\s|$)/u.test(joined)) {
    return result('GIT_CI', 'DISRUPTIVE_CHANGE', remote, remote ?? null, ['EXTERNAL_SIDE_EFFECT'], { requiresExplicitBinding: true, credentialConsumer: true });
  }
  if (/^(?:pr (?:create|edit|comment|review|close|reopen)|issue (?:create|edit|comment|close|reopen)|release (?:create|edit|upload)|repo (?:clone|fork))\b/u.test(joined)) {
    return result('GIT_CI', 'LOW_RISK_CHANGE', remote, remote ?? null, ['EXTERNAL_SIDE_EFFECT'], { requiresExplicitBinding: true, credentialConsumer: true });
  }
  return null;
}

function remoteFamily(argv) {
  if (argv.some((word, index) => word === '-F' || word.startsWith('-F=') ||
    (word === '-o' && /^(?:ProxyCommand|LocalCommand|PermitLocalCommand|Match)=?/iu.test(argv[index + 1] ?? '')) ||
    /^-o(?:ProxyCommand|LocalCommand|PermitLocalCommand|Match)=?/iu.test(word))) return null;
  const host = argv.slice(1).find((word) => !word.startsWith('-') && !argv[argv.indexOf(word) - 1]?.startsWith('-'));
  const payload = argv.at(-1);
  if (!host || host === payload || /[$*?{}]/u.test(host) || !payload) return null;
  let composition;
  try { composition = buildComposition(lexBash(payload)); } catch { return null; }
  if (composition.stages.length !== 1 || composition.operators.length !== 0 || composition.redirects.length !== 0) return null;
  const nested = lookupFamily(composition.stages[0]);
  if (!nested || ['REMOTE', 'FILTER', 'DECRYPTOR'].includes(nested.policyId)) return null;
  return result('REMOTE', nested.risk, host, host, [...nested.modifiers, 'REMOTE_EXECUTION'], { credentialConsumer: true });
}

export function lookupFamily(stage) {
  const argv = [...stage.argv];
  const exeIndex = executableIndex(argv);
  if (exeIndex < 0) return null;
  const words = argv.slice(exeIndex);
  const exe = words[0];
  const lower = exe.toLowerCase();

  if (POSIX_READ.has(lower)) return result('POSIX_HOST_READ', 'SAFE_READ_ONLY', 'local');
  if (lower === 'ps') {
    if (words.slice(1).some((word) => /e/u.test(word.replace(/^-+/u, '')) || /--(?:format|cols|columns)=?.*(?:env|command)/iu.test(word))) return null;
    return result('POSIX_HOST_READ', 'SAFE_READ_ONLY', 'local', 'local', ['SENSITIVE_OUTPUT', 'ALWAYS_ASK']);
  }
  if (lower === 'ss') {
    if (words.includes('-K') || words.includes('--kill')) return result('POSIX_HOST_READ', 'DESTRUCTIVE', words.at(-1) ?? 'socket', 'local');
    return result('POSIX_HOST_READ', 'SAFE_READ_ONLY', 'local');
  }
  if (lower === 'mount') {
    if (words.slice(1).some((word) => !['-l', '--show-labels', '-v', '--verbose'].includes(word))) return null;
    return result('POSIX_HOST_READ', 'SAFE_READ_ONLY', 'local');
  }
  if (lower === 'ip') {
    const mutating = new Set(['add', 'append', 'change', 'delete', 'del', 'flush', 'replace', 'set', 'exec']);
    if (words.slice(1).some((word) => mutating.has(word.toLowerCase()))) return null;
    if (!words.slice(1).some((word) => /^(?:addr(?:ess)?|link|route|rule|neigh(?:bor)?)$/iu.test(word))) return null;
    return result('POSIX_HOST_READ', 'SAFE_READ_ONLY', 'local');
  }
  if (lower === 'journalctl') {
    const lines = option(words, '-n', '--lines');
    if (!boundedInteger(lines, LIMITS.outputRows)) return null;
    if (words.some((word) => /^(?:--vacuum-|--rotate|--flush|--sync|--relinquish-var)/u.test(word))) {
      return result('LOG_READ', 'DESTRUCTIVE', option(words, '-u', '--unit') ?? 'journal', 'local');
    }
    return result('LOG_READ', 'SAFE_READ_ONLY', option(words, '-u', '--unit') ?? 'local-log');
  }
  if (lower === 'dmesg') {
    if (!words.some((word) => /^(?:-l|--level)(?:=|$)/u.test(word))) return null;
    return result('LOG_READ', 'SAFE_READ_ONLY', 'kernel-log', 'local', ['SENSITIVE_OUTPUT', 'APPROVAL_REQUIRED']);
  }
  if ((FILTER.has(lower) || PS_FILTER.has(lower) || ['sed', 'awk', 'jq'].includes(lower)) && isBoundedFilter(words, lower)) {
    return result('FILTER', 'SAFE_READ_ONLY', null);
  }
  if (lower === 'test-connection') {
    const count = optionCaseInsensitive(words, '-Count');
    if (!boundedInteger(count, LIMITS.fanOut)) return null;
    return result('POWERSHELL_READ', 'SAFE_READ_ONLY', words[1] ?? 'network', 'network', ['ACTIVE_PROBE', 'APPROVAL_REQUIRED']);
  }
  if (PS_READ.has(lower)) return result('POWERSHELL_READ', 'SAFE_READ_ONLY', 'local');
  if (lower === 'gpg' || lower === 'age') {
    if (!words.some((word) => word === '-d' || word === '--decrypt')) return null;
    return result('DECRYPTOR', 'SAFE_READ_ONLY', words.at(-1), null, ['SENSITIVE_OUTPUT'], { sensitiveSource: true });
  }

  if (lower === 'sshpass') {
    const descriptor = words.findIndex((word) => word === '-d');
    if (descriptor < 0 || words[descriptor + 1] !== '0') return null;
    const nestedStart = descriptor + 2;
    const nested = lookupFamily({ ...stage, argv: words.slice(nestedStart) });
    if (!nested || nested.policyId !== 'REMOTE') return null;
    return result('REMOTE', nested.risk, nested.target, nested.environment, [...nested.modifiers, 'CREDENTIAL_STDIN'], { credentialConsumer: true });
  }

  if (lower === 'sudo') {
    const nestedStart = words.findIndex((word, index) => index > 0 && !word.startsWith('-'));
    const nested = nestedStart > 0 ? lookupFamily({ ...stage, argv: words.slice(nestedStart) }) : null;
    return nested ? result('PRIVILEGE', nested.risk, nested.target, nested.environment, [...nested.modifiers, 'PRIVILEGED'], { credentialConsumer: words.includes('-S') }) : null;
  }

  if (lower === 'systemctl' || lower === 'service') {
    if (words.some((word) => /^(?:-H|--host|--root|--image|--machine)(?:=|$)/u.test(word))) return null;
    const command = lower === 'service' ? { word: words[2], index: 2 } : commandWord(words, 1);
    const verb = command?.word;
    if (!verb) return null;
    if (!['status', 'show', 'is-active', 'is-enabled', 'enable', 'disable', 'start', 'stop', 'restart', 'reload', 'daemon-reload', 'mask', 'unmask'].includes(verb)) return null;
    const risk = ['status', 'show', 'is-active', 'is-enabled'].includes(verb) ? 'SAFE_READ_ONLY' : ['enable', 'disable'].includes(verb) ? 'LOW_RISK_CHANGE' : 'DISRUPTIVE_CHANGE';
    const target = lower === 'service' ? words[1] : command ? operandsAfter(words, command.index, ['--job-mode'])[0] : null;
    return result('SERVICE_CONTROL', risk, target, 'local', [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });
  }

  if (lower === 'kubectl' || (lower === 'k3s' && words[1] === 'kubectl')) {
    const verbs = ['get', 'describe', 'logs', 'events', 'version', 'cluster-info', 'label', 'annotate', 'apply', 'patch', 'scale', 'cordon', 'uncordon', 'delete', 'drain', 'replace'];
    const command = commandWord(words, lower === 'k3s' ? 2 : 1, ['--context', '--namespace', '-n', '--kubeconfig', '--cluster', '--user', '--request-timeout']);
    const verb = command?.word;
    if (!verb) return null;
    if (!verbs.includes(verb)) return null;
    if (verb === 'logs' && !boundedInteger(option(words, '--tail'), LIMITS.outputRows)) return null;
    const forceReplace = verb === 'replace' && words.includes('--force');
    const risk = ['get', 'describe', 'logs', 'events', 'version', 'cluster-info'].includes(verb) ? 'SAFE_READ_ONLY' : ['label', 'annotate'].includes(verb) ? 'LOW_RISK_CHANGE' : ['delete', 'drain'].includes(verb) || forceReplace ? 'DESTRUCTIVE' : 'DISRUPTIVE_CHANGE';
    const context = option(words, '--context');
    const namespace = option(words, '--namespace', '-n');
    const operands = command ? operandsAfter(words, command.index, ['--tail', '--replicas', '-f', '--filename', '--type', '-p', '--patch']) : [];
    const secretRead = ['get', 'describe'].includes(verb) && operands.some((word) => /^(?:secret|secrets|configmap|configmaps)$/iu.test(word));
    const fileTarget = option(words, '-f', '--filename');
    const singleton = ['cordon', 'uncordon', 'drain'].includes(verb);
    const target = words.includes('--all') ? null : fileTarget ?? (singleton ? operands[0] : operands.length >= 2 ? `${operands[0]}/${operands[1]}` : null);
    return result('KUBERNETES', risk, risk === 'SAFE_READ_ONLY' ? context : target, [context, namespace].filter(Boolean).join('@') || null, secretRead ? ['SENSITIVE_OUTPUT', 'ALWAYS_ASK'] : [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });
  }

  if (CONTAINERS.has(lower)) {
    const command = commandWord(words, 1, ['--context', '--host', '-H', '--config', '--connection']);
    const verb = command?.word;
    if (!verb || (verb === 'stats' && !words.includes('--no-stream'))) return null;
    if (!['ps', 'inspect', 'logs', 'stats', 'images', 'info', 'pull', 'tag', 'rename', 'start', 'stop', 'restart', 'pause', 'unpause', 'rm', 'rmi', 'prune', 'reset'].includes(verb)) return null;
    if (verb === 'logs' && !boundedInteger(option(words, '--tail'), LIMITS.outputRows)) return null;
    const risk = ['ps', 'inspect', 'logs', 'stats', 'images', 'info'].includes(verb) ? 'SAFE_READ_ONLY' : ['pull', 'tag', 'rename'].includes(verb) ? 'LOW_RISK_CHANGE' : ['rm', 'rmi', 'prune', 'reset'].includes(verb) ? 'DESTRUCTIVE' : 'DISRUPTIVE_CHANGE';
    const target = command ? operandsAfter(words, command.index, ['--time', '-t'])[0] : null;
    const modifiers = verb === 'inspect' ? ['SENSITIVE_OUTPUT', 'ALWAYS_ASK'] : [];
    return result('CONTAINER', risk, risk === 'SAFE_READ_ONLY' ? 'local' : target, option(words, '--context'), modifiers, { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });
  }

  if (lower === 'aws') {
    const service = commandWord(words, 1, ['--profile', '--region', '--endpoint-url', '--output', '--query'])?.index;
    const action = service === undefined ? null : words[service + 1]?.toLowerCase();
    const permittedAction = action && cloudAction([action], ['describe-', 'get-', 'list-', 'head-', 'create-tags', 'delete-tags', 'start-', 'stop-', 'reboot-', 'update-', 'delete-', 'terminate-', 'deregister-']);
    if (!permittedAction) return null;
    if (/^(?:describe|list)-/u.test(action) && !boundedInteger(option(words, '--max-items'), LIMITS.fanOut)) return null;
    const risk = /^(describe|get|list|head)-/u.test(action) ? 'SAFE_READ_ONLY' : /^(create-tags|delete-tags)$/u.test(action) ? 'LOW_RISK_CHANGE' : /^(delete|terminate|deregister)-/u.test(action) ? 'DESTRUCTIVE' : 'DISRUPTIVE_CHANGE';
    const environment = [option(words, '--profile'), option(words, '--region')].filter(Boolean).join('@') || null;
    const target = option(words, '--instance-ids', '--resource-arn', '--resources', '--resource-id', '--bucket');
    const sensitiveRead = risk === 'SAFE_READ_ONLY' && /(?:credential|password|secret|token)/u.test(action);
    return result('AWS', risk, risk === 'SAFE_READ_ONLY' ? target ?? action : target, environment, sensitiveRead ? ['SENSITIVE_OUTPUT', 'ALWAYS_ASK'] : [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });
  }

  if (lower === 'az') {
    const prefix = commandPrefix(words);
    if (prefix.includes('rest') || prefix.includes('run-command')) return null;
    const verb = prefix.find((word) => ['show', 'list', 'create', 'update', 'start', 'stop', 'restart', 'delete', 'purge'].includes(word));
    if (!verb) return null;
    if (verb === 'list' && !boundedInteger(option(words, '--top'), LIMITS.fanOut)) return null;
    const risk = ['show', 'list'].includes(verb) ? 'SAFE_READ_ONLY' : ['create'].includes(verb) && words.includes('tag') ? 'LOW_RISK_CHANGE' : ['delete', 'purge'].includes(verb) ? 'DESTRUCTIVE' : 'DISRUPTIVE_CHANGE';
    const sensitiveRead = risk === 'SAFE_READ_ONLY' && prefix.includes('keyvault') && prefix.includes('secret');
    return result('AZURE', risk, risk === 'SAFE_READ_ONLY' ? option(words, '--name') ?? verb : option(words, '--name'), option(words, '--subscription'), sensitiveRead ? ['SENSITIVE_OUTPUT', 'ALWAYS_ASK'] : [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });
  }

  if (lower === 'gcloud' || lower === 'gsutil') {
    const prefix = commandPrefix(words);
    if (prefix.some((word) => ['ssh', 'scp', 'add-metadata'].includes(word))) return null;
    const verbIndex = prefix.findIndex((word) => ['describe', 'list', 'get-iam-policy', 'add-labels', 'remove-labels', 'start', 'stop', 'reset', 'update', 'delete', 'rm'].includes(word));
    const verb = verbIndex >= 0 && verbIndex <= 3 ? prefix[verbIndex] : null;
    if (!verb) return null;
    if (verb === 'list' && !boundedInteger(option(words, '--limit'), LIMITS.fanOut)) return null;
    const risk = ['describe', 'list', 'get-iam-policy'].includes(verb) ? 'SAFE_READ_ONLY' : ['add-labels', 'remove-labels'].includes(verb) ? 'LOW_RISK_CHANGE' : ['delete', 'rm'].includes(verb) ? 'DESTRUCTIVE' : 'DISRUPTIVE_CHANGE';
    const candidateTarget = words[words.indexOf(verb) + 1];
    const target = candidateTarget && !candidateTarget.startsWith('-') ? candidateTarget : null;
    return result('GCP', risk, risk === 'SAFE_READ_ONLY' ? target ?? verb : target, option(words, '--project'), [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });
  }

  if (lower === 'pg_isready') return result('POSTGRES', 'SAFE_READ_ONLY', option(words, '-d') ?? 'status', option(words, '-h') ?? 'local');
  if (lower === 'psql') {
    const query = option(words, '-c', '--command');
    if (!query) return null;
    if (!boundedRelationalRead(query)) return null;
    const risk = queryRisk(query, [/^(SELECT|SHOW|EXPLAIN(?!\s+ANALYZE))/u], [/^SET\s+/u], [/^(VACUUM|ANALYZE|REINDEX)/u], [/^(DROP|TRUNCATE|DELETE|UPDATE|INSERT|ALTER|CREATE)/u]);
    return risk ? result('POSTGRES', risk, option(words, '-d', '--dbname'), option(words, '-h', '--host'), [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY', credentialConsumer: true }) : null;
  }
  if (lower === 'mysql' || lower === 'mysqladmin') {
    const query = option(words, '-e', '--execute') ?? words.at(-1);
    if (!boundedRelationalRead(query)) return null;
    const risk = queryRisk(query, [/^(SELECT|SHOW|EXPLAIN|STATUS|PING)/u], [/^SET\s+/u], [/^(FLUSH|OPTIMIZE|ANALYZE|REPAIR)/u], [/^(DROP|TRUNCATE|DELETE|UPDATE|INSERT|ALTER|CREATE|SHUTDOWN)/u]);
    return risk ? result('MYSQL', risk, option(words, '-D', '--database') ?? 'server', option(words, '-h', '--host'), [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY', credentialConsumer: true }) : null;
  }
  if (lower === 'mongosh') {
    const script = option(words, '--eval') ?? '';
    if (/;|\b(?:runProgram|load|require|process|child_process)\b/iu.test(script)) return null;
    const risk = queryRisk(script, [/\b(find|findOne|explain|serverStatus|replSetGetStatus)\b/iu], [], [/\b(reconfig|compact|repairDatabase)\b/iu], [/\b(insert|update|delete|drop|shutdown)\b/iu]);
    const uri = words.find((word) => /^mongodb(?:\+srv)?:\/\//iu.test(word));
    if (!risk || !uri) return null;
    const parsed = new URL(uri.replace(/^mongodb(?:\+srv)?:/iu, 'http:'));
    return result('MONGODB', risk, parsed.pathname.slice(1) || 'server', parsed.host, [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY', credentialConsumer: true });
  }
  if (lower === 'redis-cli') {
    const verb = commandWord(words, 1, ['-h', '--host', '-p', '--port', '-n', '--db', '-a', '--pass', '--user'])?.word;
    if (!verb) return null;
    if (!/^(PING|INFO|GET|MGET|SCAN|EXPIRE|PERSIST|KILL|REPLICAOF|DEL|FLUSHALL|FLUSHDB|SHUTDOWN|CONFIG)$/iu.test(verb)) return null;
    const upper = verb.toUpperCase();
    if (upper === 'SCAN') {
      const countIndex = words.findIndex((word) => word.toUpperCase() === 'COUNT');
      if (countIndex < 0 || !boundedInteger(words[countIndex + 1], LIMITS.outputRows)) return null;
    }
    const risk = ['PING', 'INFO', 'GET', 'MGET', 'SCAN'].includes(upper) ? 'SAFE_READ_ONLY' : ['EXPIRE', 'PERSIST'].includes(upper) ? 'LOW_RISK_CHANGE' : ['KILL', 'REPLICAOF'].includes(upper) ? 'DISRUPTIVE_CHANGE' : 'DESTRUCTIVE';
    return result('REDIS', risk, words[words.indexOf(verb) + 1] ?? 'server', option(words, '-h', '--host'), [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY', credentialConsumer: true });
  }

  if (lower === 'ping') {
    const count = option(words, '-c', '-n');
    if (!boundedInteger(count, LIMITS.fanOut) || /[$*?{}]/u.test(words.at(-1) ?? '')) return null;
    return result('NETWORK_READ', 'SAFE_READ_ONLY', words.at(-1), 'network', ['ACTIVE_PROBE', 'APPROVAL_REQUIRED']);
  }
  if (['traceroute', 'tracepath'].includes(lower)) {
    const hops = option(words, '-m', '--max-hops');
    if (hops !== null && !boundedInteger(hops, LIMITS.fanOut)) return null;
    if (/[$*?{}]/u.test(words.at(-1) ?? '')) return null;
    return result('NETWORK_READ', 'SAFE_READ_ONLY', words.at(-1), 'network', ['ACTIVE_PROBE', 'APPROVAL_REQUIRED']);
  }
  if (['dig', 'nslookup', 'host'].includes(lower)) {
    if (/[$*?{}]/u.test(words.at(-1) ?? '')) return null;
    return result('NETWORK_READ', 'SAFE_READ_ONLY', words.at(-1), 'network', ['ACTIVE_PROBE', 'APPROVAL_REQUIRED']);
  }
  if (lower === 'tcpdump' || lower === 'tshark') {
    const interfaceName = option(words, '-i', '--interface');
    const count = option(words, '-c', '--count');
    if (!interfaceName || !boundedInteger(count, LIMITS.outputRows)) return null;
    return result('PACKET_CAPTURE', 'SAFE_READ_ONLY', interfaceName, 'local', ['SENSITIVE_OUTPUT', 'RESOURCE_INTENSIVE', 'APPROVAL_REQUIRED']);
  }
  if (lower === 'curl' || lower === 'invoke-restmethod' || lower === 'invoke-webrequest') {
    if (words.some((word) => /^(?:-K|--config)(?:=|$)/u.test(word))) return null;
    const isCurl = lower === 'curl';
    const bodyOptions = isCurl
      ? ['-d', '--data', '--data-ascii', '--data-binary', '--data-raw', '--data-urlencode', '--json', '-F', '--form', '--form-string']
      : ['-Body'];
    const uploadOptions = isCurl ? ['-T', '--upload-file'] : ['-InFile'];
    const sinkOptions = isCurl
      ? ['-o', '--output', '-O', '--remote-name', '-D', '--dump-header', '-c', '--cookie-jar', '--etag-save', '--trace']
      : ['-OutFile'];
    const valueOptions = isCurl
      ? [...bodyOptions, ...uploadOptions, ...sinkOptions, '-X', '--request', '-H', '--header', '-u', '--user', '--token', '--oauth2-bearer', '--url', '--connect-timeout', '--max-time', '--retry', '--cert', '--key', '--cacert', '--resolve', '--proxy', '-x', '-b', '--cookie']
      : [...bodyOptions, ...uploadOptions, ...sinkOptions, '-Uri', '-Method', '-Headers', '-ContentType', '-Credential', '-Authentication', '-TimeoutSec', '-MaximumRedirection'];
    const flagOptions = isCurl
      ? ['-s', '--silent', '-S', '--show-error', '-f', '--fail', '--fail-with-body', '-I', '--head', '-i', '--include', '-L', '--location', '--compressed', '--http1.1', '--http2', '-k', '--insecure']
      : ['-SkipCertificateCheck', '-UseBasicParsing'];
    const knownOptions = [...valueOptions, ...flagOptions].map((name) => name.toLowerCase());
    for (const word of words.slice(1)) {
      if (!word.startsWith('-')) continue;
      const name = word.split('=', 1)[0].toLowerCase();
      if (!knownOptions.includes(name)) return null;
    }
    const lowerWords = words.map((word) => word.toLowerCase());
    const hasNamedOption = (names) => names.some((name) => {
      const candidate = name.toLowerCase();
      return lowerWords.some((word) => word === candidate || word.startsWith(`${candidate}=`));
    });
    const uploadIndex = lowerWords.findIndex((word) => [...bodyOptions, ...uploadOptions].some((name) => word === name.toLowerCase()));
    if (uploadIndex >= 0 && words[uploadIndex + 1]?.startsWith('@')) return null;
    const urls = words.filter((word) => /^https?:\/\//iu.test(word));
    if (urls.length !== 1 || words.includes('--next')) return null;
    const [url] = urls;
    let parsed; try { parsed = new URL(url); } catch { return null; }
    const hasBody = hasNamedOption(bodyOptions);
    const hasUpload = hasNamedOption(uploadOptions);
    const hasSink = hasNamedOption(sinkOptions);
    const method = (optionCaseInsensitive(words, '-X', '--request', '-Method') ?? (hasUpload ? 'PUT' : hasBody ? 'POST' : 'GET')).toUpperCase();
    const risk = ['GET', 'HEAD'].includes(method) ? 'SAFE_READ_ONLY' : method === 'DELETE' ? 'DESTRUCTIVE' : ['PUT', 'PATCH', 'POST'].includes(method) ? 'LOW_RISK_CHANGE' : null;
    const effectiveRisk = hasSink && risk === 'SAFE_READ_ONLY' ? 'LOW_RISK_CHANGE' : risk;
    return effectiveRisk ? result('HTTP', effectiveRisk, parsed.pathname || '/', parsed.origin, hasSink ? ['FILE_WRITE'] : [], { requiresExplicitBinding: effectiveRisk !== 'SAFE_READ_ONLY', credentialConsumer: true }) : null;
  }
  if (lower === 'ssh') return remoteFamily(words);
  if (lower === 'scp' || lower === 'sftp') {
    const target = words.at(-1);
    if (!target?.includes(':') || /[$*?{}]/u.test(target)) return null;
    return result('REMOTE', 'LOW_RISK_CHANGE', target, target.split(':')[0], ['REMOTE_TRANSFER'], { requiresExplicitBinding: true, credentialConsumer: true });
  }
  if (lower === 'git' || lower === 'gh') return gitCiFamily(words, lower);
  if (['restart-service', 'start-service', 'stop-service', 'set-service'].includes(lower)) {
    const risk = lower === 'set-service' ? 'LOW_RISK_CHANGE' : 'DISRUPTIVE_CHANGE';
    return result('WINDOWS_CONTROL', risk, option(words, '-Name') ?? words.at(-1), 'local', [], { requiresExplicitBinding: true });
  }
  return null;
}
