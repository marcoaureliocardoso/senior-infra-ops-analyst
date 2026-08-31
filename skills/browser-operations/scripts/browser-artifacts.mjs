import { randomUUID } from 'node:crypto';
import {
  chmod, lstat, mkdir, mkdtemp, readFile, realpath, rm, writeFile,
} from 'node:fs/promises';
import path from 'node:path';


const FIELDS = new Set([
  'enabled', 'types', 'purposeRef', 'sourceClasses', 'destinationClasses',
  'maxItems', 'maxBytes', 'redaction', 'retentionSeconds',
]);
const TYPES = new Set(['upload', 'download', 'screenshot', 'trace']);
const FORBIDDEN_CLASSES = new Set([
  'browser-profile', 'browser-cookie', 'browser-cookies', 'browser-storage',
  'browser-page', 'raw-page', 'local-storage', 'session-storage',
]);
const MIME = Object.freeze({
  upload: new Set(['text/plain', 'application/json', 'application/octet-stream']),
  download: new Set(['text/plain', 'application/json', 'application/octet-stream']),
  screenshot: new Set(['image/png', 'image/jpeg']),
  trace: new Set(['application/json', 'application/zip']),
});
const TEXT_MIME = new Set(['text/plain', 'application/json']);


function artifactError(code) {
  const error = new Error(code);
  error.code = code;
  return error;
}


function validList(value, maximum = 16) {
  return Array.isArray(value) && value.length > 0 && value.length <= maximum
    && new Set(value).size === value.length
    && value.every((item) => typeof item === 'string' && /^[a-z0-9][a-z0-9-]{0,95}$/u.test(item));
}


function validatePolicy(policy) {
  if (!policy || typeof policy !== 'object' || Array.isArray(policy)
      || Object.keys(policy).some((key) => !FIELDS.has(key))
      || [...FIELDS].some((key) => !Object.hasOwn(policy, key))
      || policy.enabled !== true || !validList(policy.types, 4)
      || policy.types.some((type) => !TYPES.has(type))
      || !validList(policy.sourceClasses, 8) || !validList(policy.destinationClasses, 8)
      || policy.sourceClasses.some((value) => FORBIDDEN_CLASSES.has(value))
      || typeof policy.purposeRef !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$/u.test(policy.purposeRef)
      || policy.purposeRef === 'none'
      || !Number.isSafeInteger(policy.maxItems) || policy.maxItems < 1 || policy.maxItems > 16
      || !Number.isSafeInteger(policy.maxBytes) || policy.maxBytes < 1 || policy.maxBytes > 50_000_000
      || !['required', 'structured'].includes(policy.redaction)
      || !Number.isSafeInteger(policy.retentionSeconds)
      || policy.retentionSeconds < 1 || policy.retentionSeconds > 3600) {
    throw artifactError('ARTIFACT_POLICY_INVALID');
  }
  return Object.freeze({
    ...policy,
    types: Object.freeze([...policy.types]),
    sourceClasses: Object.freeze([...policy.sourceClasses]),
    destinationClasses: Object.freeze([...policy.destinationClasses]),
  });
}


function within(candidate, root) {
  const relative = path.relative(root, candidate);
  return relative !== '' && !relative.startsWith('..') && !path.isAbsolute(relative);
}


