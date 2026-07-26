import { lexBash } from './bash-lexer.mjs';
import { lexPowerShell } from './powershell-lexer.mjs';
import { buildComposition } from './composition.mjs';
import { lookupFamily } from './catalogue.mjs';
import { classifyCredentials, credentialFlowErrors } from './credential-flow.mjs';
import { detectSensitiveSpans, normalizeAndFingerprint } from './redaction.mjs';
import { NORMAL_MODES } from './limits.mjs';

const RANK = { SAFE_READ_ONLY: 0, LOW_RISK_CHANGE: 1, DISRUPTIVE_CHANGE: 2, DESTRUCTIVE: 3 };

function denied(reasonCode, stage = 1, modifiers = []) {
  return { decision: 'deny', reasonCode, message: `${reasonCode}: command stage ${stage} is prohibited or inconclusive.`, risk: null, modifiers, policyId: null, target: null, environment: null, scope: null, credential: null, stage };
}

function lexCommand(command) {
  const outer = lexBash(command);
  const words = outer.tokens.filter(({ kind }) => kind === 'word');
  if (['pwsh', 'powershell'].includes(words[0]?.cooked.toLowerCase())) {
    const commandIndex = words.findIndex(({ cooked }) => cooked.toLowerCase() === '-command');
    if (commandIndex < 0 || !words[commandIndex + 1]) throw new Error('unsupported PowerShell wrapper');
    return lexPowerShell(words[commandIndex + 1].cooked);
  }
  return outer;
}

export function analyzeCommand(event) {
  let composition;
  try { composition = buildComposition(lexCommand(event.command)); } catch { return denied('DENY_UNSUPPORTED_SYNTAX'); }
  const spans = detectSensitiveSpans(event.command);
  const credentialAnalysis = classifyCredentials(composition, event.command, spans);
  const credentialErrors = credentialFlowErrors(composition, credentialAnalysis);
  if (credentialErrors.length) return { ...denied(credentialErrors[0].reasonCode, credentialErrors[0].stage), credential: credentialAnalysis.metadata };
  const analyses = [];
  for (const stage of composition.stages) {
    if (stage.redirects.some(({ destination }) => !['/dev/null', 'NUL'].includes(destination))) return denied(credentialAnalysis.metadata ? 'DENY_SECRET_PERSISTENCE' : 'DENY_UNSUPPORTED_SYNTAX', stage.index);
    const match = lookupFamily(stage);
    if (!match) return denied('DENY_UNKNOWN_COMMAND', stage.index);
    if (match.policyId === 'FILTER' && stage.index === 1) return denied('DENY_UNKNOWN_COMMAND', stage.index);
    if (match.risk !== 'SAFE_READ_ONLY' && (!match.target || (match.policyId === 'KUBERNETES' && !match.environment))) return denied('DENY_AMBIGUOUS_TARGET', stage.index);
    analyses.push({ ...match, stage: stage.index });
  }
  const aggregate = analyses.reduce((highest, current) => RANK[current.risk] > RANK[highest.risk] ? current : highest, analyses[0]);
  const modifiers = [...new Set(analyses.flatMap(({ modifiers: values }) => values))];
  const knownMode = event.permissionMode === 'bypassPermissions' || NORMAL_MODES.includes(event.permissionMode);
  if (!knownMode) modifiers.push('UNKNOWN_MODE_CONSERVATIVE');
  const autonomous = event.permissionMode === 'bypassPermissions';
  let decision = aggregate.risk === 'SAFE_READ_ONLY' ? 'allow' : aggregate.risk === 'DESTRUCTIVE' ? 'ask' : autonomous ? 'allow' : 'ask';
  let reasonCode = decision === 'allow' ? (aggregate.risk === 'SAFE_READ_ONLY' ? 'ALLOW_NARROW_READ' : 'ALLOW_BYPASS_CATALOGUED_CHANGE') : aggregate.risk === 'DESTRUCTIVE' ? 'ASK_DESTRUCTIVE' : 'ASK_NORMAL_MODE_CHANGE';
  if (credentialAnalysis.metadata?.literal && !autonomous) { decision = 'ask'; reasonCode = 'ASK_LITERAL_CREDENTIAL_NORMAL'; }
  const { fingerprint } = normalizeAndFingerprint(event.command, spans);
  return {
    decision, reasonCode, message: `${reasonCode}: ${aggregate.policyId} stage ${aggregate.stage}; sensitive values redacted.`,
    risk: aggregate.risk, modifiers, policyId: aggregate.policyId, target: aggregate.target ?? null,
    environment: aggregate.environment ?? null, scope: `stages:${composition.stages.length}`,
    credential: credentialAnalysis.metadata, fingerprint, stage: aggregate.stage,
  };
}
