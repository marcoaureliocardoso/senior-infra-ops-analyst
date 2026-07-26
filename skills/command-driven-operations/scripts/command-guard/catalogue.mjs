import { lexBash } from './bash-lexer.mjs';
import { buildComposition } from './composition.mjs';

const POSIX_READ = new Set(['uname', 'uptime', 'free', 'df', 'ps', 'ss', 'ip', 'lsblk', 'mount', 'findmnt']);
const LOG_READ = new Set(['journalctl', 'dmesg']);
const FILTER = new Set(['grep', 'rg', 'head', 'tail', 'cut', 'sort', 'uniq', 'wc']);
const PS_FILTER = new Set(['where-object', 'select-object', 'sort-object', 'group-object', 'measure-object', 'format-table']);
const CONTAINERS = new Set(['docker', 'podman', 'nerdctl', 'ctr', 'crictl']);
const PS_READ = /^(Get-|Test-|Resolve-DnsName$)/iu;

export const POLICY_IDS = Object.freeze([
  'POSIX_HOST_READ', 'LOG_READ', 'SERVICE_CONTROL', 'KUBERNETES', 'CONTAINER',
  'AWS', 'AZURE', 'GCP', 'POSTGRES', 'MYSQL', 'MONGODB', 'REDIS',
  'NETWORK_READ', 'PACKET_CAPTURE', 'HTTP', 'REMOTE', 'PRIVILEGE', 'GIT_CI',
  'POWERSHELL_READ', 'WINDOWS_CONTROL', 'FILTER', 'DECRYPTOR',
]);
export const COMMAND_FAMILIES = Object.freeze(POLICY_IDS.filter((id) => id !== 'FILTER'));
export const FILTER_FAMILIES = Object.freeze(['FILTER']);

