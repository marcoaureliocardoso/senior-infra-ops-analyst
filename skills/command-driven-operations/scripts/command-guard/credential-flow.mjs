import { detectSensitiveSpans } from './redaction.mjs';

const UNSAFE = new Set(['echo', 'printf', 'printenv', 'tee', 'out-file', 'write-output', 'set-clipboard']);

export function classifyCredentials(composition, command, spans = detectSensitiveSpans(command)) {
  const literal = spans.length > 0;
  const decryptor = composition.stages.find((stage) => ['gpg', 'age'].includes(stage.argv[0]?.toLowerCase()));
  const metadata = literal ? { source: 'MODEL_VISIBLE_LITERAL', type: 'SECRET', transport: spans[0].kind, literal: true } : decryptor ? { source: 'PROTECTED_FILE', type: 'SECRET', transport: 'STDIN_DIRECT', literal: false } : null;
  return { spans, metadata, decryptorStage: decryptor?.index ?? null };
}

export function credentialFlowErrors(composition, analysis) {
  if (!analysis.metadata) return [];
  for (const stage of composition.stages) {
    const executable = stage.argv.find((word) => !/^[A-Za-z_][A-Za-z0-9_]*=/u.test(word))?.toLowerCase();
    if (UNSAFE.has(executable)) return [{ reasonCode: executable === 'tee' ? 'DENY_SECRET_PERSISTENCE' : 'DENY_SECRET_OUTPUT', stage: stage.index }];
  }
  if (analysis.decryptorStage !== null) {
    const edge = composition.edges.find(({ from }) => from === analysis.decryptorStage);
    const consumer = edge ? composition.stages[edge.to - 1] : null;
    if (!consumer || consumer.argv[0]?.toLowerCase() !== 'sudo' || !consumer.argv.includes('-S')) return [{ reasonCode: 'DENY_UNKNOWN_CREDENTIAL_CONSUMER', stage: analysis.decryptorStage }];
  }
  if (analysis.metadata.literal) {
    const consumers = new Set(['curl', 'sudo', 'ssh', 'sshpass', 'psql', 'mysql', 'mongosh', 'redis-cli']);
    const executable = composition.stages.at(-1)?.argv.find((word) => !/^[A-Za-z_][A-Za-z0-9_]*=/u.test(word))?.toLowerCase();
    if (!consumers.has(executable)) return [{ reasonCode: 'DENY_UNKNOWN_CREDENTIAL_CONSUMER', stage: composition.stages.at(-1)?.index ?? 1 }];
  }
  return [];
}
