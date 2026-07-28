import { detectSensitiveSpans } from './redaction.mjs';

const UNSAFE = new Set(['echo', 'printf', 'printenv', 'tee', 'out-file', 'write-output', 'set-clipboard']);
export const CREDENTIAL_TRANSPORTS = Object.freeze(['AUTHORIZATION', 'COOKIE', 'VARIABLE', 'FLAG', 'BASIC_AUTH', 'POWERSHELL_PLAINTEXT', 'URI_USERINFO', 'STDIN_DIRECT', 'PROVIDER_CACHE', 'PROTECTED_FILE']);

function referenceMetadata(command) {
  if (/\bAWS_PROFILE=/u.test(command) || /\s--profile(?:=|\s)/u.test(command)) {
    return { source: 'PROVIDER_CACHE', type: 'REFERENCE', transport: 'PROVIDER_CACHE', literal: false };
  }
  if (/\s(?:--cert|--key|--password-file|--identity-file)(?:=|\s)/u.test(command)) {
    return { source: 'PROTECTED_FILE', type: 'REFERENCE', transport: 'PROTECTED_FILE', literal: false };
  }
  if (/\$(?:[A-Za-z0-9_]*(?:PASSWORD|PASS|TOKEN|SECRET|API_KEY|ACCESS_KEY|CREDENTIAL|PRIVATE_KEY)[A-Za-z0-9_]*)\b/u.test(command)) {
    return { source: 'RUNTIME_VARIABLE', type: 'REFERENCE', transport: 'VARIABLE', literal: false };
  }
  return null;
}

export function classifyCredentials(composition, command, spans = detectSensitiveSpans(command)) {
  const literal = spans.length > 0;
  const decryptor = composition.stages.find((stage) => ['gpg', 'age'].includes(stage.argv[0]?.toLowerCase()));
  const metadata = literal
    ? { source: 'MODEL_VISIBLE_LITERAL', type: 'SECRET', transport: spans[0].kind, stage: composition.stages.at(-1).index, literal: true }
    : decryptor
      ? { source: 'PROTECTED_FILE', type: 'SECRET', transport: 'STDIN_DIRECT', stage: decryptor.index, literal: false }
      : referenceMetadata(command);
  return { spans, metadata, decryptorStage: decryptor?.index ?? null, command };
}

export function credentialFlowErrors(composition, analysis) {
  if (/\b(?:ANTHROPIC_AUTH_TOKEN|ANTHROPIC_API_KEY)\b/u.test(analysis.command)) {
    return [{ reasonCode: 'DENY_PROVIDER_CONTROL_CREDENTIAL_ACCESS', stage: 1 }];
  }
  if (!analysis.metadata) return [];
  for (const stage of composition.stages) {
    const executable = stage.argv.find((word) => !/^[A-Za-z_][A-Za-z0-9_]*=/u.test(word))?.toLowerCase();
    if (UNSAFE.has(executable)) return [{ reasonCode: executable === 'tee' ? 'DENY_SECRET_PERSISTENCE' : 'DENY_SECRET_OUTPUT', stage: stage.index }];
    if (executable === 'curl') {
      const options = new Set(stage.argv);
      const redirect = ['-L', '--location', '--location-trusted'].some((name) => options.has(name));
      if (redirect) return [{ reasonCode: 'DENY_AUTHENTICATED_REDIRECT', stage: stage.index }];
      const persistence = ['-o', '--output', '-O', '--remote-name', '--remote-header-name', '--dump-header', '-D', '--cookie-jar', '-c']
        .some((name) => options.has(name) || stage.argv.some((word) => word.startsWith(`${name}=`)));
      if (persistence) return [{ reasonCode: 'DENY_SECRET_PERSISTENCE', stage: stage.index }];
    }
  }
  if (analysis.decryptorStage !== null) {
    const edges = composition.edges.filter(({ from, to }) => from === analysis.decryptorStage || to === analysis.decryptorStage);
    const edge = edges.length === 1 ? edges[0] : null;
    const consumer = edge ? composition.stages[edge.to - 1] : null;
    const executable = consumer?.argv[0]?.toLowerCase();
    const directSudo = executable === 'sudo' && consumer.argv.includes('-S');
    const descriptor = executable === 'sshpass' ? consumer.argv.indexOf('-d') : -1;
    const directSshpass = descriptor >= 0 && consumer.argv[descriptor + 1] === '0';
    if (composition.stages.length !== 2 || composition.edges.length !== 1 || edge?.operator !== '|' || edge.from !== analysis.decryptorStage || !consumer || consumer.redirects.length || (!directSudo && !directSshpass)) return [{ reasonCode: 'DENY_UNKNOWN_CREDENTIAL_CONSUMER', stage: analysis.decryptorStage }];
  }
  if (analysis.metadata.literal) {
    const consumers = new Set(['curl', 'invoke-restmethod', 'invoke-webrequest', 'sudo', 'ssh', 'sshpass', 'psql', 'mysql', 'mongosh', 'redis-cli', 'aws', 'az', 'gcloud', 'gsutil', 'kubectl', 'gh']);
    const executable = composition.stages.at(-1)?.argv.find((word) => !/^[A-Za-z_][A-Za-z0-9_]*=/u.test(word))?.toLowerCase();
    if (!consumers.has(executable)) return [{ reasonCode: 'DENY_UNKNOWN_CREDENTIAL_CONSUMER', stage: composition.stages.at(-1).index }];
  }
  return [];
}
