import path from 'node:path';

import { LIMITS } from './limits.mjs';

const CONTROL_VARIABLE = 'OPS_COMMAND_GUARD_OUTPUT_VARIABLES';
const MAX_OUTPUT_VARIABLES = 8;
const VARIABLE_NAME = /^[A-Za-z_][A-Za-z0-9_]*$/u;
const CREDENTIALISH_NAME = /(?:^|_)(?:TOKEN|SECRET|PASSWORD|PASSWD|AUTH|COOKIE|CREDENTIAL|API_KEY|PRIVATE_KEY|KEY)(?:_|$)/iu;
const CONTROL_CHARACTER = /[\u0000-\u001f\u007f]/u;
const DYNAMIC_LITERAL = /[$`*?{}\[\]]/u;
const WINDOWS_ABSOLUTE = /^(?:[A-Za-z]:[\\/]|\\\\[^\\/]+[\\/][^\\/]+)/u;

function boundedString(value) {
  return typeof value === 'string'
    && value.length > 0
    && value.length <= LIMITS.tokenChars
    && !CONTROL_CHARACTER.test(value);
}

function ownString(env, name) {
  if (!Object.prototype.hasOwnProperty.call(env, name)) return null;
  return boundedString(env[name]) ? env[name] : null;
}

function configuredNames(env) {
  if (env === null || typeof env !== 'object') return null;
  if (!Object.prototype.hasOwnProperty.call(env, CONTROL_VARIABLE)) return [];
  const raw = env[CONTROL_VARIABLE];
  if (raw === '') return [];
  if (typeof raw !== 'string' || raw.length > LIMITS.auditFieldChars || CONTROL_CHARACTER.test(raw)) return null;
  const names = raw.split(',');
  if (names.length > MAX_OUTPUT_VARIABLES || names.some((name) => !VARIABLE_NAME.test(name) || CREDENTIALISH_NAME.test(name))) {
    return null;
  }
  if (new Set(names).size !== names.length) return null;
  return names;
}

function pathApiFor(...values) {
  return values.some((value) => typeof value === 'string' && WINDOWS_ABSOLUTE.test(value)) ? path.win32 : path.posix;
}

function absolutePath(value, api) {
  return boundedString(value) && api.isAbsolute(value);
}

function normalizedAbsolute(value, api) {
  if (!absolutePath(value, api)) return null;
  return api.normalize(value);
}

function remainsWithin(root, candidate, api) {
  const relative = api.relative(root, candidate);
  return relative === '' || (!relative.startsWith(`..${api.sep}`) && relative !== '..' && !api.isAbsolute(relative));
}

function hasTraversal(suffix) {
  return suffix.split(/[\\/]+/u).some((segment) => segment === '..');
}

function variableOperand(operand, dialect) {
  if (dialect === 'powershell') {
    const match = /^\$env:([A-Za-z_][A-Za-z0-9_]*)(?:[\\/](.*))?$/iu.exec(operand);
    return match ? { name: match[1], suffix: match[2] ?? '' } : null;
  }
  const match = /^\$(?:([A-Za-z_][A-Za-z0-9_]*)|\{([A-Za-z_][A-Za-z0-9_]*)\})(?:\/(.*))?$/u.exec(operand);
  return match ? { name: match[1] ?? match[2], suffix: match[3] ?? '' } : null;
}

function resolveVariableOutput(operand, { env, dialect }, names) {
  const parsed = variableOperand(operand, dialect);
  if (!parsed || !names.includes(parsed.name)) return null;
  const rootValue = ownString(env, parsed.name);
  if (rootValue === null) return null;
  const api = pathApiFor(rootValue, dialect === 'powershell' ? operand : '');
  const root = normalizedAbsolute(rootValue, api);
  if (root === null || hasTraversal(parsed.suffix) || DYNAMIC_LITERAL.test(parsed.suffix) || CONTROL_CHARACTER.test(parsed.suffix)) return null;
  const candidate = api.resolve(root, parsed.suffix || '.');
  return remainsWithin(root, candidate, api) ? candidate : null;
}

function resolveLiteralOutput(operand, { cwd, dialect }) {
  if (DYNAMIC_LITERAL.test(operand) || operand.startsWith('~') || operand === '.' || operand === '..') return null;
  const api = pathApiFor(operand, cwd, dialect === 'powershell' && operand.includes('\\') ? 'C:\\' : '');
  if (api.isAbsolute(operand)) return api.normalize(operand);
  if (!boundedString(cwd) || !api.isAbsolute(cwd)) return null;
  return api.resolve(cwd, operand);
}

export function resolveOutputPath(operand, { cwd = null, env = {}, dialect = 'bash' } = {}) {
  if (!boundedString(operand) || (dialect !== 'bash' && dialect !== 'powershell')) return null;
  const names = configuredNames(env);
  if (names === null) return null;
  if (operand.startsWith('$')) return resolveVariableOutput(operand, { env, dialect }, names);
  return resolveLiteralOutput(operand, { cwd, dialect });
}
