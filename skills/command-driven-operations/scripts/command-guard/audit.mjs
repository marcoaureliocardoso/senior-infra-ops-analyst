import { appendFileSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import os from 'node:os';
import path from 'node:path';

const FORBIDDEN = /command|secret|password|token|cookie|authorization|transcript/iu;
const LIVE_STAGE_NONCE = /^[a-f0-9]{32}$/u;

export function sanitizeAuditValue(value) {
  if (value === null || value === undefined) return null;
  if (Array.isArray(value)) return value.map(sanitizeAuditValue);
  if (typeof value === 'object') {
    const output = {};
    for (const [key, child] of Object.entries(value)) {
      if (FORBIDDEN.test(key)) throw new Error(`forbidden audit field: ${key}`);
      output[key] = sanitizeAuditValue(child);
    }
    return output;
  }
  return value;
}

export function resolveAuditPath(env = process.env, homeDirectory = os.homedir()) {
  return env.OPS_COMMAND_GUARD_AUDIT_PATH
    ? path.resolve(env.OPS_COMMAND_GUARD_AUDIT_PATH)
    : path.join(homeDirectory, '.claude', 'senior-infra-ops-analyst', 'command-guard-audit.jsonl');
}

export function structuralActionIdentity(result) {
  const structure = {
    policyId: result.policyId ?? null,
    risk: result.risk ?? null,
    modifiers: [...(result.modifiers ?? [])].sort(),
    target: result.target ?? null,
    environment: result.environment ?? null,
    scope: result.scope ?? null,
    decision: result.decision,
    reason: result.reasonCode,
    stage: result.stage ?? null,
    findings: (result.findings ?? []).map(({ stage, ruleId, risk, modifiers }) => ({
      stage, ruleId, risk, modifiers: [...modifiers].sort(),
    })),
  };
  return createHash('sha256').update(JSON.stringify(structure)).digest('hex');
}

export function appendAudit(result, event, env = process.env) {
  const auditPath = resolveAuditPath(env);
  const hasProbeNonce = Object.hasOwn(env, 'P005_LIVE_STAGE_NONCE');
  const probeNonce = env.P005_LIVE_STAGE_NONCE;
  if (hasProbeNonce && (typeof probeNonce !== 'string' || !LIVE_STAGE_NONCE.test(probeNonce))) {
    throw new Error('invalid live stage nonce');
  }
  const record = sanitizeAuditValue({
    timestamp: new Date().toISOString(), sessionId: event.sessionId,
    agent: event.agentType, mode: event.permissionMode, risk: result.risk ?? null,
    modifiers: result.modifiers ?? [], policyId: result.policyId ?? null,
    target: result.target ?? null, environment: result.environment ?? null,
    scope: result.scope ?? null, credential: result.credential ?? null,
    actionId: structuralActionIdentity(result), decision: result.decision,
    reason: result.reasonCode, stage: result.stage ?? null,
    findings: result.findings ?? [],
    ...(hasProbeNonce ? { probeNonce } : {}),
  });
  mkdirSync(path.dirname(auditPath), { recursive: true, mode: 0o700 });
  appendFileSync(auditPath, `${JSON.stringify(record)}\n`, { encoding: 'utf8', mode: 0o600 });
}
