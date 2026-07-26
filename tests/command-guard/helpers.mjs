import os from 'node:os';
import path from 'node:path';
import { mkdtemp, readFile, rm } from 'node:fs/promises';

export function validEvent(overrides = {}) {
  const base = {
    session_id: 'session-synthetic-001',
    hook_event_name: 'PreToolUse',
    agent_type: 'diagnostic-operator',
    permission_mode: 'default',
    tool_name: 'Bash',
    tool_input: { command: 'uname -a' },
  };
  return { ...base, ...overrides };
}

export async function temporaryAudit() {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'ops-guard-'));
  const auditPath = path.join(directory, 'audit.jsonl');
  return {
    auditPath,
    read: async () => readFile(auditPath, 'utf8'),
    cleanup: async () => rm(directory, { recursive: true, force: true }),
  };
}

