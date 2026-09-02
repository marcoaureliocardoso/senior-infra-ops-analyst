import {
  PUPPETEER_CAPABILITIES, adapterError, assertAllowedUrl,
  locatorDescriptor, normalizedAllowedOrigins, observedVersion,
} from './common.mjs';


const SPECIFIERS = Object.freeze(['puppeteer', 'puppeteer-core']);


function runtimeValue(module) {
  return typeof module?.launch === 'function' ? module : module?.default;
}


export async function detectPuppeteer(importModule = (specifier) => import(specifier)) {
  for (const specifier of SPECIFIERS) {
    try {
      const imported = await importModule(specifier);
      const runtime = runtimeValue(imported);
      if (runtime && typeof runtime.launch === 'function') {
        return Object.freeze({
          state: 'AVAILABLE_RECOGNIZED', id: specifier,
          observedVersion: observedVersion(imported), runtime,
        });
      }
    } catch {
      // Optional runtime absence is an observed capability state.
    }
  }
  return Object.freeze({ state: 'UNAVAILABLE', id: null, observedVersion: null, runtime: null });
}


export async function createPuppeteerAdapter(runtime, options = {}) {
  if (!runtime || typeof runtime.launch !== 'function') throw adapterError('ADAPTER_RUNTIME_INVALID');
  const allowedOrigins = normalizedAllowedOrigins(options.allowedOrigins);
  const artifactManager = options.artifactManager ?? null;
  let browser = null;
  let context = null;
  let page = null;
  let opened = false;

  function requirePage() {
    if (!opened || !page) throw adapterError('ADAPTER_NOT_OPEN');
    return page;
  }

  function locator(request) {
    const selected = requirePage();
    const descriptor = locatorDescriptor(request);
    if (typeof selected.getByRole === 'function') {
      return selected.getByRole(descriptor.role, descriptor.name === undefined ? {} : { name: descriptor.name });
    }
    if (typeof selected.locator === 'function') {
      const name = descriptor.name === undefined ? '' : `[name="${descriptor.name.replace(/["\\]/gu, '')}"]`;
      return selected.locator(`::-p-aria(${descriptor.role}${name})`);
    }
    throw adapterError('SEMANTIC_LOCATOR_UNAVAILABLE');
  }

  const adapter = {
    id: options.id ?? 'puppeteer',
    observedVersion: observedVersion(runtime),
    capabilities: PUPPETEER_CAPABILITIES,
    async open() {
      if (opened) return { status: 'ok', observation: 'adapter-already-open' };
      try {
        browser = await runtime.launch({ headless: true });
        const createContext = browser.createBrowserContext ?? browser.createIncognitoBrowserContext;
        if (typeof createContext !== 'function') throw adapterError('EPHEMERAL_CONTEXT_UNAVAILABLE');
        context = await createContext.call(browser);
        page = await context.newPage();
        await page.setRequestInterception(true);
        page.on('request', async (request) => {
          try {
            assertAllowedUrl(request.url(), allowedOrigins);
            await request.continue();
          } catch {
            await request.abort();
          }
        });
        browser.on('targetcreated', async (target) => {
          if (target.type() === 'page') await (await target.page())?.close?.().catch(() => {});
        });
        opened = true;
        return { status: 'ok', observation: 'ephemeral-context-open' };
      } catch {
        await page?.close?.().catch(() => {});
        await context?.close?.().catch(() => {});
        await browser?.close?.().catch(() => {});
        page = null; context = null; browser = null; opened = false;
        throw adapterError('ADAPTER_OPEN_FAILED');
      }
    },
    async inspect(request) {
      const selected = locator(request);
      if (typeof selected.evaluate === 'function') {
        await selected.evaluate((element) => element.textContent);
      } else {
        await selected.textContent();
      }
      return { status: 'ok', observation: 'element-present' };
    },
    async navigate(request) {
      const destination = assertAllowedUrl(request.origin, allowedOrigins);
      await requirePage().goto(destination, { waitUntil: 'domcontentloaded' });
      return { status: 'ok', observation: 'navigation-complete' };
    },
    async fill(request) { await locator(request).fill(request.credential); return { status: 'ok', observation: 'field-filled' }; },
    async select(request) { await locator(request).select(request.credential); return { status: 'ok', observation: 'option-selected' }; },
    async click(request) { await locator(request).click(); return { status: 'ok', observation: 'control-clicked' }; },
    async submit(request) { await locator(request).click(); return { status: 'ok', observation: 'form-submitted' }; },
    async upload(request) {
      if (!artifactManager) throw adapterError('ARTIFACT_POLICY_REQUIRED');
      await locator(request).uploadFile(artifactManager.materialize(request.artifactRef));
      return { status: 'ok', observation: 'upload-staged' };
    },
    async download() { throw adapterError('DOWNLOAD_DEFAULT_DENIED'); },
    async screenshot() {
      if (!artifactManager) throw adapterError('ARTIFACT_POLICY_REQUIRED');
      const data = await requirePage().screenshot({ type: 'png' });
      const handle = await artifactManager.capture({
        type: 'screenshot', sourceClass: 'browser-viewport', destinationClass: 'operation-temp',
        mimeType: 'image/png', data,
      });
      return { status: 'ok', observation: handle.artifactId };
    },
    async trace() { throw adapterError('TRACE_NOT_ACTIVE'); },
    async validate(request) { return adapter.inspect({ ...request, locatorRole: 'status' }); },
    async close() {
      const selectedPage = page; const selectedContext = context; const selectedBrowser = browser;
      page = null; context = null; browser = null; opened = false;
      await selectedPage?.close?.().catch(() => {});
      await selectedContext?.close?.().catch(() => {});
      await selectedBrowser?.close?.().catch(() => {});
    },
  };
  return Object.freeze(adapter);
}
