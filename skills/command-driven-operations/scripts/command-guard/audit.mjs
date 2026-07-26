import { appendFileSync, mkdirSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const FORBIDDEN = /command|secret|password|token|cookie|authorization|transcript/iu;

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

export function appendAudit(result, event, env = process.env) {
  const auditPath = resolveAuditPath(env);
  const record = sanitizeAuditValue({
    timestamp: new Date().toISOString(), sessionId: event.sessionId,
    agent: event.agentType, mode: event.permissionMode, risk: result.risk ?? null,
    modifiers: result.modifiers ?? [], policyId: result.policyId ?? null,
    target: result.target ?? null, environment: result.environment ?? null,
    scope: result.scope ?? null, credential: result.credential ?? null,
    fingerprint: result.fingerprint ?? null, decision: result.decision,
    reason: result.reasonCode, stage: result.stage ?? null,
  });
  mkdirSync(path.dirname(auditPath), { recursive: true, mode: 0o700 });
  appendFileSync(auditPath, `${JSON.stringify(record)}\n`, { encoding: 'utf8', mode: 0o600 });
}
