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
    replacement: "if (!match) return { decision: 'allow' };",
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
  {
    id: 'CATALOGUE_REDIS_EXPIRE_DELETE', file: 'command-guard/catalogue.mjs',
    search: "return { risk: ttl <= 0n ? 'DESTRUCTIVE' : 'LOW_RISK_CHANGE', target: args[0] };",
    replacement: "return { risk: 'LOW_RISK_CHANGE', target: args[0] };",
  },
  {
    id: 'CATALOGUE_REDIS_LITERAL_OPERAND', file: 'command-guard/catalogue.mjs',
    search: "return typeof value === 'string' && value.length > 0 && !/(?:[$*?{}]|\\[|\\])/u.test(value);",
    replacement: "return typeof value === 'string' && value.length > 0;",
  },
  {
    id: 'CATALOGUE_REDIS_CLIENT_KILL', file: 'command-guard/catalogue.mjs',
    search: "if (verb === 'CLIENT' && args[0]?.toUpperCase() === 'KILL') {",
    replacement: "if (false && verb === 'CLIENT' && args[0]?.toUpperCase() === 'KILL') {",
  },
  {
    id: 'CATALOGUE_REDIS_CANONICAL_ENVIRONMENT', file: 'command-guard/catalogue.mjs',
    search: 'return `redis+${transport}://${encodeURIComponent(user)}@${encodeURIComponent(host)}:${Number(portText)}/${Number(databaseText)}`;',
    replacement: 'return `redis+${transport}://default@${encodeURIComponent(host)}:6379/0`;',
  },
  {
    id: 'CATALOGUE_REDIS_UNKNOWN_OPTION', file: 'command-guard/catalogue.mjs',
    search: "const group = valueOptions.get(optionName);\n    if (!group || values.has(group)) return null;",
    replacement: "const group = valueOptions.get(optionName);\n    if (!group) continue; if (values.has(group)) return null;",
  },
  {
    id: 'CATALOGUE_HTTP_EXTERNAL_EFFECT', file: 'command-guard/catalogue.mjs',
    search: "const externalModifiers = mutable ? ['EXTERNAL_SIDE_EFFECT'] : [];",
    replacement: 'const externalModifiers = [];',
  },
  {
    id: 'CATALOGUE_CURL_REMOTE_NAME_ARITY', file: 'command-guard/catalogue.mjs',
    search: '    if (CURL_FLAGS.has(word)) {',
    replacement: "    if (CURL_SINK_FLAGS.has(word)) { index += 1; continue; }\n    if (CURL_FLAGS.has(word)) {",
  },
  {
    id: 'CATALOGUE_HTTP_SINK_ALWAYS_ASK', file: 'command-guard/catalogue.mjs',
    search: "const sinkModifiers = hasSink ? ['FILE_WRITE', 'ALWAYS_ASK'] : [];",
    replacement: "const sinkModifiers = hasSink ? ['FILE_WRITE'] : [];",
  },
  {
    id: 'CATALOGUE_DATABASE_SELECTOR_UNIQUENESS', file: 'command-guard/catalogue.mjs',
    search: 'const group = options.get(name);\n    if (!group || values.has(group)) return null;',
    replacement: 'const group = options.get(name);\n    if (!group) return null;',
  },
  {
    id: 'CATALOGUE_DATABASE_CANONICAL_ENVIRONMENT', file: 'command-guard/catalogue.mjs',
    search: 'return `${scheme}://${encodeURIComponent(user)}@${encodeURIComponent(host)}:${port}/${encodeURIComponent(database)}`;',
    replacement: 'return `${scheme}://default@${encodeURIComponent(host)}:1/default-db`;',
  },
  {
    id: 'CATALOGUE_GIT_LONG_DELETE', file: 'command-guard/catalogue.mjs',
    search: "if (['--delete', '--force'].includes(args[0])) {",
    replacement: "if (false && ['--delete', '--force'].includes(args[0])) {",
  },
  {
    id: 'OUTPUT_PATH_ALLOWLIST', file: 'command-guard/output-path.mjs',
    search: 'if (!parsed || !names.includes(parsed.name)) return null;',
    replacement: 'if (!parsed) return null;',
  },
  {
    id: 'CATALOGUE_HTTP_ROUTING_HEADER_REJECT', file: 'command-guard/catalogue.mjs',
    search: "if (!match || match[1].toLowerCase() === 'host') return false;",
    replacement: 'if (!match) return false;',
  },
  {
    id: 'CATALOGUE_DATABASE_EXPLICIT_DOMAIN', file: 'command-guard/catalogue.mjs',
    search: "if (!invocation || ['host', 'port', 'user', 'database'].some((key) => invocation[key] === null)) return null;",
    replacement: 'if (!invocation) return null;',
  },
  {
    id: 'CATALOGUE_HTTP_STDOUT_SENSITIVE', file: 'command-guard/catalogue.mjs',
    search: 'const sensitiveHeaders = isCurl && (',
    replacement: 'const sensitiveHeaders = false && isCurl && (',
  },
  {
    id: 'OUTPUT_PATH_TILDE_REJECT', file: 'command-guard/output-path.mjs',
    search: "if (DYNAMIC_LITERAL.test(operand) || operand.startsWith('~') || operand === '.' || operand === '..') return null;",
    replacement: "if (DYNAMIC_LITERAL.test(operand) || operand === '.' || operand === '..') return null;",
  },
  {
    id: 'CATALOGUE_POSTGRES_ENVIRONMENT_REJECT', file: 'command-guard/catalogue.mjs',
    search: "if (env && typeof env === 'object' && [...POSTGRES_FORBIDDEN_ENVIRONMENT].some((name) => Object.prototype.hasOwnProperty.call(env, name))) return null;",
    replacement: "if (false) return null;",
  },
  {
    id: 'CATALOGUE_MYSQL_SOCKET_HOST_REJECT', file: 'command-guard/catalogue.mjs',
    search: "if (['localhost', '.'].includes(invocation.host.toLowerCase())) return null;",
    replacement: "if (false) return null;",
  },
  {
    id: 'CATALOGUE_CREDENTIAL_TRACE_DISCLOSURE', file: 'command-guard/catalogue.mjs',
    search: "const credentialDisclosureModifiers = sinkOption === '--trace'",
    replacement: "const credentialDisclosureModifiers = false && sinkOption === '--trace'",
  },
  {
    id: 'CATALOGUE_POSTGRES_SSL_NEGOTIATION_ENV', file: 'command-guard/catalogue.mjs',
    search: "'PGSSLNEGOTIATION',",
    replacement: "'PGSSLNEGOTIATION_MUTATED',",
  },
  {
    id: 'CATALOGUE_POSTGRES_REQUIRE_AUTH_ENV', file: 'command-guard/catalogue.mjs',
    search: "'PGREQUIREAUTH',",
    replacement: "'PGREQUIREAUTH_MUTATED',",
  },
  {
    id: 'CATALOGUE_POSTGRES_SSL_CERT_MODE_ENV', file: 'command-guard/catalogue.mjs',
    search: "'PGSSLCERTMODE',",
    replacement: "'PGSSLCERTMODE_MUTATED',",
  },
  {
    id: 'CATALOGUE_POSTGRES_SSL_MIN_PROTOCOL_ENV', file: 'command-guard/catalogue.mjs',
    search: "'PGSSLMINPROTOCOLVERSION',",
    replacement: "'PGSSLMINPROTOCOLVERSION_MUTATED',",
  },
  {
    id: 'CATALOGUE_POSTGRES_SSL_MAX_PROTOCOL_ENV', file: 'command-guard/catalogue.mjs',
    search: "'PGSSLMAXPROTOCOLVERSION',",
    replacement: "'PGSSLMAXPROTOCOLVERSION_MUTATED',",
  },
  {
    id: 'CATALOGUE_POSTGRES_GSS_DELEGATION_ENV', file: 'command-guard/catalogue.mjs',
    search: "'PGGSSDELEGATION',",
    replacement: "'PGGSSDELEGATION_MUTATED',",
  },
  {
    id: 'CATALOGUE_POSTGRES_MIN_PROTOCOL_ENV', file: 'command-guard/catalogue.mjs',
    search: "'PGMINPROTOCOLVERSION',",
    replacement: "'PGMINPROTOCOLVERSION_MUTATED',",
  },
  {
    id: 'CATALOGUE_POSTGRES_MAX_PROTOCOL_ENV', file: 'command-guard/catalogue.mjs',
    search: "'PGMAXPROTOCOLVERSION',",
    replacement: "'PGMAXPROTOCOLVERSION_MUTATED',",
  },
]);
