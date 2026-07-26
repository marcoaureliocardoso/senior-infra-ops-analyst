export const LIMITS = Object.freeze({
  inputBytes: 131072,
  jsonDepth: 16,
  commandChars: 32768,
  timeoutMs: 120000,
  stages: 8,
  redirects: 8,
  tokens: 512,
  tokenChars: 8192,
  outputRows: 1000,
  fanOut: 20,
  auditFieldChars: 512,
});

export const EXECUTOR_AGENTS = Object.freeze([
  'audit-evidence-collector',
  'cloud-platform-operator',
  'database-operator',
  'diagnostic-operator',
  'kubernetes-operator',
  'network-edge-operator',
  'observability-sre',
  'release-cicd-operator',
]);

export const NORMAL_MODES = Object.freeze([
  'default', 'plan', 'acceptEdits', 'auto', 'dontAsk',
]);
