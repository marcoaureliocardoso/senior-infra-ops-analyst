import { lexBash } from './bash-lexer.mjs';
import { buildComposition } from './composition.mjs';
import { LIMITS } from './limits.mjs';
import { resolveOutputPath } from './output-path.mjs';

const POSIX_READ = new Set(['uname', 'uptime', 'free', 'df', 'lsblk', 'findmnt']);
const FILTER = new Set(['grep', 'rg', 'head', 'tail', 'cut', 'sort', 'uniq', 'wc']);
const PS_FILTER = new Set(['where-object', 'select-object', 'sort-object', 'group-object', 'measure-object', 'format-table']);
const CONTAINERS = new Set(['docker', 'podman', 'nerdctl', 'crictl']);
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
    'AWS_PROFILE', 'PGPASSWORD', 'MYSQL_PWD', 'SSHPASS',
    'GH_TOKEN', 'GITHUB_TOKEN', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
    'AWS_SESSION_TOKEN', 'OPS_CREDENTIAL_IDENTITY',
  ]);
  const seenAssignments = new Set();
  for (let index = 0; index < argv.length; index += 1) {
    const match = argv[index].match(/^([A-Za-z_][A-Za-z0-9_]*)=/u);
    if (!match) return index;
    if (!allowedAssignments.has(match[1]) || seenAssignments.has(match[1])) return -1;
    seenAssignments.add(match[1]);
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

function assignmentValue(argv, name) {
  const prefix = `${name}=`;
  const assignment = argv.find((word) => word.startsWith(prefix));
  return assignment?.slice(prefix.length) || null;
}

function optionOccurrences(argv, names) {
  return argv.filter((word) => names.some((name) => word === name ||
    word.startsWith(`${name}=`))).length;
}

function repeatedOptionGroup(argv, names) {
  return optionOccurrences(argv, names) > 1;
}

function parseRedisInvocation(argv) {
  const valueOptions = new Map([
    ['-h', 'host'], ['--host', 'host'], ['-p', 'port'], ['--port', 'port'],
    ['-n', 'database'], ['--db', 'database'], ['-a', 'password'], ['--pass', 'password'],
    ['--user', 'user'],
  ]);
  const values = new Map();
  const flags = new Set();
  for (let index = 1; index < argv.length; index += 1) {
    const word = argv[index];
    if (!word.startsWith('-')) return { commandIndex: index, values, flags };
    if (word === '--tls') {
      if (flags.has('tls')) return null;
      flags.add('tls');
      continue;
    }
    let optionName = word;
    let optionValue = null;
    const separator = word.indexOf('=');
    if (separator > 0 && word.startsWith('--')) {
      optionName = word.slice(0, separator);
      optionValue = word.slice(separator + 1);
    } else if (/^-a.+/u.test(word)) {
      optionName = '-a';
      optionValue = word.slice(2).replace(/^=/u, '');
    }
    const group = valueOptions.get(optionName);
    if (!group || values.has(group)) return null;
    if (optionValue === null) {
      optionValue = argv[index + 1];
      if (optionValue === undefined) return null;
      index += 1;
    }
    if (!optionValue) return null;
    values.set(group, optionValue);
  }
  return null;
}

function canonicalRedisEnvironment(invocation) {
  const host = invocation.values.get('host') ?? '127.0.0.1';
  const portText = invocation.values.get('port') ?? '6379';
  const databaseText = invocation.values.get('database') ?? '0';
  const user = invocation.values.get('user') ?? 'default';
  if ([host, user].some((value) => !value || /[$*?{}]/u.test(value))) return null;
  if (!/^\d{1,5}$/u.test(portText) || Number(portText) < 1 || Number(portText) > 65_535) return null;
  if (!/^\d{1,10}$/u.test(databaseText) || Number(databaseText) > 2_147_483_647) return null;
  const transport = invocation.flags.has('tls') ? 'tls' : 'tcp';
  return `redis+${transport}://${encodeURIComponent(user)}@${encodeURIComponent(host)}:${Number(portText)}/${Number(databaseText)}`;
}

function literalRedisOperand(value) {
  return typeof value === 'string' && value.length > 0 && !/(?:[$*?{}]|\[|\])/u.test(value);
}

function redisInteger(value, minimum, maximum) {
  if (!/^-?\d+$/u.test(value)) return null;
  const parsed = BigInt(value);
  return parsed >= minimum && parsed <= maximum ? parsed : null;
}

function parseRedisCommand(words, commandIndex) {
  const verb = words[commandIndex]?.toUpperCase();
  const args = words.slice(commandIndex + 1);
  const literalArgs = () => args.every(literalRedisOperand);
  if (verb === 'PING' && args.length === 0) return { risk: 'SAFE_READ_ONLY', target: 'server' };
  if (verb === 'INFO' && args.length <= 1 && literalArgs()) return { risk: 'SAFE_READ_ONLY', target: args[0] ?? 'server' };
  if (verb === 'GET' && args.length === 1 && literalArgs()) return { risk: 'SAFE_READ_ONLY', target: args[0] };
  if (verb === 'MGET' && args.length >= 1 && args.length <= LIMITS.outputRows && literalArgs()) return { risk: 'SAFE_READ_ONLY', target: args[0] };
  if (verb === 'SCAN' && args.length === 3 && args[1]?.toUpperCase() === 'COUNT') {
    const cursor = redisInteger(args[0], 0n, 9_223_372_036_854_775_807n);
    if (cursor !== null && boundedInteger(args[2], LIMITS.outputRows)) return { risk: 'SAFE_READ_ONLY', target: cursor.toString() };
    return null;
  }
  if (verb === 'EXPIRE' && args.length >= 2 && args.length <= 3 && literalRedisOperand(args[0])) {
    const ttl = redisInteger(args[1], -9_223_372_036_854_775_808n, 9_223_372_036_854_775_807n);
    const condition = args[2]?.toUpperCase();
    if (ttl === null || (condition && !['NX', 'XX', 'GT', 'LT'].includes(condition))) return null;
    return { risk: ttl <= 0n ? 'DESTRUCTIVE' : 'LOW_RISK_CHANGE', target: args[0] };
  }
  if (verb === 'PERSIST' && args.length === 1 && literalArgs()) return { risk: 'LOW_RISK_CHANGE', target: args[0] };
  if (verb === 'CLIENT' && args[0]?.toUpperCase() === 'KILL') {
    if (args.length === 2 && literalRedisOperand(args[1])) {
      const address = args[1].match(/^([^:\s]+):(\d+)$/u);
      if (address && boundedInteger(address[2], 65_535)) return { risk: 'DISRUPTIVE_CHANGE', target: args[1] };
    }
    if (args.length === 3 && args[1]?.toUpperCase() === 'ID') {
      const id = redisInteger(args[2], 1n, 9_223_372_036_854_775_807n);
      if (id !== null) return { risk: 'DISRUPTIVE_CHANGE', target: `id:${id}` };
    }
    return null;
  }
  if (verb === 'REPLICAOF') {
    if (args.length === 2 && args[0]?.toUpperCase() === 'NO' && args[1]?.toUpperCase() === 'ONE') {
      return { risk: 'DISRUPTIVE_CHANGE', target: 'no-one' };
    }
    if (args.length === 2 && literalRedisOperand(args[0]) && boundedInteger(args[1], 65_535)) {
      return { risk: 'DISRUPTIVE_CHANGE', target: `${args[0]}:${Number(args[1])}` };
    }
    return null;
  }
  if (verb === 'DEL' && args.length >= 1 && args.length <= LIMITS.fanOut && literalArgs()) return { risk: 'DESTRUCTIVE', target: args[0] };
  if (['FLUSHALL', 'FLUSHDB', 'SHUTDOWN'].includes(verb) && args.length === 0) return { risk: 'DESTRUCTIVE', target: 'server' };
  if (verb === 'CONFIG' && args.length === 3 && args[0]?.toUpperCase() === 'SET' && literalRedisOperand(args[1]) && literalRedisOperand(args[2])) {
    return { risk: 'DESTRUCTIVE', target: args[1] };
  }
  return null;
}

function enabledBooleanOption(argv, ...names) {
  for (const name of names) {
    const index = argv.indexOf(name);
    if (index >= 0) {
      const following = argv[index + 1]?.toLowerCase();
      return following !== 'false';
    }
    const inline = argv.find((word) => word.startsWith(`${name}=`));
    if (inline) return inline.slice(name.length + 1).toLowerCase() !== 'false';
  }
  return false;
}

const CURL_BODY_OPTIONS = new Set(['-d', '--data', '--data-ascii', '--data-binary', '--data-raw', '--data-urlencode', '--json', '-F', '--form', '--form-string']);
const CURL_UPLOAD_OPTIONS = new Set(['-T', '--upload-file']);
const CURL_SINK_VALUE_OPTIONS = new Set(['-o', '--output', '-D', '--dump-header', '-c', '--cookie-jar', '--etag-save', '--trace']);
const CURL_SINK_FLAGS = new Set(['-O', '--remote-name']);
const CURL_FLAGS = new Set(['-s', '--silent', '-S', '--show-error', '-f', '--fail', '--fail-with-body', '-I', '--head', '-i', '--include', '-L', '--location', '--compressed', '--http1.1', '--http2', ...CURL_SINK_FLAGS]);
const CURL_VALUE_GROUPS = new Map([
  ...[...CURL_BODY_OPTIONS].map((name) => [name, 'body']),
  ...[...CURL_UPLOAD_OPTIONS].map((name) => [name, 'upload']),
  ...[...CURL_SINK_VALUE_OPTIONS].map((name) => [name, 'sink']),
  ['-X', 'method'], ['--request', 'method'], ['-H', 'header'], ['--header', 'header'],
  ['-u', 'user'], ['--user', 'user'], ['--token', 'token'], ['--oauth2-bearer', 'oauth'],
  ['--url', 'url'], ['--connect-timeout', 'connect-timeout'], ['--max-time', 'max-time'],
  ['--retry', 'retry'], ['--cert', 'cert'], ['--key', 'key'], ['-b', 'cookie'], ['--cookie', 'cookie'],
]);
const CURL_REPEATABLE_GROUPS = new Set(['body', 'header']);
const CURL_SHORT_FLAGS = new Map([['s', '-s'], ['S', '-S'], ['f', '-f'], ['I', '-I'], ['i', '-i'], ['L', '-L'], ['O', '-O']]);

function addCurlFlag(flag, flags, groups) {
  if (flags.has(flag)) return false;
  if (CURL_SINK_FLAGS.has(flag)) {
    if (groups.has('sink')) return false;
    groups.add('sink');
  }
  flags.add(flag);
  return true;
}

function addCurlEntry(name, value, entries, groups) {
  const group = CURL_VALUE_GROUPS.get(name);
  if (value === '' || (!CURL_REPEATABLE_GROUPS.has(group) && groups.has(group))) return false;
  entries.push({ name, value, group });
  groups.add(group);
  return true;
}

function parseCurlInvocation(argv) {
  const entries = [];
  const flags = new Set();
  const groups = new Set();
  const positional = [];
  for (let index = 1; index < argv.length; index += 1) {
    const word = argv[index];
    if (!word.startsWith('-')) { positional.push(word); continue; }
    if (CURL_FLAGS.has(word)) {
      if (!addCurlFlag(word, flags, groups)) return null;
      continue;
    }
    if (word.startsWith('--')) {
      const separator = word.indexOf('=');
      const name = separator < 0 ? word : word.slice(0, separator);
      if (!CURL_VALUE_GROUPS.has(name)) return null;
      const value = separator < 0 ? argv[++index] : word.slice(separator + 1);
      if (value === undefined || !addCurlEntry(name, value, entries, groups)) return null;
      continue;
    }
    const shortName = word.slice(0, 2);
    if (CURL_VALUE_GROUPS.has(shortName)) {
      const value = word.length === 2 ? argv[++index] : word.slice(2).replace(/^=/u, '');
      if (value === undefined || !addCurlEntry(shortName, value, entries, groups)) return null;
      continue;
    }
    if (/^-[A-Za-z]+$/u.test(word)) {
      for (const character of word.slice(1)) {
        const flag = CURL_SHORT_FLAGS.get(character);
        if (!flag || !addCurlFlag(flag, flags, groups)) return null;
      }
      continue;
    }
    return null;
  }
  const configuredUrl = entries.find(({ group }) => group === 'url')?.value;
  if (positional.length + (configuredUrl ? 1 : 0) !== 1) return null;
  return { entries, flags, groups, url: configuredUrl ?? positional[0] };
}

const POWERSHELL_HTTP_VALUE_GROUPS = new Map([
  ['-uri', 'url'], ['-method', 'method'], ['-body', 'body'], ['-infile', 'upload'],
  ['-outfile', 'sink'], ['-headers', 'headers'], ['-credential', 'credential'],
  ['-authentication', 'authentication'], ['-contenttype', 'content-type'],
  ['-timeoutsec', 'timeout'], ['-maximumredirection', 'redirects'],
]);

function parsePowerShellHttpInvocation(argv) {
  const values = new Map();
  const flags = new Set();
  const positional = [];
  for (let index = 1; index < argv.length; index += 1) {
    const word = argv[index];
    if (!word.startsWith('-')) { positional.push(word); continue; }
    const separator = word.indexOf('=');
    const name = (separator < 0 ? word : word.slice(0, separator)).toLowerCase();
    if (name === '-usebasicparsing') {
      if (separator >= 0 || flags.has(name)) return null;
      flags.add(name);
      continue;
    }
    const group = POWERSHELL_HTTP_VALUE_GROUPS.get(name);
    if (!group || values.has(group)) return null;
    const value = separator < 0 ? argv[++index] : word.slice(separator + 1);
    if (!value) return null;
    values.set(group, value);
  }
  const configuredUrl = values.get('url');
  if (positional.length + (configuredUrl ? 1 : 0) !== 1) return null;
  return { values, flags, url: configuredUrl ?? positional[0] };
}

function curlReadsLocalRequestFile(entries) {
  const uploads = new Set(['-T', '--upload-file']);
  const directAt = new Set(['-d', '--data', '--data-ascii', '--data-binary', '--json']);
  for (const { name, value } of entries) {
    if (uploads.has(name)) return true;
    if (directAt.has(name) && value.startsWith('@')) return true;
    if (name === '--data-urlencode' && (/^@/u.test(value) || /^[^=]+@/u.test(value))) return true;
    if (['-F', '--form'].includes(name) && /(?:^|=)[@<]/u.test(value)) return true;
    if (['-H', '--header'].includes(name) && value.startsWith('@')) return true;
    if (['-b', '--cookie'].includes(name) && !value.includes('=')) return true;
  }
  return false;
}

function curlHeadersAreBound(entries) {
  for (const { group, value } of entries) {
    if (group !== 'header') continue;
    if (/[$`*?{}\[\]]/u.test(value)) return false;
    if (/^\s*:authority\s*:/iu.test(value)) return false;
    const match = /^\s*([^:\s]+)\s*:/u.exec(value);
    if (!match || match[1].toLowerCase() === 'host') return false;
  }
  return true;
}

function remoteNameOperand(parsedUrl) {
  if (/%(?:2f|5c)/iu.test(parsedUrl.pathname) || parsedUrl.pathname.endsWith('/')) return null;
  const encoded = parsedUrl.pathname.split('/').at(-1);
  let decoded;
  try { decoded = decodeURIComponent(encoded); } catch { return null; }
  if (!decoded || /[\\/\u0000-\u001f\u007f$`*?{}\[\]]/u.test(decoded)) return null;
  return decoded;
}

function classifyHttp(words, context) {
  const isCurl = words[0].toLowerCase() === 'curl';
  const invocation = isCurl ? parseCurlInvocation(words) : parsePowerShellHttpInvocation(words);
  if (!invocation || /[$*?{}]/u.test(invocation.url)) return null;
  let parsed;
  try { parsed = new URL(invocation.url); } catch { return null; }
  if (!['http:', 'https:'].includes(parsed.protocol)) return null;

  let method;
  let sinkOperand = null;
  let sinkOption = null;
  let hasBody;
  if (isCurl) {
    if (curlReadsLocalRequestFile(invocation.entries) || !curlHeadersAreBound(invocation.entries)) return null;
    hasBody = invocation.groups.has('body');
    method = (invocation.entries.find(({ group }) => group === 'method')?.value
      ?? (invocation.flags.has('-I') || invocation.flags.has('--head') ? 'HEAD' : hasBody ? 'POST' : 'GET')).toUpperCase();
    const sink = invocation.entries.find(({ group }) => group === 'sink');
    if (sink) { sinkOperand = sink.value; sinkOption = sink.name; }
    else if (invocation.flags.has('-O') || invocation.flags.has('--remote-name')) sinkOperand = remoteNameOperand(parsed);
  } else {
    hasBody = invocation.values.has('body');
    if (invocation.values.has('upload')) return null;
    method = (invocation.values.get('method') ?? (hasBody ? 'POST' : 'GET')).toUpperCase();
    sinkOperand = invocation.values.get('sink') ?? null;
  }

  const mutable = ['PUT', 'PATCH', 'POST'].includes(method);
  const risk = ['GET', 'HEAD'].includes(method) ? 'SAFE_READ_ONLY'
    : method === 'DELETE' ? 'DESTRUCTIVE' : mutable ? 'DISRUPTIVE_CHANGE' : null;
  if (!risk) return null;
  const stdoutSink = isCurl && (sinkOperand === '-' || (sinkOption === '--trace' && sinkOperand === '%'));
  const sensitiveHeaders = isCurl && (
    invocation.flags.has('-i') || invocation.flags.has('--include') ||
    invocation.flags.has('-I') || invocation.flags.has('--head') ||
    (stdoutSink && ['-D', '--dump-header', '-c', '--cookie-jar', '--etag-save', '--trace'].includes(sinkOption))
  );
  const hasSink = (sinkOperand !== null && !stdoutSink) || (isCurl && (invocation.flags.has('-O') || invocation.flags.has('--remote-name')));
  let resolvedSink = null;
  if (hasSink) {
    if (sinkOperand === null) return null;
    resolvedSink = resolveOutputPath(sinkOperand, context);
    if (resolvedSink === null) return null;
  }
  const effectiveRisk = hasSink && risk === 'SAFE_READ_ONLY' ? 'LOW_RISK_CHANGE' : risk;
  const remotePath = parsed.pathname;
  const target = hasSink ? `${method} ${remotePath} -> file:${resolvedSink}` : remotePath;
  const sinkModifiers = hasSink ? ['FILE_WRITE', 'ALWAYS_ASK'] : [];
  const sensitiveModifiers = sensitiveHeaders ? ['SENSITIVE_OUTPUT', 'ALWAYS_ASK'] : [];
  const externalModifiers = mutable ? ['EXTERNAL_SIDE_EFFECT'] : [];
  const credentialDisclosureModifiers = sinkOption === '--trace'
    ? [stdoutSink ? 'CREDENTIAL_OUTPUT' : 'CREDENTIAL_PERSISTENCE'] : [];
  const modifiers = [...new Set([
    ...sinkModifiers,
    ...sensitiveModifiers,
    ...externalModifiers,
    ...credentialDisclosureModifiers,
  ])];
  return result('HTTP', effectiveRisk, target, parsed.origin, modifiers, {
    requiresExplicitBinding: effectiveRisk !== 'SAFE_READ_ONLY', credentialConsumer: true,
    credentialTransports: ['AUTHORIZATION', 'COOKIE', 'FLAG', 'BASIC_AUTH', 'URI_USERINFO'],
  });
}

const POSTGRES_OPTIONS = new Map([
  ['-h', 'host'], ['--host', 'host'], ['-p', 'port'], ['--port', 'port'],
  ['-U', 'user'], ['--username', 'user'], ['-d', 'database'], ['--dbname', 'database'],
  ['-c', 'query'], ['--command', 'query'],
]);
const MYSQL_OPTIONS = new Map([
  ['-h', 'host'], ['--host', 'host'], ['-P', 'port'], ['--port', 'port'],
  ['-u', 'user'], ['--user', 'user'], ['-D', 'database'], ['--database', 'database'],
  ['-e', 'query'], ['--execute', 'query'], ['-p', 'password'], ['--password', 'password'],
]);
const POSTGRES_FORBIDDEN_ENVIRONMENT = new Set([
  'PGHOSTADDR', 'PGSERVICE', 'PGSERVICEFILE', 'PGPASSFILE', 'PGOPTIONS',
  'PGTARGETSESSIONATTRS', 'PGLOADBALANCEHOSTS', 'PGSSLMODE', 'PGREQUIRESSL',
  'PGSSLCOMPRESSION', 'PGSSLCERT', 'PGSSLKEY', 'PGSSLROOTCERT', 'PGSSLCRL',
  'PGSSLCRLDIR', 'PGSSLSNI', 'PGREQUIREPEER', 'PGSSLNEGOTIATION',
  'PGREQUIREAUTH', 'PGSSLCERTMODE', 'PGSSLMINPROTOCOLVERSION',
  'PGSSLMAXPROTOCOLVERSION', 'PGGSSENCMODE', 'PGGSSDELEGATION',
  'PGCHANNELBINDING', 'PGKRBSRVNAME', 'PGGSSLIB', 'PGMINPROTOCOLVERSION',
  'PGMAXPROTOCOLVERSION',
]);

function parseDatabaseOptions(words, options, { allowOperation = false } = {}) {
  const values = new Map();
  const operands = [];
  for (let index = 1; index < words.length; index += 1) {
    const word = words[index];
    if (!word.startsWith('-')) { operands.push(word); continue; }
    let name = word;
    let value = null;
    if (word.startsWith('--')) {
      const separator = word.indexOf('=');
      if (separator >= 0) {
        name = word.slice(0, separator);
        value = word.slice(separator + 1);
      }
    } else {
      const compactName = word.slice(0, 2);
      if (options.has(compactName) && word.length > 2) {
        name = compactName;
        value = word.slice(2).replace(/^=/u, '');
      }
    }
    const group = options.get(name);
    if (!group || values.has(group)) return null;
    if (value === null) value = words[++index];
    if (!value) return null;
    values.set(group, value);
  }
  if (allowOperation) {
    if (values.has('query') || operands.length !== 1) return null;
    values.set('query', operands[0]);
  } else if (operands.length !== 0 || !values.has('query')) return null;
  return {
    query: values.get('query'), host: values.get('host') ?? null,
    port: values.get('port') ?? null, user: values.get('user') ?? null,
    database: values.get('database') ?? null, password: values.get('password') ?? null,
  };
}

function validDatabaseSelector(value, kind) {
  if (value === null) return true;
  if (/[$*?{}\u0000-\u001f\u007f]/u.test(value)) return false;
  if (kind === 'database' && /[\/:@=]/u.test(value)) return false;
  return true;
}

function validateDatabaseInvocation(invocation) {
  if (!invocation || !['host', 'user', 'database'].every((key) => validDatabaseSelector(invocation[key], key))) return null;
  if (invocation.port !== null && !boundedInteger(invocation.port, 65_535)) return null;
  return invocation;
}

function parsePostgresInvocation(words, env = {}) {
  if (env && typeof env === 'object' && [...POSTGRES_FORBIDDEN_ENVIRONMENT].some((name) => Object.prototype.hasOwnProperty.call(env, name))) return null;
  const invocation = validateDatabaseInvocation(parseDatabaseOptions(words, POSTGRES_OPTIONS));
  if (!invocation || ['host', 'port', 'user', 'database'].some((key) => invocation[key] === null)) return null;
  if (/[\\/]/u.test(invocation.host)) return null;
  return invocation;
}

function parseMySqlInvocation(words, executable) {
  const invocation = validateDatabaseInvocation(parseDatabaseOptions(words, MYSQL_OPTIONS, { allowOperation: executable === 'mysqladmin' }));
  const required = executable === 'mysqladmin' ? ['host', 'port', 'user'] : ['host', 'port', 'user', 'database'];
  if (!invocation || required.some((key) => invocation[key] === null) || /[\\/]/u.test(invocation.host)) return null;
  if (['localhost', '.'].includes(invocation.host.toLowerCase())) return null;
  return invocation;
}

function canonicalDatabaseEnvironment(family, invocation) {
  const scheme = family === 'POSTGRES' ? 'postgresql' : 'mysql';
  const user = invocation.user;
  const host = invocation.host;
  const port = Number(invocation.port);
  const database = invocation.database ?? 'default-db';
  return `${scheme}://${encodeURIComponent(user)}@${encodeURIComponent(host)}:${port}/${encodeURIComponent(database)}`;
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

function hasClosedOptions(words, start, valueOptions = [], flagOptions = [], booleanOptions = []) {
  const values = new Set(valueOptions);
  const flags = new Set(flagOptions);
  const booleans = new Set(booleanOptions);
  for (let index = start; index < words.length; index += 1) {
    const word = words[index];
    if (!word.startsWith('-')) continue;
    if (values.has(word)) {
      if (words[index + 1] === undefined) return false;
      index += 1;
      continue;
    }
    const inlineValue = [...values].find((name) => word.startsWith(`${name}=`));
    if (inlineValue) {
      if (word.length === inlineValue.length + 1) return false;
      continue;
    }
    if (flags.has(word)) continue;
    if (booleans.has(word)) {
      if (/^(?:true|false)$/iu.test(words[index + 1] ?? '')) index += 1;
      continue;
    }
    const inlineBoolean = [...booleans].find((name) => word.startsWith(`${name}=`));
    if (inlineBoolean && /^(?:true|false)$/iu.test(word.slice(inlineBoolean.length + 1))) continue;
    return false;
  }
  return true;
}

function hasClosedKubectlOptions(words, start, verb) {
  const commonValues = [
    '--context', '--namespace', '-n', '--request-timeout', '-o', '--output',
  ];
  const commonFlags = ['--all', '--all-namespaces', '-A', '--show-labels', '--ignore-not-found'];
  const schemas = {
    get: {
      values: ['-l', '--selector', '--field-selector', '--chunk-size', '--sort-by'],
      booleans: ['--watch', '--watch-only', '-w'],
    },
    describe: { values: ['-l', '--selector'], flags: ['--show-events'], booleans: ['--watch', '--watch-only', '-w'] },
    logs: {
      values: ['--tail', '--since', '--since-time', '--limit-bytes', '--container', '-c', '--max-log-requests'],
      flags: ['--timestamps', '--prefix', '--previous', '-p', '--all-containers', '--ignore-errors'],
      booleans: ['--follow', '-f', '--watch', '--watch-only', '-w'],
    },
    events: { values: ['--for', '--types', '--chunk-size'], booleans: ['--watch', '--watch-only', '-w'] },
    version: { flags: ['--client', '--short'] },
    'cluster-info': {},
    label: { values: ['-f', '--filename', '--resource-version', '--dry-run'], flags: ['--overwrite', '--list', '--local'] },
    annotate: { values: ['-f', '--filename', '--resource-version', '--dry-run'], flags: ['--overwrite', '--list', '--local'] },
    apply: {
      values: ['-f', '--filename', '--dry-run', '--field-manager', '--validate', '--selector', '-l'],
      flags: ['--server-side', '--force-conflicts', '--prune', '--wait'],
    },
    patch: {
      values: ['-p', '--patch', '--patch-file', '--type', '--subresource', '--dry-run', '--field-manager'],
      flags: ['--local'],
    },
    scale: { values: ['--replicas', '--current-replicas', '--resource-version', '--timeout'], flags: ['--all'] },
    cordon: { values: ['--selector'], flags: ['--dry-run'] },
    uncordon: { values: ['--selector'], flags: ['--dry-run'] },
    delete: {
      values: ['-f', '--filename', '--grace-period', '--timeout', '--cascade', '--propagation-policy', '--dry-run'],
      flags: ['--force', '--now'], booleans: ['--wait'],
    },
    drain: {
      values: ['--grace-period', '--pod-selector', '--selector', '--timeout', '--skip-wait-for-delete-timeout'],
      flags: ['--ignore-daemonsets', '--delete-emptydir-data', '--disable-eviction', '--force', '--dry-run'],
    },
    replace: {
      values: ['-f', '--filename', '--dry-run', '--field-manager', '--validate'],
      flags: ['--force'],
    },
  };
  const schema = schemas[verb];
  return hasClosedOptions(
    words, start,
    [...commonValues, ...(schema.values ?? [])],
    [...commonFlags, ...(schema.flags ?? [])],
    schema.booleans ?? [],
  );
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
    const explicitPattern = words.some((word) => word === '-e' || word === '--regexp' || word.startsWith('-e=') || word.startsWith('--regexp='));
    return operands.length === (explicitPattern ? 0 : 1);
  }
  if (lower === 'head' || lower === 'tail') return positionalOperands(words, ['-n', '--lines', '-c', '--bytes']).length === 0;
  if (lower === 'cut') return positionalOperands(words, ['-b', '--bytes', '-c', '--characters', '-d', '--delimiter', '-f', '--fields']).length === 0;
  if (['sort', 'uniq', 'wc'].includes(lower)) return positionalOperands(words).length === 0;
  if (lower === 'sed') return words.includes('-n') && positionalOperands(words).length === 1;
  if (lower === 'awk') return positionalOperands(words).length === 1 && !words.some((word) => /system|getline|\|/iu.test(word));
  if (lower === 'jq') return positionalOperands(words, ['--arg', '--argjson']).length === 1 && !words.some((word) => /^(?:--from-file|-f|--run-tests)$/u.test(word));
  return true;
}

function literalGitBranch(value) {
  return typeof value === 'string' && value.length <= LIMITS.tokenChars
    && /^[A-Za-z0-9][A-Za-z0-9._/-]*$/u.test(value)
    && !value.includes('..') && !value.includes('//')
    && !value.endsWith('/') && !value.endsWith('.') && !value.endsWith('.lock');
}

function literalGitRepository(value) {
  return typeof value === 'string' && value.length <= LIMITS.tokenChars
    && value.length > 0 && !value.startsWith('-')
    && !/[$*?{}\[\]]/u.test(value);
}

function literalGitRefspec(value) {
  const normalized = value.startsWith('+') ? value.slice(1) : value;
  if (!normalized || normalized.split(':').length > 2) return false;
  const [source, destination] = normalized.split(':');
  if (destination === undefined) return literalGitBranch(source);
  if (!destination || !literalGitBranch(destination)) return false;
  return source === '' || literalGitBranch(source);
}

function parseGitPush(words) {
  const operands = [];
  const flags = new Set();
  let repository = null;
  let risk = 'LOW_RISK_CHANGE';
  const allowedFlags = new Map([
    ['-n', 'dryRun'], ['--dry-run', 'dryRun'],
    ['--porcelain', 'porcelain'], ['--thin', 'thin'], ['--no-thin', 'thin'],
    ['-u', 'upstream'], ['--set-upstream', 'upstream'],
    ['--follow-tags', 'followTags'], ['--atomic', 'atomic'],
    ['--verify', 'verify'], ['--progress', 'progress'],
    ['-4', 'addressFamily'], ['--ipv4', 'addressFamily'],
    ['-6', 'addressFamily'], ['--ipv6', 'addressFamily'],
  ]);
  const destructiveFlags = new Map([
    ['-f', 'force'], ['--force', 'force'], ['--force-with-lease', 'force'],
    ['--force-if-includes', 'forceIncludes'], ['-d', 'delete'], ['--delete', 'delete'],
    ['--mirror', 'mirror'], ['--prune', 'prune'],
  ]);

  for (let index = 2; index < words.length; index += 1) {
    const word = words[index];
    if (word === '--repo' || word.startsWith('--repo=')) {
      if (repository !== null) return null;
      repository = word === '--repo' ? words[++index] : word.slice('--repo='.length);
      if (!literalGitRepository(repository)) return null;
      continue;
    }
    if (/^(?:--exec|--receive-pack|--push-option)(?:=|$)|^-o(?:.|$)|^--no-verify$/u.test(word)) return null;
    if (word.startsWith('--force-with-lease=')) {
      if (flags.has('force') || !literalOperand(word.slice('--force-with-lease='.length))) return null;
      flags.add('force');
      risk = 'DESTRUCTIVE';
      continue;
    }
    const allowedGroup = allowedFlags.get(word);
    if (allowedGroup) {
      if (flags.has(allowedGroup)) return null;
      flags.add(allowedGroup);
      continue;
    }
    const destructiveGroup = destructiveFlags.get(word);
    if (destructiveGroup) {
      if (flags.has(destructiveGroup)) return null;
      flags.add(destructiveGroup);
      risk = 'DESTRUCTIVE';
      continue;
    }
    if (word.startsWith('-')) return null;
    if (operands.length > LIMITS.fanOut || !literalGitRepository(word)) return null;
    operands.push(word);
  }

  if (repository === null) repository = operands.shift() ?? null;
  if (!literalGitRepository(repository)) return null;
  const mirror = flags.has('mirror');
  if ((operands.length === 0 && !mirror) || operands.length > LIMITS.fanOut) return null;
  if (!operands.every(literalGitRefspec)) return null;
  if (operands.some((refspec) => refspec.startsWith('+') || refspec.startsWith(':'))) risk = 'DESTRUCTIVE';
  return { risk, target: mirror ? 'refs:*' : operands.join(','), environment: repository };
}

function parseGitBranch(words) {
  const args = words.slice(2);
  if (args.length === 0) return { risk: 'SAFE_READ_ONLY', target: 'local' };
  if (args[0] === '--list') {
    if (args.length > 2 || (args[1] !== undefined && !literalGitBranch(args[1]))) return null;
    return { risk: 'SAFE_READ_ONLY', target: args[1] ?? 'local' };
  }
  if (['-m', '-M', '--move'].includes(args[0])) {
    if (args.length !== 3 || !args.slice(1).every(literalGitBranch)) return null;
    return { risk: 'LOW_RISK_CHANGE', target: `${args[1]}->${args[2]}` };
  }
  if (['-d', '-D'].includes(args[0])) {
    const targets = args.slice(1);
    if (targets.length < 1 || targets.length > LIMITS.fanOut || !targets.every(literalGitBranch)) return null;
    return { risk: 'DESTRUCTIVE', target: targets.join(',') };
  }
  if (['--delete', '--force'].includes(args[0])) {
    const flags = new Set();
    let index = 0;
    while (['--delete', '--force'].includes(args[index])) {
      if (flags.has(args[index])) return null;
      flags.add(args[index]);
      index += 1;
    }
    const targets = args.slice(index);
    if (!flags.has('--delete') || targets.length < 1 || targets.length > LIMITS.fanOut || !targets.every(literalGitBranch)) return null;
    return { risk: 'DESTRUCTIVE', target: targets.join(',') };
  }
  if (args.length <= 2 && args.every(literalGitBranch)) {
    return { risk: 'LOW_RISK_CHANGE', target: args[0] };
  }
  return null;
}

function literalOperand(value) {
  return typeof value === 'string' && value.length > 0 && !/[$*?{}\[\]]/u.test(value);
}

function parseGitRead(words, context) {
  const verb = words[1];
  const args = words.slice(2);
  if (verb === 'status') {
    const flags = new Set(['--short', '-s', '--branch', '-b', '--porcelain', '--untracked-files=no']);
    return args.every((word) => flags.has(word))
      ? { risk: 'SAFE_READ_ONLY', target: 'local', modifiers: [] }
      : null;
  }

  const booleanOptions = new Set([
    '--stat', '--oneline', '--patch', '-p', '--name-only', '--name-status',
    '--summary', '--no-renames', '--color=never', '--no-color', '--cached', '--staged',
  ]);
  const valueOptions = new Set(['-n', '--max-count', '--since', '--until', '--format', '--pretty']);
  const operands = [];
  let sink = null;
  for (let index = 0; index < args.length; index += 1) {
    const word = args[index];
    if (word === '--ext-diff' || word === '--textconv') return null;
    if (verb === 'diff' && (word === '--output' || word.startsWith('--output='))) {
      if (sink !== null) return null;
      sink = word === '--output' ? args[++index] : word.slice('--output='.length);
      if (!sink) return null;
      continue;
    }
    if (booleanOptions.has(word)) continue;
    if (valueOptions.has(word)) {
      const value = args[++index];
      if (!literalOperand(value)) return null;
      continue;
    }
    if ([...valueOptions].some((name) => word.startsWith(`${name}=`))) {
      if (!literalOperand(word.slice(word.indexOf('=') + 1))) return null;
      continue;
    }
    if (word.startsWith('-')) return null;
    if (!literalOperand(word) || operands.length >= LIMITS.fanOut) return null;
    operands.push(word);
  }
  if (sink !== null) {
    const resolved = resolveOutputPath(sink, context);
    if (resolved === null) return null;
    return { risk: 'LOW_RISK_CHANGE', target: `${verb} -> file:${resolved}`, modifiers: ['FILE_WRITE', 'ALWAYS_ASK'] };
  }
  return { risk: 'SAFE_READ_ONLY', target: operands[0] ?? 'local', modifiers: [] };
}

function parseGhRead(words) {
  const key = `${words[1] ?? ''} ${words[2] ?? ''}`.toLowerCase();
  const schemas = new Map([
    ['repo view', { minOperands: 0, maxOperands: 1, values: ['--repo', '--json', '--jq', '--template'], flags: [] }],
    ['pr view', { minOperands: 0, maxOperands: 1, values: ['--repo', '--json', '--jq', '--template'], flags: ['--comments'] }],
    ['pr list', { minOperands: 0, maxOperands: 0, values: ['--repo', '--limit', '--state', '--author', '--assignee', '--search', '--head', '--base', '--label', '--json', '--jq', '--template', '--app'], flags: ['--draft'] }],
    ['pr checks', { minOperands: 0, maxOperands: 1, values: ['--repo', '--json', '--jq', '--template'], flags: ['--required'] }],
    ['run view', { minOperands: 1, maxOperands: 1, values: ['--repo', '--job', '--attempt', '--json', '--jq', '--template'], flags: ['--exit-status', '--log', '--log-failed'] }],
    ['run list', { minOperands: 0, maxOperands: 0, values: ['--repo', '--limit', '--workflow', '--branch', '--user', '--event', '--status', '--commit', '--created', '--json', '--jq', '--template'], flags: ['--all'] }],
    ['workflow view', { minOperands: 1, maxOperands: 1, values: ['--repo', '--ref'], flags: ['--yaml'] }],
    ['workflow list', { minOperands: 0, maxOperands: 0, values: ['--repo', '--limit'], flags: ['--all'] }],
  ]);
  const schema = schemas.get(key);
  if (!schema) return null;
  const valueNames = new Set(schema.values);
  const flagNames = new Set(schema.flags);
  const values = new Map();
  const flags = new Set();
  const operands = [];

  for (let index = 3; index < words.length; index += 1) {
    const word = words[index];
    if (word === '--watch' || word.startsWith('--watch=')) return null;
    let name = word;
    let value = null;
    const separator = word.indexOf('=');
    if (separator > 0 && word.startsWith('--')) {
      name = word.slice(0, separator);
      value = word.slice(separator + 1);
    }
    if (valueNames.has(name)) {
      if (values.has(name)) return null;
      if (value === null) value = words[++index];
      if (!literalOperand(value)) return null;
      values.set(name, value);
      continue;
    }
    if (flagNames.has(word)) {
      const group = word === '--log' || word === '--log-failed' ? 'log' : word;
      if (flags.has(group)) return null;
      flags.add(group);
      continue;
    }
    if (word.startsWith('-') || !literalOperand(word) || operands.length >= schema.maxOperands) return null;
    operands.push(word);
  }

  if (operands.length < schema.minOperands) return null;
  const limit = values.get('--limit');
  if (limit !== undefined && !boundedInteger(limit, LIMITS.outputRows)) return null;
  const selectedRepo = values.get('--repo');
  if (key === 'repo view' && selectedRepo && operands.length > 0) return null;
  const remote = selectedRepo ?? (key === 'repo view' ? operands[0] : null) ?? 'local';
  const broadLogs = key === 'run view' && flags.has('log');
  return {
    target: operands[0] ?? remote,
    environment: remote,
    modifiers: broadLogs ? ['SENSITIVE_OUTPUT', 'RESOURCE_INTENSIVE', 'ALWAYS_ASK'] : [],
  };
}

function parseJournalctl(words) {
  const valueOptions = new Map([
    ['-n', 'lines'], ['--lines', 'lines'], ['-u', 'unit'], ['--unit', 'unit'],
    ['--since', 'since'], ['--until', 'until'], ['-p', 'priority'], ['--priority', 'priority'],
    ['-o', 'output'], ['--output', 'output'], ['-t', 'identifier'], ['--identifier', 'identifier'],
    ['--vacuum-size', 'vacuumSize'], ['--vacuum-time', 'vacuumTime'], ['--vacuum-files', 'vacuumFiles'],
  ]);
  const flags = new Map([
    ['--no-pager', 'noPager'], ['--utc', 'utc'], ['--reverse', 'reverse'], ['-r', 'reverse'],
    ['--quiet', 'quiet'], ['-q', 'quiet'], ['--no-hostname', 'noHostname'],
    ['--catalog', 'catalog'], ['-x', 'catalog'],
    ['--rotate', 'rotate'], ['--flush', 'flush'], ['--sync', 'sync'], ['--relinquish-var', 'relinquish'],
  ]);
  const values = new Map();
  const seenFlags = new Set();
  let destructive = false;

  for (let index = 1; index < words.length; index += 1) {
    const word = words[index];
    if (word === '--follow' || word === '-f' || word.startsWith('--follow=')) return null;
    let name = word;
    let value = null;
    const separator = word.indexOf('=');
    if (separator > 0 && word.startsWith('--')) {
      name = word.slice(0, separator);
      value = word.slice(separator + 1);
    }
    const group = valueOptions.get(name);
    if (group) {
      if (values.has(group)) return null;
      if (value === null) value = words[++index];
      if (!literalOperand(value)) return null;
      values.set(group, value);
      if (group.startsWith('vacuum')) destructive = true;
      continue;
    }
    const flagGroup = flags.get(word);
    if (!flagGroup || seenFlags.has(flagGroup)) return null;
    seenFlags.add(flagGroup);
    if (['rotate', 'flush', 'sync', 'relinquish'].includes(flagGroup)) destructive = true;
  }

  if (!boundedInteger(values.get('lines'), LIMITS.outputRows)) return null;
  return {
    risk: destructive ? 'DESTRUCTIVE' : 'SAFE_READ_ONLY',
    target: values.get('unit') ?? 'local-log',
  };
}

function parseContainerLogs(words, commandIndex) {
  const prefix = words.slice(1, commandIndex);
  if (prefix.length > 0) {
    if (prefix.length !== 2 || prefix[0] !== '--context' || !literalOperand(prefix[1])) return null;
  }
  const values = new Map();
  const flags = new Set();
  const operands = [];
  const valueOptions = new Map([
    ['--tail', 'tail'], ['--since', 'since'], ['--until', 'until'],
  ]);
  const flagOptions = new Map([
    ['--timestamps', 'timestamps'], ['-t', 'timestamps'], ['--details', 'details'],
  ]);

  for (let index = commandIndex + 1; index < words.length; index += 1) {
    const word = words[index];
    if (word === '--follow' || word === '-f' || word.startsWith('--follow=')) return null;
    let name = word;
    let value = null;
    const separator = word.indexOf('=');
    if (separator > 0 && word.startsWith('--')) {
      name = word.slice(0, separator);
      value = word.slice(separator + 1);
    }
    const group = valueOptions.get(name);
    if (group) {
      if (values.has(group)) return null;
      if (value === null) value = words[++index];
      if (!literalOperand(value)) return null;
      values.set(group, value);
      continue;
    }
    const flagGroup = flagOptions.get(word);
    if (flagGroup) {
      if (flags.has(flagGroup)) return null;
      flags.add(flagGroup);
      continue;
    }
    if (word.startsWith('-') || !literalOperand(word) || operands.length >= 1) return null;
    operands.push(word);
  }

  if (!boundedInteger(values.get('tail'), LIMITS.outputRows) || operands.length !== 1) return null;
  return { target: operands[0] };
}

function gitCiFamily(words, lower, context = {}) {
  const joined = words.slice(1).join(' ').toLowerCase();
  const remote = option(words, '--repo') ?? (lower === 'gh' ? words.find((word) => word.includes('/')) : 'local');
  if (lower === 'git') {
    if (words[1] === 'branch') {
      const branch = parseGitBranch(words);
      return branch ? result('GIT_CI', branch.risk, branch.target, 'local') : null;
    }
    if (['status', 'log', 'diff', 'show'].includes(words[1])) {
      const read = parseGitRead(words, context);
      return read ? result('GIT_CI', read.risk, read.target, 'local', read.modifiers) : null;
    }
    if (words[1] === 'push') {
      const push = parseGitPush(words);
      return push ? result('GIT_CI', push.risk, push.target, push.environment) : null;
    }
    if (/^(?:reset\s+--hard|clean\s+.*-[A-Za-z]*f|tag\s+(?:-d|--delete)\b)/u.test(joined)) {
      return result('GIT_CI', 'DESTRUCTIVE', words.at(-1), 'local');
    }
    if (/^(?:add|commit|tag)(?:\s|$)/u.test(joined)) {
      return result('GIT_CI', 'LOW_RISK_CHANGE', words.at(-1), 'local');
    }
    return null;
  }
  const ghRead = parseGhRead(words);
  if (ghRead) {
    return result('GIT_CI', 'SAFE_READ_ONLY', ghRead.target, ghRead.environment, ghRead.modifiers, { credentialConsumer: true, credentialTransports: ['VARIABLE'], credentialSelectors: ['GH_TOKEN', 'GITHUB_TOKEN'] });
  }
  if (/^(?:repo delete|release delete|pr merge)(?:\s|$)/u.test(joined)) {
    return result('GIT_CI', 'DESTRUCTIVE', remote, remote, [], { requiresExplicitBinding: true, credentialConsumer: true, credentialTransports: ['VARIABLE'], credentialSelectors: ['GH_TOKEN', 'GITHUB_TOKEN'] });
  }
  if (/^(?:workflow (?:run|rerun|cancel)|run (?:rerun|cancel)|deployment)(?:\s|$)/u.test(joined)) {
    return result('GIT_CI', 'DISRUPTIVE_CHANGE', remote, remote, ['EXTERNAL_SIDE_EFFECT'], { requiresExplicitBinding: true, credentialConsumer: true, credentialTransports: ['VARIABLE'], credentialSelectors: ['GH_TOKEN', 'GITHUB_TOKEN'] });
  }
  if (/^(?:pr (?:create|edit|comment|review|close|reopen)|issue (?:create|edit|comment|close|reopen)|release (?:create|edit|upload)|repo (?:clone|fork))\b/u.test(joined)) {
    return result('GIT_CI', 'LOW_RISK_CHANGE', remote, remote, ['EXTERNAL_SIDE_EFFECT'], { requiresExplicitBinding: true, credentialConsumer: true, credentialTransports: ['VARIABLE'], credentialSelectors: ['GH_TOKEN', 'GITHUB_TOKEN'] });
  }
  return null;
}

function validSshOption(value) {
  const separator = value.indexOf('=');
  if (separator <= 0) return false;
  const name = value.slice(0, separator).toLowerCase();
  const optionValue = value.slice(separator + 1);
  if (!optionValue || /[$*?{}]/u.test(optionValue)) return false;
  if (name === 'batchmode' || name === 'identitiesonly') return optionValue.toLowerCase() === 'yes';
  if (name === 'stricthostkeychecking') return /^(?:yes|accept-new)$/iu.test(optionValue);
  if (name === 'connecttimeout' || name === 'serveraliveinterval') return boundedInteger(optionValue, 300, 0);
  if (name === 'connectionattempts' || name === 'serveralivecountmax') return boundedInteger(optionValue, 10);
  if (name === 'port') return boundedInteger(optionValue, 65535);
  if (name === 'addressfamily') return /^(?:any|inet|inet6)$/iu.test(optionValue);
  if (name === 'loglevel') return /^(?:quiet|fatal|error|info|verbose|debug[123]?)$/iu.test(optionValue);
  if (name === 'user') return /^[A-Za-z0-9._-]+$/u.test(optionValue);
  if (name === 'proxyjump') return /^[A-Za-z0-9._@,:\[\]-]+$/u.test(optionValue);
  return false;
}

function parseSshInvocation(argv) {
  const flags = new Set(['-4', '-6', '-q', '-v', '-vv', '-vvv', '-T']);
  const values = new Set(['-p', '-l', '-i', '-J']);
  let index = 1;
  while (index < argv.length && argv[index].startsWith('-')) {
    const word = argv[index];
    if (flags.has(word)) { index += 1; continue; }
    if (word === '-o') {
      if (!validSshOption(argv[index + 1] ?? '')) return null;
      index += 2;
      continue;
    }
    if (word.startsWith('-o')) {
      const value = word.slice(2).replace(/^=/u, '');
      if (!validSshOption(value)) return null;
      index += 1;
      continue;
    }
    if (values.has(word)) {
      const value = argv[index + 1];
      if (!value || /[$*?{}]/u.test(value)) return null;
      if (word === '-p' && !boundedInteger(value, 65535)) return null;
      index += 2;
      continue;
    }
    const compact = [...values].find((name) => word.startsWith(name) && word.length > name.length);
    if (!compact) return null;
    const value = word.slice(compact.length);
    if (/[$*?{}]/u.test(value) || (compact === '-p' && !boundedInteger(value, 65535))) return null;
    index += 1;
  }
  if (index + 2 !== argv.length) return null;
  const host = argv[index];
  const payload = argv[index + 1];
  if (!host || !payload || /[$*?{}]/u.test(host)) return null;
  return { host, payload };
}

function remoteFamily(argv) {
  const invocation = parseSshInvocation(argv);
  if (!invocation) return null;
  const { host, payload } = invocation;
  let composition;
  try { composition = buildComposition(lexBash(payload)); } catch { return null; }
  if (composition.stages.length !== 1 || composition.operators.length !== 0 || composition.redirects.length !== 0) return null;
  const nested = lookupFamily(composition.stages[0], { cwd: null, env: {}, dialect: 'bash', remote: true });
  if (!nested || ['REMOTE', 'FILTER', 'DECRYPTOR'].includes(nested.policyId)) return null;
  return result('REMOTE', nested.risk, host, host, [...nested.modifiers, 'REMOTE_EXECUTION'], { credentialConsumer: true });
}

function parseRemoteTransfer(words, client) {
  const flags = client === 'scp'
    ? new Set(['-B', '-C', '-p', '-q', '-r', '-v'])
    : new Set(['-C', '-q', '-v']);
  const values = new Set(['-P', '-i', '-J', '-l']);
  const selectors = { user: null, port: null, proxyJump: null, limitKbps: null, identityFile: null, addressFamily: null };
  const seenSelectors = new Set();
  const setSelector = (name, value) => {
    if (seenSelectors.has(name)) return false;
    seenSelectors.add(name);
    selectors[name] = value;
    return true;
  };
  const consumeSshOption = (optionValue) => {
    if (!validSshOption(optionValue)) return false;
    const separator = optionValue.indexOf('=');
    const name = optionValue.slice(0, separator).toLowerCase();
    const value = optionValue.slice(separator + 1);
    const selectorName = { user: 'user', port: 'port', proxyjump: 'proxyJump', addressfamily: 'addressFamily' }[name] ?? `option:${name}`;
    return setSelector(selectorName, name === 'addressfamily' ? value.toLowerCase() : value);
  };
  const consumeValue = (name, value) => {
    if (!literalOperand(value)) return false;
    if (name === '-P') return boundedInteger(value, 65_535) && setSelector('port', String(Number(value)));
    if (name === '-J') return validSshOption(`ProxyJump=${value}`) && setSelector('proxyJump', value);
    if (name === '-l') return boundedInteger(value, 1_000_000_000) && setSelector('limitKbps', String(Number(value)));
    return setSelector('identityFile', value);
  };
  const operands = [];
  for (let index = 1; index < words.length; index += 1) {
    const word = words[index];
    if (flags.has(word)) continue;
    if (word === '-4' || word === '-6') {
      if (!setSelector('addressFamily', word === '-4' ? 'inet' : 'inet6')) return null;
      continue;
    }
    if (word === '-o') {
      if (!consumeSshOption(words[++index] ?? '')) return null;
      continue;
    }
    if (word.startsWith('-o')) {
      if (!consumeSshOption(word.slice(2).replace(/^=/u, ''))) return null;
      continue;
    }
    if (values.has(word)) {
      const value = words[++index];
      if (!consumeValue(word, value)) return null;
      continue;
    }
    const compact = [...values].find((name) => word.startsWith(name) && word.length > name.length);
    if (compact) {
      const value = word.slice(compact.length);
      if (!consumeValue(compact, value)) return null;
      continue;
    }
    if (word.startsWith('-') || !literalOperand(word)) return null;
    operands.push(word);
  }
  if (client === 'scp') {
    if (operands.length !== 2 || operands[0].includes(':') || !operands[1].includes(':')) return null;
  } else if (operands.length !== 1 || !(operands[0].includes(':') || /^sftp:\/\//iu.test(operands[0]))) return null;
  const target = operands.at(-1);
  let operandUser = null;
  let operandPort = null;
  let host = null;
  if (/^sftp:\/\//iu.test(target)) {
    try {
      const parsed = new URL(target);
      if (parsed.protocol !== 'sftp:' || parsed.password || !/^[A-Za-z0-9.-]+$/u.test(parsed.hostname) || (parsed.port && !boundedInteger(parsed.port, 65_535))) return null;
      operandUser = parsed.username ? decodeURIComponent(parsed.username) : null;
      operandPort = parsed.port || null;
      host = parsed.hostname;
    } catch { return null; }
  } else {
    const endpoint = target.slice(0, target.indexOf(':'));
    const match = endpoint.match(/^(?:([A-Za-z0-9._-]+)@)?([A-Za-z0-9.-]+)$/u);
    if (!match) return null;
    [, operandUser = null, host] = match;
  }
  if (operandUser && selectors.user !== null || operandPort && selectors.port !== null) return null;
  const user = selectors.user ?? operandUser;
  const port = selectors.port ?? operandPort ?? '22';
  if (!user || !/^[A-Za-z0-9._-]+$/u.test(user) || !host || !boundedInteger(port, 65_535)) return null;
  const query = [];
  if (selectors.addressFamily !== null) query.push(`addressFamily=${encodeURIComponent(selectors.addressFamily)}`);
  if (selectors.proxyJump !== null) query.push(`via=${encodeURIComponent(selectors.proxyJump)}`);
  if (selectors.limitKbps !== null) query.push(`limitKbps=${encodeURIComponent(selectors.limitKbps)}`);
  if (selectors.identityFile !== null) query.push(`identityFile=${encodeURIComponent(selectors.identityFile)}`);
  const environment = `ssh://${encodeURIComponent(user)}@${host.toLowerCase()}:${Number(port)}${query.length ? `;${query.join(';')}` : ''}`;
  return { target, environment };
}

function parseMongoInvocation(words) {
  let uri = null;
  let script = null;
  for (let index = 1; index < words.length; index += 1) {
    const word = words[index];
    if (/^mongodb(?:\+srv)?:\/\//iu.test(word)) {
      if (uri !== null) return null;
      uri = word;
      continue;
    }
    if (word === '--eval' || word.startsWith('--eval=')) {
      if (script !== null) return null;
      script = word === '--eval' ? words[++index] : word.slice('--eval='.length);
      if (!script) return null;
      continue;
    }
    return null;
  }
  return uri && script ? { uri, script } : null;
}

function parsePacketCapture(words, context) {
  const client = words[0].toLowerCase();
  const valueOptions = new Map([
    ['-i', 'interface'], ['--interface', 'interface'],
    ['-c', 'count'], ['--count', 'count'],
    ['-s', 'snapshotLength'], ['--snapshot-length', 'snapshotLength'],
    ['-w', 'sink'],
  ]);
  const flags = client === 'tcpdump'
    ? new Set(['-n', '-nn', '-q', '-v', '-vv', '-vvv'])
    : new Set(['-n', '-q']);
  const values = new Map();
  const filter = [];
  for (let index = 1; index < words.length; index += 1) {
    const word = words[index];
    if (flags.has(word)) continue;
    let name = word;
    let value = null;
    const separator = word.indexOf('=');
    if (separator > 0) {
      name = word.slice(0, separator);
      value = word.slice(separator + 1);
    }
    if (valueOptions.has(name)) {
      const group = valueOptions.get(name);
      if (values.has(group)) return null;
      if (value === null) value = words[++index];
      if (!literalOperand(value)) return null;
      values.set(group, value);
      continue;
    }
    if (word.startsWith('-') || !literalOperand(word)) return null;
    filter.push(word);
  }
  const interfaceName = values.get('interface');
  const count = values.get('count');
  const snapLength = values.get('snapshotLength');
  if (!interfaceName || !boundedInteger(count, LIMITS.outputRows)) return null;
  if (snapLength !== undefined && !boundedInteger(snapLength, 262_144)) return null;
  const sink = values.get('sink');
  if (sink !== undefined) {
    if (sink === '-') {
      return { risk: 'SAFE_READ_ONLY', target: `${interfaceName} -> stdout:pcap`, modifiers: ['SENSITIVE_OUTPUT', 'RESOURCE_INTENSIVE', 'ALWAYS_ASK'] };
    }
    const resolved = resolveOutputPath(sink, context);
    if (resolved === null) return null;
    return { risk: 'LOW_RISK_CHANGE', target: `${interfaceName} -> file:${resolved}`, modifiers: ['SENSITIVE_OUTPUT', 'RESOURCE_INTENSIVE', 'FILE_WRITE', 'ALWAYS_ASK'] };
  }
  return { risk: 'SAFE_READ_ONLY', target: interfaceName, modifiers: ['SENSITIVE_OUTPUT', 'RESOURCE_INTENSIVE', 'APPROVAL_REQUIRED'] };
}

function parseCtr(words) {
  if (words.length < 3 || words[1] !== 'images') return null;
  const verb = words[2].toLowerCase();
  const operands = words.slice(3);
  if (operands.some((word) => !literalOperand(word)) || operands.length > LIMITS.fanOut) return null;
  if (['list', 'ls'].includes(verb) && operands.length === 0) return { risk: 'SAFE_READ_ONLY', target: 'local' };
  if (['pull', 'import'].includes(verb) && operands.length === 1) return { risk: 'LOW_RISK_CHANGE', target: operands[0] };
  if (['rm', 'remove'].includes(verb) && operands.length >= 1) return { risk: 'DESTRUCTIVE', target: operands.join(',') };
  return null;
}

function parseDmesg(words) {
  const args = words.slice(1);
  const destructive = new Set(['-C', '--clear', '-c', '--read-clear']);
  const disruptiveFlags = new Set(['-D', '--console-off', '-E', '--console-on']);
  const displayFlags = new Set(['-H', '--human', '-T', '--ctime', '-x', '--decode', '--color=never']);
  let risk = 'SAFE_READ_ONLY';
  let hasLevel = false;
  for (let index = 0; index < args.length; index += 1) {
    const word = args[index];
    if (destructive.has(word)) {
      risk = 'DESTRUCTIVE';
      continue;
    }
    if (disruptiveFlags.has(word)) {
      if (risk !== 'DESTRUCTIVE') risk = 'DISRUPTIVE_CHANGE';
      continue;
    }
    if (word === '-n' || word === '--console-level') {
      if (!literalOperand(args[++index])) return null;
      if (risk !== 'DESTRUCTIVE') risk = 'DISRUPTIVE_CHANGE';
      continue;
    }
    if (word.startsWith('--console-level=')) {
      if (!literalOperand(word.slice('--console-level='.length))) return null;
      if (risk !== 'DESTRUCTIVE') risk = 'DISRUPTIVE_CHANGE';
      continue;
    }
    if (word === '-l' || word === '--level') {
      if (!literalOperand(args[++index])) return null;
      hasLevel = true;
      continue;
    }
    if (word.startsWith('--level=') && literalOperand(word.slice('--level='.length))) {
      hasLevel = true;
      continue;
    }
    if (!displayFlags.has(word)) return null;
  }
  if (risk !== 'SAFE_READ_ONLY') return { risk, modifiers: [] };
  return hasLevel ? { risk, modifiers: ['SENSITIVE_OUTPUT', 'APPROVAL_REQUIRED'] } : null;
}

export function lookupFamily(stage, context = {}) {
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
    if (words.includes('-K') || words.includes('--kill')) return result('POSIX_HOST_READ', 'DESTRUCTIVE', words.at(-1), 'local');
    return result('POSIX_HOST_READ', 'SAFE_READ_ONLY', 'local');
  }
  if (lower === 'mount') {
    if (words.slice(1).some((word) => !['-l', '--show-labels', '-v', '--verbose'].includes(word))) return null;
    return result('POSIX_HOST_READ', 'SAFE_READ_ONLY', 'local');
  }
  if (lower === 'ip') {
    if (words.slice(1).some((word) =>
      ['-b', '-batch', '--batch'].includes(word) || /^--?batch=/u.test(word) || /^-b(?!r(?:ief)?$).+/u.test(word))) return null;
    const mutating = new Set(['add', 'append', 'change', 'delete', 'del', 'flush', 'replace', 'set', 'exec']);
    if (words.slice(1).some((word) => mutating.has(word.toLowerCase()))) return null;
    if (!words.slice(1).some((word) => /^(?:addr(?:ess)?|link|route|rule|neigh(?:bor)?)$/iu.test(word))) return null;
    return result('POSIX_HOST_READ', 'SAFE_READ_ONLY', 'local');
  }
  if (lower === 'journalctl') {
    const invocation = parseJournalctl(words);
    return invocation ? result('LOG_READ', invocation.risk, invocation.target, 'local') : null;
  }
  if (lower === 'dmesg') {
    const invocation = parseDmesg(words);
    return invocation ? result('LOG_READ', invocation.risk, 'kernel-log', 'local', invocation.modifiers, { requiresExplicitBinding: invocation.risk !== 'SAFE_READ_ONLY' }) : null;
  }
  if ((FILTER.has(lower) || PS_FILTER.has(lower) || ['sed', 'awk', 'jq'].includes(lower)) && isBoundedFilter(words, lower)) {
    return result('FILTER', 'SAFE_READ_ONLY', null);
  }
  if (lower === 'test-connection') {
    const count = optionCaseInsensitive(words, '-Count');
    if (!boundedInteger(count, LIMITS.fanOut)) return null;
    return result('POWERSHELL_READ', 'SAFE_READ_ONLY', words[1], 'network', ['ACTIVE_PROBE', 'APPROVAL_REQUIRED']);
  }
  if (PS_READ.has(lower)) return result('POWERSHELL_READ', 'SAFE_READ_ONLY', 'local');
  if (lower === 'gpg' || lower === 'age') {
    if (!words.some((word) => word === '-d' || word === '--decrypt')) return null;
    const literalPassphrase = lower === 'gpg' && words.some((word) => word === '--passphrase' || word.startsWith('--passphrase='));
    return result('DECRYPTOR', 'SAFE_READ_ONLY', words.at(-1), null, ['SENSITIVE_OUTPUT'], {
      sensitiveSource: true,
      credentialConsumer: literalPassphrase,
      credentialTransports: literalPassphrase ? ['FLAG'] : [],
    });
  }

  if (lower === 'sshpass') {
    const descriptor = words.findIndex((word) => word === '-d');
    if (descriptor < 0 || words[descriptor + 1] !== '0') return null;
    const nestedStart = descriptor + 2;
    const nested = lookupFamily({ ...stage, argv: words.slice(nestedStart) }, context);
    if (!nested || nested.policyId !== 'REMOTE') return null;
    return result('REMOTE', nested.risk, nested.target, nested.environment, [...nested.modifiers, 'CREDENTIAL_STDIN'], { credentialConsumer: true, credentialTransports: [] });
  }

  if (lower === 'sudo') {
    const nestedStart = words.findIndex((word, index) => index > 0 && !word.startsWith('-'));
    const nested = nestedStart > 0 ? lookupFamily({ ...stage, argv: words.slice(nestedStart) }, context) : null;
    return nested ? result('PRIVILEGE', nested.risk, nested.target, nested.environment, [...nested.modifiers, 'PRIVILEGED'], { credentialConsumer: words.includes('-S'), credentialTransports: [] }) : null;
  }

  if (lower === 'systemctl' || lower === 'service') {
    if (words.some((word) => /^(?:-H|--host|--root|--image|--machine)(?:=|$)/u.test(word))) return null;
    const command = lower === 'service' ? { word: words[2], index: 2 } : commandWord(words, 1);
    const verb = command?.word;
    if (!verb) return null;
    if (!['status', 'show', 'is-active', 'is-enabled', 'enable', 'disable', 'start', 'stop', 'restart', 'reload', 'daemon-reload', 'mask', 'unmask'].includes(verb)) return null;
    const risk = ['status', 'show', 'is-active', 'is-enabled'].includes(verb) ? 'SAFE_READ_ONLY' : ['enable', 'disable'].includes(verb) ? 'LOW_RISK_CHANGE' : 'DISRUPTIVE_CHANGE';
    const target = lower === 'service' ? words[1] : operandsAfter(words, command.index, ['--job-mode'])[0];
    return result('SERVICE_CONTROL', risk, target, 'local', [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });
  }

  if (lower === 'kubectl' || (lower === 'k3s' && words[1] === 'kubectl')) {
    if (words.some((word) => word === '--kubeconfig' || word.startsWith('--kubeconfig='))) return null;
    if (repeatedOptionGroup(words, ['--context']) || repeatedOptionGroup(words, ['--namespace', '-n'])) return null;
    const verbs = ['get', 'describe', 'logs', 'events', 'version', 'cluster-info', 'label', 'annotate', 'apply', 'patch', 'scale', 'cordon', 'uncordon', 'delete', 'drain', 'replace'];
    const command = commandWord(words, lower === 'k3s' ? 2 : 1, ['--context', '--namespace', '-n', '--kubeconfig', '--cluster', '--user', '--request-timeout']);
    const verb = command?.word;
    if (!verb) return null;
    if (!verbs.includes(verb)) return null;
    if (!hasClosedKubectlOptions(words, lower === 'k3s' ? 2 : 1, verb)) return null;
    if (['get', 'describe', 'logs', 'events'].includes(verb) && enabledBooleanOption(words, '--watch', '--watch-only', '-w')) return null;
    if (verb === 'logs' && enabledBooleanOption(words, '--follow', '-f')) return null;
    const chunkSize = option(words, '--chunk-size');
    if (chunkSize !== null && !boundedInteger(chunkSize, LIMITS.outputRows)) return null;
    if (verb === 'logs' && !boundedInteger(option(words, '--tail'), LIMITS.outputRows)) return null;
    const forceReplace = verb === 'replace' && words.includes('--force');
    const risk = ['get', 'describe', 'logs', 'events', 'version', 'cluster-info'].includes(verb) ? 'SAFE_READ_ONLY' : ['label', 'annotate'].includes(verb) ? 'LOW_RISK_CHANGE' : ['delete', 'drain'].includes(verb) || forceReplace ? 'DESTRUCTIVE' : 'DISRUPTIVE_CHANGE';
    const context = option(words, '--context');
    const namespace = option(words, '--namespace', '-n');
    const operands = operandsAfter(words, command.index, ['--tail', '--replicas', '-f', '--filename', '--type', '-p', '--patch']);
    const secretRead = ['get', 'describe'].includes(verb) && operands.some((word) => /^(?:secret|secrets|configmap|configmaps)$/iu.test(word));
    const fileTarget = option(words, '-f', '--filename');
    const singleton = ['cordon', 'uncordon', 'drain'].includes(verb);
    const target = words.includes('--all') ? null : fileTarget ?? (singleton ? operands[0] : operands.length >= 2 ? `${operands[0]}/${operands[1]}` : null);
    return result('KUBERNETES', risk, risk === 'SAFE_READ_ONLY' ? context : target, [context, namespace].filter(Boolean).join('@') || null, secretRead ? ['SENSITIVE_OUTPUT', 'ALWAYS_ASK'] : [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });
  }

  if (lower === 'ctr') {
    const invocation = parseCtr(words);
    return invocation ? result('CONTAINER', invocation.risk, invocation.target, 'local', [], { requiresExplicitBinding: invocation.risk !== 'SAFE_READ_ONLY' }) : null;
  }

  if (CONTAINERS.has(lower)) {
    if (words.some((word) => /^(?:--host|--config|--connection)(?:=|$)|^-H(?:=|.|$)/u.test(word))) return null;
    if (repeatedOptionGroup(words, ['--context'])) return null;
    const command = commandWord(words, 1, ['--context', '--host', '-H', '--config', '--connection']);
    const verb = command?.word;
    if (!verb || (verb === 'stats' && !words.includes('--no-stream'))) return null;
    if (!['ps', 'inspect', 'logs', 'stats', 'images', 'info', 'pull', 'tag', 'rename', 'start', 'stop', 'restart', 'pause', 'unpause', 'rm', 'rmi', 'prune', 'reset'].includes(verb)) return null;
    const logInvocation = verb === 'logs' ? parseContainerLogs(words, command.index) : null;
    if (verb === 'logs' && !logInvocation) return null;
    const risk = ['ps', 'inspect', 'logs', 'stats', 'images', 'info'].includes(verb) ? 'SAFE_READ_ONLY' : ['pull', 'tag', 'rename'].includes(verb) ? 'LOW_RISK_CHANGE' : ['rm', 'rmi', 'prune', 'reset'].includes(verb) ? 'DESTRUCTIVE' : 'DISRUPTIVE_CHANGE';
    const target = logInvocation?.target ?? operandsAfter(words, command.index, ['--time', '-t'])[0];
    const modifiers = verb === 'inspect' ? ['SENSITIVE_OUTPUT', 'ALWAYS_ASK'] : [];
    const context = option(words, '--context');
    if (context && /[$*?{}]/u.test(context)) return null;
    return result('CONTAINER', risk, risk === 'SAFE_READ_ONLY' ? 'local' : target, context, modifiers, { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });
  }

  if (lower === 'aws') {
    if (words.some((word) => /^(?:--endpoint-url|--ca-bundle|--no-verify-ssl|--no-sign-request|--debug|--cli-input-json|--cli-input-yaml|--cli-auto-prompt|--generate-cli-skeleton)(?:=|$)/u.test(word))) return null;
    if (repeatedOptionGroup(words, ['--profile']) || repeatedOptionGroup(words, ['--region'])) return null;
    const assignedProfile = assignmentValue(argv, 'AWS_PROFILE');
    const selectedProfile = option(words, '--profile');
    if (assignedProfile && selectedProfile && assignedProfile !== selectedProfile) return null;
    const service = commandWord(words, 1, ['--profile', '--region', '--endpoint-url', '--output', '--query'])?.index;
    const action = service === undefined ? null : words[service + 1]?.toLowerCase();
    const permittedAction = action && cloudAction([action], ['describe-', 'get-', 'list-', 'head-', 'create-tags', 'delete-tags', 'start-', 'stop-', 'reboot-', 'update-', 'delete-', 'terminate-', 'deregister-']);
    if (!permittedAction) return null;
    if (/^(?:describe|list)-/u.test(action) && !boundedInteger(option(words, '--max-items'), LIMITS.fanOut)) return null;
    const risk = /^(describe|get|list|head)-/u.test(action) ? 'SAFE_READ_ONLY' : /^(create-tags|delete-tags)$/u.test(action) ? 'LOW_RISK_CHANGE' : /^(delete|terminate|deregister)-/u.test(action) ? 'DESTRUCTIVE' : 'DISRUPTIVE_CHANGE';
    const environment = [selectedProfile ?? assignedProfile, option(words, '--region')].filter(Boolean).join('@') || null;
    const target = option(words, '--instance-ids', '--resource-arn', '--resources', '--resource-id', '--bucket');
    const sensitiveRead = risk === 'SAFE_READ_ONLY' && /^get-/u.test(action);
    return result('AWS', risk, risk === 'SAFE_READ_ONLY' ? target ?? action : target, environment, sensitiveRead ? ['SENSITIVE_OUTPUT', 'ALWAYS_ASK'] : [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY', credentialConsumer: true, credentialTransports: ['VARIABLE'], credentialSelectors: ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN'] });
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
    const invocation = parsePostgresInvocation(words, context.env);
    if (!invocation || !boundedRelationalRead(invocation.query)) return null;
    const risk = queryRisk(invocation.query, [/^(SELECT|SHOW|EXPLAIN(?!\s+ANALYZE))/u], [/^SET\s+/u], [/^(VACUUM|ANALYZE|REINDEX)/u], [/^(DROP|TRUNCATE|DELETE|UPDATE|INSERT|ALTER|CREATE)/u]);
    return risk ? result('POSTGRES', risk, invocation.database ?? 'default-db', canonicalDatabaseEnvironment('POSTGRES', invocation), [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY', credentialConsumer: true, credentialTransports: ['VARIABLE'], credentialSelectors: ['PGPASSWORD'] }) : null;
  }
  if (lower === 'mysql' || lower === 'mysqladmin') {
    const invocation = parseMySqlInvocation(words, lower);
    if (!invocation || !boundedRelationalRead(invocation.query)) return null;
    const risk = queryRisk(invocation.query, [/^(SELECT|SHOW|EXPLAIN|STATUS|PING)/u], [/^SET\s+/u], [/^(FLUSH|OPTIMIZE|ANALYZE|REPAIR)/u], [/^(DROP|TRUNCATE|DELETE|UPDATE|INSERT|ALTER|CREATE|SHUTDOWN)/u]);
    return risk ? result('MYSQL', risk, invocation.database ?? 'default-db', canonicalDatabaseEnvironment('MYSQL', invocation), [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY', credentialConsumer: true, credentialTransports: ['VARIABLE', 'FLAG'], credentialSelectors: ['MYSQL_PWD'] }) : null;
  }
  if (lower === 'mongosh') {
    const invocation = parseMongoInvocation(words);
    if (!invocation) return null;
    const { script, uri } = invocation;
    if (/;|\b(?:runProgram|load|require|process|child_process)\b/iu.test(script)) return null;
    const risk = queryRisk(script, [/\b(find|findOne|explain|serverStatus|replSetGetStatus)\b/iu], [], [/\b(reconfig|compact|repairDatabase)\b/iu], [/\b(insert|update|delete|drop|shutdown)\b/iu]);
    if (!risk) return null;
    let parsed;
    try { parsed = new URL(uri.replace(/^mongodb(?:\+srv)?:/iu, 'http:')); } catch { return null; }
    return result('MONGODB', risk, parsed.pathname.slice(1) || 'server', parsed.host, [], { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY', credentialConsumer: true, credentialTransports: ['URI_USERINFO'] });
  }
  if (lower === 'redis-cli') {
    const invocation = parseRedisInvocation(words);
    const environment = invocation ? canonicalRedisEnvironment(invocation) : null;
    if (!environment) return null;
    const command = parseRedisCommand(words, invocation.commandIndex);
    return command ? result('REDIS', command.risk, command.target, environment, [], { requiresExplicitBinding: command.risk !== 'SAFE_READ_ONLY', credentialConsumer: true, credentialTransports: ['FLAG'] }) : null;
  }

  if (lower === 'ping') {
    const count = option(words, '-c', '-n');
    if (!boundedInteger(count, LIMITS.fanOut) || /[$*?{}]/u.test(words.at(-1))) return null;
    return result('NETWORK_READ', 'SAFE_READ_ONLY', words.at(-1), 'network', ['ACTIVE_PROBE', 'APPROVAL_REQUIRED']);
  }
  if (['traceroute', 'tracepath'].includes(lower)) {
    const hops = option(words, '-m', '--max-hops');
    if (hops !== null && !boundedInteger(hops, LIMITS.fanOut)) return null;
    if (/[$*?{}]/u.test(words.at(-1))) return null;
    return result('NETWORK_READ', 'SAFE_READ_ONLY', words.at(-1), 'network', ['ACTIVE_PROBE', 'APPROVAL_REQUIRED']);
  }
  if (['dig', 'nslookup', 'host'].includes(lower)) {
    if (/[$*?{}]/u.test(words.at(-1))) return null;
    return result('NETWORK_READ', 'SAFE_READ_ONLY', words.at(-1), 'network', ['ACTIVE_PROBE', 'APPROVAL_REQUIRED']);
  }
  if (lower === 'tcpdump' || lower === 'tshark') {
    const invocation = parsePacketCapture(words, context);
    return invocation ? result('PACKET_CAPTURE', invocation.risk, invocation.target, 'local', invocation.modifiers) : null;
  }
  if (lower === 'curl' || lower === 'invoke-restmethod' || lower === 'invoke-webrequest') {
    return classifyHttp(words, context);
  }
  if (lower === 'ssh') return remoteFamily(words);
  if (lower === 'scp' || lower === 'sftp') {
    const invocation = parseRemoteTransfer(words, lower);
    return invocation ? result('REMOTE', 'LOW_RISK_CHANGE', invocation.target, invocation.environment, ['REMOTE_TRANSFER'], { requiresExplicitBinding: true, credentialConsumer: true }) : null;
  }
  if (lower === 'git' || lower === 'gh') return gitCiFamily(words, lower, context);
  if (['restart-service', 'start-service', 'stop-service', 'set-service'].includes(lower)) {
    const risk = lower === 'set-service' ? 'LOW_RISK_CHANGE' : 'DISRUPTIVE_CHANGE';
    return result('WINDOWS_CONTROL', risk, option(words, '-Name') ?? words.at(-1), 'local', [], { requiresExplicitBinding: true });
  }
  return null;
}
