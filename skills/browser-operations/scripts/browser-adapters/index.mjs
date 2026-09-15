import { createPlaywrightAdapter, detectPlaywright } from './playwright.mjs';
import { createPuppeteerAdapter, detectPuppeteer } from './puppeteer.mjs';


export async function resolveBrowserAdapter({
  importModule = (specifier, importOptions) => import(specifier, importOptions),
  preference = null, options = {},
} = {}) {
  const [playwright, puppeteer] = await Promise.all([
    detectPlaywright(importModule), detectPuppeteer(importModule),
  ]);
  const available = [playwright, puppeteer].filter((candidate) => candidate.state === 'AVAILABLE_RECOGNIZED');
  if (available.length === 0) {
    const unrecognized = [playwright, puppeteer]
      .find((candidate) => candidate.state === 'AVAILABLE_UNRECOGNIZED');
    if (unrecognized) {
      return Object.freeze({
        state: 'AVAILABLE_UNRECOGNIZED', reasonCode: 'CAPABILITY_UNRECOGNIZED',
        observedVersion: unrecognized.observedVersion, adapter: null,
      });
    }
    return Object.freeze({ state: 'UNAVAILABLE', reasonCode: 'CAPABILITY_UNAVAILABLE', adapter: null });
  }
  const family = preference === 'playwright' ? 'playwright'
    : preference === 'puppeteer' ? 'puppeteer' : null;
  if (available.length > 1 && family === null) {
    return Object.freeze({ state: 'CONFLICT', reasonCode: 'CAPABILITY_CONFLICT', adapter: null });
  }
  const selected = family === null ? available[0]
    : available.find((candidate) => candidate.id.startsWith(family));
  if (!selected) {
    return Object.freeze({ state: 'CONFLICT', reasonCode: 'CAPABILITY_CONFLICT', adapter: null });
  }
  const adapter = selected.id.startsWith('playwright')
    ? await createPlaywrightAdapter(selected.runtime, { ...options, id: selected.id })
    : await createPuppeteerAdapter(selected.runtime, { ...options, id: selected.id });
  return Object.freeze({
    state: 'ACTIVE', reasonCode: 'CAPABILITY_ACTIVE',
    observedVersion: selected.observedVersion, adapter,
  });
}
