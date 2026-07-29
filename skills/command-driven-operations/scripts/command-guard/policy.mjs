import { lexBash } from './bash-lexer.mjs';
import { lexPowerShell } from './powershell-lexer.mjs';
import { buildComposition } from './composition.mjs';
import { lookupFamily } from './catalogue.mjs';
import { classifyCredentials, credentialFlowErrors } from './credential-flow.mjs';
import { detectSensitiveSpans } from './redaction.mjs';
import { NORMAL_MODES } from './limits.mjs';

const RANK = { SAFE_READ_ONLY: 0, LOW_RISK_CHANGE: 1, DISRUPTIVE_CHANGE: 2, DESTRUCTIVE: 3 };
export const REASON_CODES = Object.freeze([
  'ALLOW_NARROW_READ', 'ALLOW_BYPASS_BOUNDED_READ', 'ALLOW_BYPASS_CATALOGUED_CHANGE',
  'ASK_BOUNDED_READ', 'ASK_NORMAL_MODE_CHANGE', 'ASK_DESTRUCTIVE', 'ASK_LITERAL_CREDENTIAL_NORMAL',
  'ASK_EXTERNAL_SIDE_EFFECT', 'ASK_SENSITIVE_OPERATION',
  'DENY_UNSUPPORTED_SYNTAX', 'DENY_SECRET_PERSISTENCE', 'DENY_SECRET_OUTPUT',
  'DENY_AUTHENTICATED_REDIRECT',
  'DENY_PROVIDER_CONTROL_CREDENTIAL_ACCESS',
  'DENY_MULTIPLE_CREDENTIAL_TRANSPORTS', 'DENY_UNKNOWN_CREDENTIAL_CONSUMER',
  'DENY_UNKNOWN_COMMAND', 'DENY_AMBIGUOUS_TARGET',
]);
export const SECURITY_PREDICATE_IDS = Object.freeze([
  'CONTRACT_BACKGROUND_REJECT', 'CONTRACT_COMMAND_BOUND', 'LEXER_DYNAMIC_REJECT',
  'POLICY_UNKNOWN_REJECT', 'POLICY_TARGET_REQUIRED', 'POLICY_DESTRUCTIVE_ALWAYS_ASK',
  'POLICY_RISK_ESCALATION', 'CREDENTIAL_UNSAFE_SINK_REJECT',
  'REDACTION_AUTHORIZATION', 'AUDIT_FORBIDDEN_FIELD_REJECT', 'ENTRYPOINT_CATCH_EXIT',
  'CATALOGUE_REDIS_EXPIRE_DELETE', 'CATALOGUE_REDIS_LITERAL_OPERAND',
  'CATALOGUE_REDIS_CLIENT_KILL', 'CATALOGUE_REDIS_CANONICAL_ENVIRONMENT',
  'CATALOGUE_REDIS_UNKNOWN_OPTION', 'CATALOGUE_HTTP_EXTERNAL_EFFECT',
  'CATALOGUE_CURL_REMOTE_NAME_ARITY', 'CATALOGUE_HTTP_SINK_ALWAYS_ASK',
  'CATALOGUE_DATABASE_SELECTOR_UNIQUENESS', 'CATALOGUE_DATABASE_CANONICAL_ENVIRONMENT',
  'CATALOGUE_GIT_LONG_DELETE', 'OUTPUT_PATH_ALLOWLIST',
  'CATALOGUE_HTTP_ROUTING_HEADER_REJECT', 'CATALOGUE_DATABASE_EXPLICIT_DOMAIN',
  'CATALOGUE_HTTP_STDOUT_SENSITIVE', 'OUTPUT_PATH_TILDE_REJECT',
  'CATALOGUE_POSTGRES_ENVIRONMENT_REJECT', 'CATALOGUE_MYSQL_SOCKET_HOST_REJECT',
  'CATALOGUE_CREDENTIAL_TRACE_DISCLOSURE',
  'CATALOGUE_POSTGRES_SSL_NEGOTIATION_ENV', 'CATALOGUE_POSTGRES_REQUIRE_AUTH_ENV',
  'CATALOGUE_POSTGRES_SSL_CERT_MODE_ENV', 'CATALOGUE_POSTGRES_SSL_MIN_PROTOCOL_ENV',
  'CATALOGUE_POSTGRES_SSL_MAX_PROTOCOL_ENV', 'CATALOGUE_POSTGRES_GSS_DELEGATION_ENV',
  'CATALOGUE_POSTGRES_MIN_PROTOCOL_ENV', 'CATALOGUE_POSTGRES_MAX_PROTOCOL_ENV',
]);