function executableIndex(argv) {
  return argv.findIndex((word) => !/^[A-Za-z_][A-Za-z0-9_]*=/u.test(word));
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

function cloudAction(argv, prefixes) {
  return argv.find((word) => prefixes.some((prefix) => word.toLowerCase().startsWith(prefix)))?.toLowerCase() ?? null;
}

function remoteFamily(argv) {
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
  if (LOG_READ.has(lower)) return result('LOG_READ', 'SAFE_READ_ONLY', option(words, '-u', '--unit') ?? 'local-log');
  if (FILTER.has(lower) || PS_FILTER.has(lower)) return result('FILTER', 'SAFE_READ_ONLY', null);
  if (lower === 'sed' && words.includes('-n')) return result('FILTER', 'SAFE_READ_ONLY', null);
  if (lower === 'awk' && !words.some((word) => /system|getline|\|/iu.test(word))) return result('FILTER', 'SAFE_READ_ONLY', null);
  if (lower === 'jq' && !words.some((word) => /^(?:--from-file|-f|--run-tests)$/u.test(word))) return result('FILTER', 'SAFE_READ_ONLY', null);
  if (PS_READ.test(exe) || lower === 'get-ciminstance') return result('POWERSHELL_READ', 'SAFE_READ_ONLY', 'local');
  if (lower === 'gpg' || lower === 'age') return result('DECRYPTOR', 'SAFE_READ_ONLY', words.at(-1), null, ['SENSITIVE_OUTPUT'], { sensitiveSource: true });

  if (lower === 'sudo') {
    const nestedStart = words.findIndex((word, index) => index > 0 && !word.startsWith('-'));
    const nested = nestedStart > 0 ? lookupFamily({ ...stage, argv: words.slice(nestedStart) }) : null;
    return nested ? result('PRIVILEGE', nested.risk, nested.target, nested.environment, [...nested.modifiers, 'PRIVILEGED'], { credentialConsumer: words.includes('-S') }) : null;
  }

  if (lower === 'systemctl' || lower === 'service') {
    const verb = words.find((word) => ['status', 'show', 'is-active', 'is-enabled', 'enable', 'disable', 'start', 'stop', 'restart', 'reload', 'daemon-reload', 'mask', 'unmask'].includes(word));
    if (!verb) return null;
    const risk = ['status', 'show', 'is-active', 'is-enabled'].includes(verb) ? 'SAFE_READ_ONLY' : ['enable', 'disable'].includes(verb) ? 'LOW_RISK_CHANGE' : 'DISRUPTIVE_CHANGE';
    return result('SERVICE_CONTROL', risk, words.at(-1), 'local', [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });
  }

  if (lower === 'kubectl' || (lower === 'k3s' && words[1] === 'kubectl')) {
    const verbs = ['get', 'describe', 'logs', 'events', 'version', 'cluster-info', 'label', 'annotate', 'apply', 'patch', 'scale', 'cordon', 'uncordon', 'delete', 'drain', 'replace'];
    const verb = words.find((word) => verbs.includes(word));
    if (!verb) return null;
    const forceReplace = verb === 'replace' && words.includes('--force');
    const risk = ['get', 'describe', 'logs', 'events', 'version', 'cluster-info'].includes(verb) ? 'SAFE_READ_ONLY' : ['label', 'annotate'].includes(verb) ? 'LOW_RISK_CHANGE' : ['delete', 'drain'].includes(verb) || forceReplace ? 'DESTRUCTIVE' : 'DISRUPTIVE_CHANGE';
    return result('KUBERNETES', risk, option(words, '--context'), option(words, '--namespace', '-n'), [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });
  }

  if (CONTAINERS.has(lower)) {
    const verb = words.find((word) => ['ps', 'inspect', 'logs', 'stats', 'images', 'info', 'pull', 'tag', 'rename', 'start', 'stop', 'restart', 'pause', 'unpause', 'rm', 'rmi', 'prune', 'reset'].includes(word));
    if (!verb || (verb === 'stats' && !words.includes('--no-stream'))) return null;
    const risk = ['ps', 'inspect', 'logs', 'stats', 'images', 'info'].includes(verb) ? 'SAFE_READ_ONLY' : ['pull', 'tag', 'rename'].includes(verb) ? 'LOW_RISK_CHANGE' : ['rm', 'rmi', 'prune', 'reset'].includes(verb) ? 'DESTRUCTIVE' : 'DISRUPTIVE_CHANGE';
    return result('CONTAINER', risk, risk === 'SAFE_READ_ONLY' ? 'local' : words.at(-1), option(words, '--context'), [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });
  }

  if (lower === 'aws') {
    const action = cloudAction(words, ['describe-', 'get-', 'list-', 'head-', 'create-tags', 'delete-tags', 'start-', 'stop-', 'reboot-', 'update-', 'delete-', 'terminate-', 'deregister-']);
    if (!action) return null;
    const risk = /^(describe|get|list|head)-/u.test(action) ? 'SAFE_READ_ONLY' : /^(create-tags|delete-tags)$/u.test(action) ? 'LOW_RISK_CHANGE' : /^(delete|terminate|deregister)-/u.test(action) ? 'DESTRUCTIVE' : 'DISRUPTIVE_CHANGE';
    const environment = [option(words, '--profile'), option(words, '--region')].filter(Boolean).join('@') || null;
    return result('AWS', risk, option(words, '--instance-ids', '--resource-arn') ?? action, environment, [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });
  }

  if (lower === 'az') {
    const verb = words.find((word) => ['show', 'list', 'create', 'update', 'start', 'stop', 'restart', 'delete', 'purge'].includes(word));
    if (!verb) return null;
    const risk = ['show', 'list'].includes(verb) ? 'SAFE_READ_ONLY' : ['create'].includes(verb) && words.includes('tag') ? 'LOW_RISK_CHANGE' : ['delete', 'purge'].includes(verb) ? 'DESTRUCTIVE' : 'DISRUPTIVE_CHANGE';
    return result('AZURE', risk, option(words, '--name') ?? words.at(-1), option(words, '--subscription'), [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });
  }

  if (lower === 'gcloud' || lower === 'gsutil') {
    const verb = words.find((word) => ['describe', 'list', 'get-iam-policy', 'add-labels', 'remove-labels', 'start', 'stop', 'reset', 'update', 'delete', 'rm'].includes(word));
    if (!verb) return null;
    const risk = ['describe', 'list', 'get-iam-policy'].includes(verb) ? 'SAFE_READ_ONLY' : ['add-labels', 'remove-labels'].includes(verb) ? 'LOW_RISK_CHANGE' : ['delete', 'rm'].includes(verb) ? 'DESTRUCTIVE' : 'DISRUPTIVE_CHANGE';
    return result('GCP', risk, words[words.indexOf(verb) + 1] ?? words.at(-1), option(words, '--project'), [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });
  }

  if (lower === 'pg_isready') return result('POSTGRES', 'SAFE_READ_ONLY', option(words, '-d') ?? 'status', option(words, '-h') ?? 'local');
  if (lower === 'psql') {
    const query = option(words, '-c', '--command');
    if (!query) return null;
    const risk = queryRisk(query, [/^(SELECT|SHOW|EXPLAIN(?!\s+ANALYZE))/u], [/^SET\s+/u], [/^(VACUUM|ANALYZE|REINDEX)/u], [/^(DROP|TRUNCATE|DELETE|UPDATE|INSERT|ALTER|CREATE)/u]);
    return risk ? result('POSTGRES', risk, option(words, '-d', '--dbname'), option(words, '-h', '--host'), [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY', credentialConsumer: true }) : null;
  }
  if (lower === 'mysql' || lower === 'mysqladmin') {
    const query = option(words, '-e', '--execute') ?? words.at(-1);
    const risk = queryRisk(query, [/^(SELECT|SHOW|EXPLAIN|STATUS|PING)/u], [/^SET\s+/u], [/^(FLUSH|OPTIMIZE|ANALYZE|REPAIR)/u], [/^(DROP|TRUNCATE|DELETE|UPDATE|INSERT|ALTER|CREATE|SHUTDOWN)/u]);
    return risk ? result('MYSQL', risk, option(words, '-D', '--database') ?? 'server', option(words, '-h', '--host'), [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY', credentialConsumer: true }) : null;
  }
  if (lower === 'mongosh') {
    const script = option(words, '--eval') ?? '';
    const risk = queryRisk(script, [/\b(find|findOne|explain|serverStatus|replSetGetStatus)\b/iu], [], [/\b(reconfig|compact|repairDatabase)\b/iu], [/\b(insert|update|delete|drop|shutdown)\b/iu]);
    const uri = words.find((word) => /^mongodb(?:\+srv)?:\/\//iu.test(word));
    if (!risk || !uri) return null;
    const parsed = new URL(uri.replace(/^mongodb(?:\+srv)?:/iu, 'http:'));
    return result('MONGODB', risk, parsed.pathname.slice(1) || 'server', parsed.host, [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY', credentialConsumer: true });
  }
  if (lower === 'redis-cli') {
    const verb = words.find((word) => /^(PING|INFO|GET|MGET|SCAN|EXPIRE|PERSIST|KILL|REPLICAOF|DEL|FLUSHALL|FLUSHDB|SHUTDOWN|CONFIG)$/iu.test(word));
    if (!verb) return null;
    const upper = verb.toUpperCase();
    const risk = ['PING', 'INFO', 'GET', 'MGET', 'SCAN'].includes(upper) ? 'SAFE_READ_ONLY' : ['EXPIRE', 'PERSIST'].includes(upper) ? 'LOW_RISK_CHANGE' : ['KILL', 'REPLICAOF'].includes(upper) ? 'DISRUPTIVE_CHANGE' : 'DESTRUCTIVE';
    return result('REDIS', risk, words[words.indexOf(verb) + 1] ?? 'server', option(words, '-h', '--host'), [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY', credentialConsumer: true });
  }

  if (['ping', 'traceroute', 'tracepath', 'dig', 'nslookup', 'host'].includes(lower)) return result('NETWORK_READ', 'SAFE_READ_ONLY', words.at(-1), 'network', ['ACTIVE_PROBE', 'APPROVAL_REQUIRED']);
  if (lower === 'tcpdump' || lower === 'tshark') {
    const interfaceName = option(words, '-i', '--interface');
    const count = option(words, '-c', '--count');
    if (!interfaceName || !count || !/^\d+$/u.test(count)) return null;
    return result('PACKET_CAPTURE', 'SAFE_READ_ONLY', interfaceName, 'local', ['SENSITIVE_OUTPUT', 'RESOURCE_INTENSIVE', 'APPROVAL_REQUIRED']);
  }
  if (lower === 'curl' || lower === 'invoke-restmethod' || lower === 'invoke-webrequest') {
    const url = words.find((word) => /^https?:\/\//iu.test(word));
    if (!url) return null;
    let parsed; try { parsed = new URL(url); } catch { return null; }
    const method = (option(words, '-X', '--request', '-Method') ?? 'GET').toUpperCase();
    const risk = ['GET', 'HEAD'].includes(method) ? 'SAFE_READ_ONLY' : method === 'DELETE' ? 'DESTRUCTIVE' : ['PUT', 'PATCH', 'POST'].includes(method) ? 'LOW_RISK_CHANGE' : null;
    return risk ? result('HTTP', risk, parsed.pathname || '/', parsed.origin, [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY', credentialConsumer: true }) : null;
  }
  if (lower === 'ssh') return remoteFamily(words);
  if (lower === 'scp' || lower === 'sftp') {
    const target = words.at(-1);
    if (!target?.includes(':') || /[$*?{}]/u.test(target)) return null;
    return result('REMOTE', 'LOW_RISK_CHANGE', target, target.split(':')[0], ['REMOTE_TRANSFER'], { requiresExplicitBinding: true, credentialConsumer: true });
  }
  if (lower === 'git' || lower === 'gh') {
    const joined = words.slice(1).join(' ').toLowerCase();
    const read = /^(?:status|log|diff|show|branch(?:\s+--list)?|repo view|pr (?:view|list|checks)|run (?:view|list)|workflow (?:view|list))/u.test(joined);
    const destructive = /(?:--force|-f\b|repo delete|branch delete|tag delete|clean -f|push .*--delete)/u.test(joined);
    const disruptive = /(?:workflow (?:run|rerun|cancel)|run (?:rerun|cancel)|deployment)/u.test(joined);
    const risk = read ? 'SAFE_READ_ONLY' : destructive ? 'DESTRUCTIVE' : disruptive ? 'DISRUPTIVE_CHANGE' : 'LOW_RISK_CHANGE';
    const remote = option(words, '--repo') ?? (lower === 'gh' ? words.find((word) => word.includes('/')) : 'local');
    return result('GIT_CI', risk, remote, remote === 'local' ? 'local' : remote, [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' && lower === 'gh', credentialConsumer: lower === 'gh' });
  }
  if (['restart-service', 'start-service', 'stop-service', 'set-service'].includes(lower)) {
    const risk = lower === 'set-service' ? 'LOW_RISK_CHANGE' : 'DISRUPTIVE_CHANGE';
    return result('WINDOWS_CONTROL', risk, option(words, '-Name') ?? words.at(-1), 'local', [], { requiresExplicitBinding: true });
  }
  return null;
}
