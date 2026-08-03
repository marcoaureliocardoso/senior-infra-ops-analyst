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
  {
    id: 'POLICY_CREDENTIAL_CONSUMER_BINDING', file: 'command-guard/policy.mjs',
    search: "const credentialBinding = credentialStage?.environment && credentialStage.policyId\n    ? {\n      domain: credentialStage.environment,\n      family: credentialStage.policyId,\n      targetClass: credentialStage.policyId,\n    }\n    : null;",
    replacement: "const credentialBinding = aggregate.environment && aggregate.policyId\n    ? { domain: aggregate.environment, family: aggregate.policyId, targetClass: aggregate.policyId }\n    : null;",
  },
  {
    id: 'CATALOGUE_MONGOSH_SINGLE_EVAL', file: 'command-guard/catalogue.mjs',
    search: '      if (script !== null) return null;',
    replacement: '      if (false) return null;',
  },
  {
    id: 'CATALOGUE_IP_BATCH_REJECT', file: 'command-guard/catalogue.mjs',
    search: "    if (words.slice(1).some((word) =>\n      ['-b', '-batch', '--batch'].includes(word) || /^--?batch=/u.test(word) || /^-b(?!r(?:ief)?$).+/u.test(word))) return null;",
    replacement: '    if (false) return null;',
  },
  {
    id: 'CATALOGUE_REMOTE_EXECUTOR_REJECT', file: 'command-guard/catalogue.mjs',
    search: "const values = new Set(['-P', '-i', '-J', '-l']);",
    replacement: "const values = new Set(['-P', '-i', '-J', '-l', '-S']);",
  },
  {
    id: 'CATALOGUE_PACKET_SINK_EFFECT', file: 'command-guard/catalogue.mjs',
    search: "  const sink = values.get('sink');",
    replacement: '  const sink = undefined;',
  },
  {
    id: 'CATALOGUE_CTR_NESTED_RISK', file: 'command-guard/catalogue.mjs',
    search: "if (['pull', 'import'].includes(verb) && operands.length === 1) return { risk: 'LOW_RISK_CHANGE', target: operands[0] };",
    replacement: "if (['pull', 'import'].includes(verb) && operands.length === 1) return { risk: 'SAFE_READ_ONLY', target: operands[0] };",
  },
  {
    id: 'CATALOGUE_GIT_OUTPUT_EFFECT', file: 'command-guard/catalogue.mjs',
    search: "    if (verb === 'diff' && (word === '--output' || word.startsWith('--output='))) {",
    replacement: "    if (false && (word === '--output' || word.startsWith('--output='))) {",
  },
  {
    id: 'CATALOGUE_DMESG_CONTROL_RISK', file: 'command-guard/catalogue.mjs',
    search: "    if (destructive.has(word)) {\n      risk = 'DESTRUCTIVE';",
    replacement: "    if (destructive.has(word)) {\n      risk = 'SAFE_READ_ONLY';",
  },
  {
    id: 'POLICY_CREDENTIAL_STAGE_OWNERSHIP', file: 'command-guard/credential-flow.mjs',
    search: 'stage: literalStage, literal: true',
    replacement: 'stage: composition.stages.at(-1).index, literal: true',
  },
  {
    id: 'CATALOGUE_REMOTE_ENDPOINT_IDENTITY', file: 'command-guard/catalogue.mjs',
    search: 'const environment = `ssh://${encodeURIComponent(user)}@${host.toLowerCase()}:${Number(port)}${query.length ? `;${query.join(\';\')}` : \'\'}`;',
    replacement: 'const environment = `ssh://${encodeURIComponent(user)}@${host.toLowerCase()}:22`;',
  },
  {
    id: 'CATALOGUE_PACKET_STDOUT_IDENTITY', file: 'command-guard/catalogue.mjs',
    search: "    if (sink === '-') {",
    replacement: '    if (false) {',
  },
  {
    id: 'CATALOGUE_PACKET_SELECTOR_UNIQUENESS', file: 'command-guard/catalogue.mjs',
    search: '    if (valueOptions.has(name)) {\n      const group = valueOptions.get(name);\n      if (values.has(group)) return null;',
    replacement: '    if (valueOptions.has(name)) {\n      const group = valueOptions.get(name);\n      if (false) return null;',
  },
  {
    id: 'POLICY_CREDENTIAL_EFFECTIVE_CONSUMER', file: 'command-guard/policy.mjs',
    search: "    !credentialStage?.credentialConsumer ||\n    !credentialStage.credentialTransports?.includes(credentialAnalysis.metadata.transport) ||\n    credentialAnalysis.metadata.transport === 'VARIABLE' && (\n      credentialAnalysis.metadata.selectors.length === 0 ||\n      !credentialAnalysis.metadata.selectors.every((selector) => credentialStage.credentialSelectors?.includes(selector))\n    )",
    replacement: '    false',
  },
  {
    id: 'CATALOGUE_REMOTE_ADDRESS_FAMILY_IDENTITY', file: 'command-guard/catalogue.mjs',
    search: "    if (word === '-4' || word === '-6') {\n      if (!setSelector('addressFamily', word === '-4' ? 'inet' : 'inet6')) return null;\n      continue;\n    }",
    replacement: '    if (false) {\n      continue;\n    }',
  },
  {
    id: 'CATALOGUE_REMOTE_ADDRESS_FAMILY_CANONICAL', file: 'command-guard/catalogue.mjs',
    search: "    return setSelector(selectorName, name === 'addressfamily' ? value.toLowerCase() : value);",
    replacement: '    return setSelector(selectorName, value);',
  },
  {
    id: 'CATALOGUE_GIT_PUSH_EXEC_REJECT', file: 'command-guard/catalogue.mjs',
    search: "    if (/^(?:--exec|--receive-pack|--push-option)(?:=|$)|^-o(?:.|$)|^--no-verify$/u.test(word)) return null;",
    replacement: "    if (/^(?:--exec|--receive-pack|--push-option)(?:=|$)|^-o(?:.|$)|^--no-verify$/u.test(word)) continue;",
  },
  {
    id: 'CATALOGUE_GIT_PUSH_DESTINATION_BINDING', file: 'command-guard/catalogue.mjs',
    search: "  return { risk, target: mirror ? 'refs:*' : operands.join(','), environment: repository };",
    replacement: "  return { risk, target: mirror ? 'refs:*' : operands.join(','), environment: 'local' };",
  },
  {
    id: 'CATALOGUE_JOURNAL_FOLLOW_REJECT', file: 'command-guard/catalogue.mjs',
    search: "function parseJournalctl(words) {\n  const valueOptions",
    replacement: "function parseJournalctl(words) {\n  if (words.includes('--follow') || words.includes('-f')) return { risk: 'SAFE_READ_ONLY', target: 'local-log' };\n  const valueOptions",
  },
  {
    id: 'CATALOGUE_CONTAINER_FOLLOW_REJECT', file: 'command-guard/catalogue.mjs',
    search: "function parseContainerLogs(words, commandIndex) {\n  const prefix",
    replacement: "function parseContainerLogs(words, commandIndex) {\n  if (words.includes('--follow') || words.includes('-f')) return { target: words.at(-1) };\n  const prefix",
  },
  {
    id: 'CATALOGUE_GH_WATCH_REJECT', file: 'command-guard/catalogue.mjs',
    search: "    if (word === '--watch' || word.startsWith('--watch=')) return null;",
    replacement: "    if (word === '--watch' || word.startsWith('--watch=')) continue;",
  },
  {
    id: 'CATALOGUE_GH_LIMIT_BOUND', file: 'command-guard/catalogue.mjs',
    search: "  if (limit !== undefined && !boundedInteger(limit, LIMITS.outputRows)) return null;",
    replacement: "  if (false && limit !== undefined && !boundedInteger(limit, LIMITS.outputRows)) return null;",
  },
  {
    id: 'CATALOGUE_GH_LOG_APPROVAL', file: 'command-guard/catalogue.mjs',
    search: "  const broadLogs = key === 'run view' && flags.has('log');",
    replacement: '  const broadLogs = false;',
  },
  {
    id: 'CATALOGUE_KUBECTL_DUMP_REJECT', file: 'command-guard/catalogue.mjs',
    search: "    if (verb === 'cluster-info' && operandsAfter(words, command.index, ['--context', '--namespace', '-n', '--request-timeout', '-o', '--output']).length > 0) return null;",
    replacement: "    if (false && verb === 'cluster-info' && operandsAfter(words, command.index, ['--context', '--namespace', '-n', '--request-timeout', '-o', '--output']).length > 0) return null;",
  },
  {
    id: 'CATALOGUE_GIT_PUSH_REPOSITORY_TRANSPORT', file: 'command-guard/catalogue.mjs',
    search: "    && !value.includes('::')",
    replacement: '    && true',
  },
  {
    id: 'CATALOGUE_GH_REPOSITORY_BINDING', file: 'command-guard/catalogue.mjs',
    search: "  if (remote === 'local') return null;",
    replacement: "  if (false && remote === 'local') return null;",
  },
  {
    id: 'CATALOGUE_CONTAINER_LOG_TARGET', file: 'command-guard/catalogue.mjs',
    search: "    return result('CONTAINER', risk, risk === 'SAFE_READ_ONLY' && verb !== 'logs' ? 'local' : target, context, modifiers, { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });",
    replacement: "    return result('CONTAINER', risk, risk === 'SAFE_READ_ONLY' ? 'local' : target, context, modifiers, { requiresExplicitBinding: risk !== 'SAFE_READ_ONLY' });",
  },
  {
    id: 'CATALOGUE_GIT_PUSH_URL_TRANSPORT', file: 'command-guard/catalogue.mjs',
    search: '    && (urlScheme === undefined || GIT_NATIVE_TRANSPORTS.has(urlScheme))',
    replacement: '    && true',
  },
  {
    id: 'CATALOGUE_GIT_PUSH_URL_SCHEME_CASE', file: 'command-guard/catalogue.mjs',
    search: "  const urlScheme = /^([A-Za-z][A-Za-z0-9+.-]*):\\/\\//u.exec(value ?? '')?.[1];",
    replacement: "  const urlScheme = /^([A-Za-z][A-Za-z0-9+.-]*):\\/\\//u.exec(value ?? '')?.[1]?.toLowerCase();",
  },
]);