function redact(data, mimeType) {
  if (!TEXT_MIME.has(mimeType)) return { data, redacted: false };
  const text = data.toString('utf8');
  const value = text
    .replace(/SYNTH_SECRET_[A-Za-z0-9_-]+/gu, '[REDACTED]')
    .replace(/("(?:token|password|secret|credential)"\s*:\s*")[^"]*(")/giu, '$1[REDACTED]$2');
  return { data: Buffer.from(value, 'utf8'), redacted: value !== text };
}


export async function createArtifactManager(policyValue, options = {}) {
  const policy = validatePolicy(policyValue);
  const now = options.now ?? Date.now();
  if (!Number.isSafeInteger(now) || now < 0 || typeof options.operationId !== 'string') {
    throw artifactError('ARTIFACT_OPTIONS_INVALID');
  }
  const root = path.resolve(options.root ?? path.join(process.cwd(), '.browser-artifacts'));
  await mkdir(root, { recursive: true, mode: 0o700 });
  const rootInfo = await lstat(root);
  if (!rootInfo.isDirectory() || rootInfo.isSymbolicLink()) throw artifactError('ARTIFACT_ROOT_UNSAFE');
  await chmod(root, 0o700);
  const canonicalRoot = await realpath(root);
  const directory = await mkdtemp(path.join(canonicalRoot, 'p004b-operation-'));
  await chmod(directory, 0o700);
  const handles = new Map();
  let totalBytes = 0;
  let closed = false;
  const expiresAt = now + policy.retentionSeconds * 1000;
  const uploadRoots = [];
  for (const rootValue of options.uploadRoots ?? []) {
    const selected = path.resolve(rootValue);
    const info = await lstat(selected).catch(() => null);
    if (!info?.isDirectory() || info.isSymbolicLink()) throw artifactError('ARTIFACT_SOURCE_FORBIDDEN');
    uploadRoots.push(await realpath(selected));
  }

  function requireOpen() {
    if (closed) throw artifactError('ARTIFACT_MANAGER_CLOSED');
  }

  function validateMetadata(value) {
    if (!policy.types.includes(value.type)) throw artifactError('ARTIFACT_TYPE_FORBIDDEN');
    if (!policy.sourceClasses.includes(value.sourceClass) || FORBIDDEN_CLASSES.has(value.sourceClass)) {
      throw artifactError('ARTIFACT_SOURCE_FORBIDDEN');
    }
    if (!policy.destinationClasses.includes(value.destinationClass)) {
      throw artifactError('ARTIFACT_DESTINATION_FORBIDDEN');
    }
    if (!MIME[value.type]?.has(value.mimeType)) throw artifactError('ARTIFACT_MIME_FORBIDDEN');
  }

  async function store(value, { applyRedaction = true } = {}) {
    requireOpen();
    validateMetadata(value);
    if (handles.size >= policy.maxItems) throw artifactError('ARTIFACT_ITEM_LIMIT');
    const input = Buffer.isBuffer(value.data) ? value.data
      : typeof value.data === 'string' ? Buffer.from(value.data, 'utf8') : null;
    if (!input) throw artifactError('ARTIFACT_DATA_INVALID');
    const transformed = applyRedaction ? redact(input, value.mimeType) : { data: input, redacted: false };
    if (transformed.data.length > policy.maxBytes || totalBytes + transformed.data.length > policy.maxBytes) {
      throw artifactError('ARTIFACT_BYTE_LIMIT');
    }
    const artifactId = `artifact-${randomUUID()}`;
    const target = path.join(directory, `${artifactId}.bin`);
    if (!within(target, directory)) throw artifactError('ARTIFACT_PATH_ESCAPE');
    await writeFile(target, transformed.data, { mode: 0o600, flag: 'wx' });
    await chmod(target, 0o600);
    totalBytes += transformed.data.length;
    const handle = Object.freeze({
      artifactId, type: value.type, mimeType: value.mimeType,
      bytes: transformed.data.length, redacted: transformed.redacted, expiresAt,
    });
    handles.set(artifactId, { handle, target });
    return handle;
  }

  const manager = {
    directory,
    policy,
    async capture(value) { return store(value); },
    async stageUpload({ sourcePath, sourceClass, mimeType }) {
      requireOpen();
      const candidate = path.resolve(sourcePath);
      const info = await lstat(candidate).catch(() => null);
      if (!info?.isFile() || info.isSymbolicLink()) throw artifactError('ARTIFACT_SOURCE_FORBIDDEN');
      const canonical = await realpath(candidate);
      if (!uploadRoots.some((allowed) => within(canonical, allowed))) {
        throw artifactError('ARTIFACT_SOURCE_FORBIDDEN');
      }
      if (info.size > policy.maxBytes) throw artifactError('ARTIFACT_BYTE_LIMIT');
      const data = await readFile(canonical);
      return store({
        type: 'upload', sourceClass, destinationClass: 'operation-temp', mimeType, data,
      }, { applyRedaction: false });
    },
    materialize(artifactId) {
      requireOpen();
      const entry = handles.get(artifactId);
      if (!entry) throw artifactError('ARTIFACT_HANDLE_UNKNOWN');
      return entry.target;
    },
    async expire(at = Date.now()) {
      if (!Number.isSafeInteger(at) || at < expiresAt) return false;
      await manager.close({ retain: false, outcome: 'expiry' });
      return true;
    },
    async close({ retain = false } = {}) {
      if (closed) return;
      if (retain) return;
      const current = await lstat(directory).catch(() => null);
      if (current?.isSymbolicLink() || !within(directory, canonicalRoot)) {
        throw artifactError('ARTIFACT_DIRECTORY_UNSAFE');
      }
      closed = true;
      handles.clear();
      await rm(directory, { recursive: true, force: true });
    },
  };
  return Object.freeze(manager);
}
