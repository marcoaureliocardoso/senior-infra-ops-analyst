const READ = new Set(['uname', 'uptime', 'free', 'df', 'ps', 'ss', 'ip', 'lsblk', 'mount', 'findmnt', 'journalctl', 'dmesg', 'ping', 'traceroute', 'tracepath', 'dig', 'nslookup', 'host', 'pg_isready']);
const FILTER = new Set(['grep', 'rg', 'head', 'tail', 'cut', 'sort', 'uniq', 'wc', 'jq']);
const PS_READ = /^(Get-|Test-|Resolve-DnsName$)/iu;
const PS_FILTER = new Set(['where-object', 'select-object', 'sort-object', 'group-object', 'measure-object', 'format-table']);

export const POLICY_IDS = Object.freeze(['HOST_READ', 'FILTER', 'SERVICE_CONTROL', 'KUBERNETES', 'HTTP', 'DECRYPTOR', 'PRIVILEGE', 'POWERSHELL_READ']);
export const COMMAND_FAMILIES = Object.freeze(POLICY_IDS);
export const FILTER_FAMILIES = Object.freeze(['FILTER']);

function executable(argv) {
  return argv.find((word) => !/^[A-Za-z_][A-Za-z0-9_]*=/u.test(word)) ?? '';
}

export function lookupFamily(stage) {
  const argv = [...stage.argv];
  const exe = executable(argv);
  const lower = exe.toLowerCase();
  if (READ.has(lower)) return { policyId: 'HOST_READ', risk: 'SAFE_READ_ONLY', target: 'local', modifiers: [] };
  if (FILTER.has(lower) || PS_FILTER.has(lower)) return { policyId: 'FILTER', risk: 'SAFE_READ_ONLY', target: null, modifiers: [] };
  if (PS_READ.test(exe)) return { policyId: 'POWERSHELL_READ', risk: 'SAFE_READ_ONLY', target: 'local', modifiers: [] };
  if (lower === 'gpg' || lower === 'age') return { policyId: 'DECRYPTOR', risk: 'SAFE_READ_ONLY', target: argv.at(-1), modifiers: ['SENSITIVE_OUTPUT'], sensitiveSource: true };
  if (lower === 'sudo') {
    const inner = argv.filter((word) => !word.startsWith('-')).slice(1);
    const nested = lookupFamily({ ...stage, argv: inner });
    return nested ? { ...nested, policyId: 'PRIVILEGE', modifiers: [...nested.modifiers, 'PRIVILEGED'], credentialConsumer: argv.includes('-S') } : null;
  }
  if (lower === 'systemctl' || lower === 'service') {
    const verb = argv.find((word) => ['status', 'show', 'is-active', 'is-enabled', 'enable', 'disable', 'start', 'stop', 'restart', 'reload', 'daemon-reload', 'mask', 'unmask'].includes(word));
    if (!verb) return null;
    const risk = ['status', 'show', 'is-active', 'is-enabled'].includes(verb) ? 'SAFE_READ_ONLY' : ['enable', 'disable'].includes(verb) ? 'LOW_RISK_CHANGE' : 'DISRUPTIVE_CHANGE';
    return { policyId: 'SERVICE_CONTROL', risk, target: argv.at(-1), modifiers: [] };
  }
  if (lower === 'kubectl') {
    const verb = argv.find((word) => ['get', 'describe', 'logs', 'version', 'scale', 'apply', 'patch', 'delete', 'drain'].includes(word));
    if (!verb) return null;
    const risk = ['get', 'describe', 'logs', 'version'].includes(verb) ? 'SAFE_READ_ONLY' : ['delete', 'drain'].includes(verb) ? 'DESTRUCTIVE' : 'DISRUPTIVE_CHANGE';
    const contextIndex = argv.indexOf('--context');
    const namespaceIndex = argv.indexOf('--namespace');
    return { policyId: 'KUBERNETES', risk, target: contextIndex >= 0 ? argv[contextIndex + 1] : null, environment: namespaceIndex >= 0 ? argv[namespaceIndex + 1] : null, modifiers: [] };
  }
  if (lower === 'curl') {
    const url = argv.find((word) => /^https?:\/\//iu.test(word));
    if (!url) return null;
    const methodIndex = argv.findIndex((word) => word === '-X' || word === '--request');
    const method = methodIndex >= 0 ? argv[methodIndex + 1]?.toUpperCase() : 'GET';
    const risk = ['GET', 'HEAD'].includes(method) ? 'SAFE_READ_ONLY' : method === 'DELETE' ? 'DESTRUCTIVE' : 'LOW_RISK_CHANGE';
    return { policyId: 'HTTP', risk, target: new URL(url).origin, modifiers: [], credentialConsumer: true };
  }
  return null;
}
