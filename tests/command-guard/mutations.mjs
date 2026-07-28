export const MUTATIONS = Object.freeze([
  {
    id: 'CONTRACT_BACKGROUND_REJECT', file: 'command-guard/contract.mjs',
    search: "if (value.tool_input.run_in_background === true) throw new Error('background execution is denied');",
    replacement: "if (false) throw new Error('background execution is denied');",
  },
  {
    id: 'CONTRACT_COMMAND_BOUND', file: 'command-guard/contract.mjs',
    search: "if (command.length > LIMITS.commandChars) throw new Error('command length exceeds limit');",
    replacement: "if (command.length < 0) throw new Error('command length exceeds limit');",
  },
  {
    id: 'LEXER_DYNAMIC_REJECT', file: 'command-guard/bash-lexer.mjs',
    search: "for (const pattern of UNSUPPORTED) if (pattern.test(command)) throw new Error('unsupported dynamic shell construct');",
    replacement: "for (const pattern of UNSUPPORTED) if (false && pattern.test(command)) throw new Error('unsupported dynamic shell construct');",
  },
  {
    id: 'POLICY_UNKNOWN_REJECT', file: 'command-guard/policy.mjs',
    search: "if (!match) return denied('DENY_UNKNOWN_COMMAND', stage.index);",
    replacement: "if (false && !match) return denied('DENY_UNKNOWN_COMMAND', stage.index);",
  },
  {
    id: 'POLICY_TARGET_REQUIRED', file: 'command-guard/policy.mjs',
    search: "if (match.requiresExplicitBinding && (!explicitBinding(match.target) || !explicitBinding(match.environment))) return denied('DENY_AMBIGUOUS_TARGET', stage.index);",
    replacement: "if (false) return denied('DENY_AMBIGUOUS_TARGET', stage.index);",
  },
  {
    id: 'POLICY_DESTRUCTIVE_ALWAYS_ASK', file: 'command-guard/policy.mjs',
    search: "let decision = aggregate.risk === 'SAFE_READ_ONLY' ? (boundedRead && !autonomous ? 'ask' : 'allow') : aggregate.risk === 'DESTRUCTIVE' ? 'ask' : autonomous ? 'allow' : 'ask';",
    replacement: "let decision = aggregate.risk === 'SAFE_READ_ONLY' ? (boundedRead && !autonomous ? 'ask' : 'allow') : aggregate.risk === 'DESTRUCTIVE' ? 'allow' : autonomous ? 'allow' : 'ask';",
  },
  {
    id: 'POLICY_RISK_ESCALATION', file: 'command-guard/policy.mjs',
    search: 'RANK[current.risk] > RANK[highest.risk] ? current : highest',
    replacement: 'RANK[current.risk] < RANK[highest.risk] ? current : highest',
  },
  {
    id: 'CREDENTIAL_UNSAFE_SINK_REJECT', file: 'command-guard/credential-flow.mjs',
    search: 'if (UNSAFE.has(executable)) return',
    replacement: 'if (false && UNSAFE.has(executable)) return',
  },
  {
    id: 'REDACTION_AUTHORIZATION', file: 'command-guard/redaction.mjs',
    search: '/Authorization:\\s*(?:[A-Za-z][A-Za-z0-9._~-]*\\s+)?([^\\s"\']+)/giu',
    replacement: '/X-Authorization:\\s*(?:[A-Za-z][A-Za-z0-9._~-]*\\s+)?([^\\s"\']+)/giu',
  },
  {
    id: 'AUDIT_FORBIDDEN_FIELD_REJECT', file: 'command-guard/audit.mjs',
    search: 'const FORBIDDEN = /command|secret|password|token|cookie|authorization|transcript/iu;',
    replacement: 'const FORBIDDEN = /^$/u;',
  },
  {
    id: 'ENTRYPOINT_CATCH_EXIT', file: 'validate-ops-command.mjs',
    search: '    return 2;',
    replacement: '    return 0;',
  },
]);