const DENY_GUIDANCE = Object.freeze({
  DENY_UNSUPPORTED_SYNTAX: 'Use one literal foreground command with supported quoting, operators, and finite bounds, then retry.',
  DENY_SECRET_PERSISTENCE: 'Remove file, log, history, or other persistence sinks and pass the sensitive value only to a supported direct consumer.',
  DENY_SECRET_OUTPUT: 'Remove display, clipboard, or generic output sinks and pass the sensitive value only to a supported direct consumer.',
  DENY_AUTHENTICATED_REDIRECT: 'Use the final explicit origin directly; authenticated redirects are not followed.',
  DENY_PROVIDER_CONTROL_CREDENTIAL_ACCESS: 'Use an operational credential source; Claude provider control credentials are outside the command boundary.',
  DENY_MULTIPLE_CREDENTIAL_TRANSPORTS: 'Use exactly one literal credential transport per command; split mixed Authorization, Cookie, flag, variable, or basic-auth transports into separately approved operations.',
  DENY_UNKNOWN_CREDENTIAL_CONSUMER: 'Use a catalogued credential consumer and an explicit supported transport without intermediate stages.',
  DENY_UNKNOWN_COMMAND: 'Reformulate with a catalogued executable, verb, literal operands, and finite options.',
  DENY_AMBIGUOUS_TARGET: 'Reformulate with explicit target and environment selectors; variables, globs, and implicit remote context are not sufficient.',
});

function denied(reasonCode, stage = 1) {
  const guidance = DENY_GUIDANCE[reasonCode];
  return { decision: 'deny', reasonCode, message: `${reasonCode}: stage ${stage} is prohibited or inconclusive. ${guidance}`, risk: null, modifiers: [], policyId: null, target: null, environment: null, scope: null, credential: null, stage };
}

function lexCommand(command) {
  const outer = lexBash(command);
  const words = outer.tokens.filter(({ kind }) => kind === 'word');
  if (['pwsh', 'powershell'].includes(words[0]?.cooked.toLowerCase())) {
    if (outer.tokens.some(({ kind }) => kind !== 'word')) throw new Error('PowerShell wrapper has outer composition');
    const commandIndexes = words
      .map(({ cooked }, index) => cooked.toLowerCase() === '-command' ? index : -1)
      .filter((index) => index >= 0);
    if (commandIndexes.length !== 1) throw new Error('unsupported PowerShell wrapper');
    const [commandIndex] = commandIndexes;
    const allowedWrapperOptions = new Set(['-noprofile', '-noninteractive', '-nolog', '-sta', '-mta']);
    if (words.slice(1, commandIndex).some(({ cooked }) => !allowedWrapperOptions.has(cooked.toLowerCase()))) {
      throw new Error('unsupported PowerShell wrapper option');
    }
    if (!words[commandIndex + 1] || commandIndex + 2 !== words.length) throw new Error('unconsumed PowerShell wrapper argument');
    return { lexed: lexPowerShell(words[commandIndex + 1].cooked), dialect: 'powershell' };
  }
  return { lexed: outer, dialect: 'bash' };
}

function explicitBinding(value) {
  return typeof value === 'string' && value.length > 0 && !/[$*?{}]/u.test(value);
}

