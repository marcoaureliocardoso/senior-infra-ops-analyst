import { normalizeOrigin } from '../browser-contract.mjs';


export const ADAPTER_CAPABILITIES = Object.freeze({
  preCall: true,
  topLevelOrigin: true,
  redirects: true,
  popups: true,
  subresources: true,
  ephemeralProfile: true,
  downloadsDefaultDenied: true,
  arbitraryScript: false,
});


export const PUPPETEER_CAPABILITIES = Object.freeze({
  ...ADAPTER_CAPABILITIES,
  popups: false,
});


export function adapterError(code) {
  const error = new Error(code);
  error.code = code;
  return error;
}


export function normalizedAllowedOrigins(values) {
  if (!Array.isArray(values) || values.length < 1 || values.length > 16) {
    throw adapterError('ADAPTER_ORIGINS_INVALID');
  }
  const normalized = values.map(normalizeOrigin);
  if (new Set(normalized).size !== normalized.length) {
    throw adapterError('ADAPTER_ORIGINS_INVALID');
  }
  return new Set(normalized);
}


export function assertAllowedUrl(value, allowedOrigins) {
  let selected;
  try {
    selected = normalizeOrigin(value);
  } catch {
    throw adapterError('ORIGIN_ESCAPE');
  }
  if (!allowedOrigins.has(selected)) throw adapterError('ORIGIN_ESCAPE');
  return value;
}


export function observedVersion(runtime) {
  for (const candidate of [runtime?.version, runtime?.default?.version]) {
    if (typeof candidate === 'string' && /^[A-Za-z0-9][A-Za-z0-9.+_-]{0,63}$/u.test(candidate)) {
      return candidate;
    }
  }
  return 'unknown';
}


export function boundedObservation(value) {
  if (typeof value !== 'string') return 'structural-observation';
  return value.replace(/[\r\n\0]/gu, ' ').slice(0, 128);
}


export function locatorDescriptor(request) {
  if (!request || typeof request.locatorRole !== 'string') {
    throw adapterError('LOCATOR_REQUIRED');
  }
  return {
    role: request.locatorRole,
    name: typeof request.locatorName === 'string' ? request.locatorName : undefined,
  };
}


export async function closeAdapterResources(resources) {
  let failed = false;
  for (const resource of resources) {
    try {
      await resource?.close?.();
    } catch {
      failed = true;
    }
  }
  if (failed) throw adapterError('ADAPTER_CLOSE_FAILED');
}