export function analyzeCommand(event, env = {}) {
  let composition;
  let dialect;
  try {
    const lexed = lexCommand(event.command);
    composition = buildComposition(lexed.lexed);
    dialect = lexed.dialect;
  } catch { return denied('DENY_UNSUPPORTED_SYNTAX'); }
  const spans = detectSensitiveSpans(event.command);
  const credentialAnalysis = classifyCredentials(composition, event.command, spans);
  const credentialErrors = credentialFlowErrors(composition, credentialAnalysis);
  if (credentialErrors.length) return { ...denied(credentialErrors[0].reasonCode, credentialErrors[0].stage), credential: credentialAnalysis.metadata };
  const analyses = [];
  for (const stage of composition.stages) {
    if (stage.redirects.some(({ destination }) => !['/dev/null', 'NUL', '&1'].includes(destination))) return denied(credentialAnalysis.metadata ? 'DENY_SECRET_PERSISTENCE' : 'DENY_UNSUPPORTED_SYNTAX', stage.index);
    const match = lookupFamily(stage, { cwd: event.cwd, env, dialect });
    if (!match) return denied('DENY_UNKNOWN_COMMAND', stage.index);
    if (credentialAnalysis.metadata?.literal && match.modifiers.includes('CREDENTIAL_OUTPUT')) {
      return { ...denied('DENY_SECRET_OUTPUT', stage.index), credential: credentialAnalysis.metadata };
    }
    if (credentialAnalysis.metadata?.literal && match.modifiers.includes('CREDENTIAL_PERSISTENCE')) {
      return { ...denied('DENY_SECRET_PERSISTENCE', stage.index), credential: credentialAnalysis.metadata };
    }
    if (match.policyId === 'FILTER' && stage.index === 1) return denied('DENY_UNKNOWN_COMMAND', stage.index);
    if (match.requiresExplicitBinding && (!explicitBinding(match.target) || !explicitBinding(match.environment))) return denied('DENY_AMBIGUOUS_TARGET', stage.index);
    analyses.push({ ...match, stage: stage.index });
  }
  const aggregate = analyses.reduce((highest, current) => RANK[current.risk] > RANK[highest.risk] ? current : highest, analyses[0]);
  const modifiers = [...new Set(analyses.flatMap(({ modifiers: values }) => values))];
  const findings = analyses.map(({ stage, policyId, risk, modifiers: stageModifiers }) => ({
    stage, ruleId: policyId, risk, modifiers: stageModifiers,
  }));
  const knownMode = event.permissionMode === 'bypassPermissions' || NORMAL_MODES.includes(event.permissionMode);
  if (!knownMode) modifiers.push('UNKNOWN_MODE_CONSERVATIVE');
  const autonomous = event.permissionMode === 'bypassPermissions';
  const boundedRead = aggregate.risk === 'SAFE_READ_ONLY' && modifiers.includes('APPROVAL_REQUIRED');
  const alwaysAsk = modifiers.includes('ALWAYS_ASK');
  const externalEffect = modifiers.includes('EXTERNAL_SIDE_EFFECT');
  let decision = aggregate.risk === 'SAFE_READ_ONLY' ? (boundedRead && !autonomous ? 'ask' : 'allow') : aggregate.risk === 'DESTRUCTIVE' ? 'ask' : autonomous ? 'allow' : 'ask';
  let reasonCode = decision === 'allow' ? (boundedRead ? 'ALLOW_BYPASS_BOUNDED_READ' : aggregate.risk === 'SAFE_READ_ONLY' ? 'ALLOW_NARROW_READ' : 'ALLOW_BYPASS_CATALOGUED_CHANGE') : aggregate.risk === 'DESTRUCTIVE' ? 'ASK_DESTRUCTIVE' : boundedRead ? 'ASK_BOUNDED_READ' : 'ASK_NORMAL_MODE_CHANGE';
  if (alwaysAsk) { decision = 'ask'; reasonCode = 'ASK_SENSITIVE_OPERATION'; }
  if (externalEffect) { decision = 'ask'; reasonCode = 'ASK_EXTERNAL_SIDE_EFFECT'; }
  if (credentialAnalysis.metadata?.literal) { decision = 'ask'; reasonCode = 'ASK_LITERAL_CREDENTIAL_NORMAL'; }
  const action = decision === 'ask'
    ? 'Operator confirmation is required before execution.'
    : 'The effective permission mode authorizes this bounded operation.';
  const stageSummary = findings
    .map(({ stage, ruleId, risk }) => `stage ${stage} ${ruleId}/${risk}`)
    .join('; ');
  return {
    decision, reasonCode, message: `${reasonCode}: ${stageSummary}. ${action} Sensitive values are redacted.`,
    risk: aggregate.risk, modifiers, policyId: aggregate.policyId, target: aggregate.target,
    environment: aggregate.environment ?? null, scope: `stages:${composition.stages.length}`,
    credential: credentialAnalysis.metadata, findings, stage: aggregate.stage,
  };
}
