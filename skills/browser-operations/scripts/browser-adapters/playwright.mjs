import {
  ADAPTER_CAPABILITIES, adapterError, assertAllowedUrl,
  locatorDescriptor, normalizedAllowedOrigins, observedVersion,
} from './common.mjs';


const SPECIFIERS = Object.freeze(['playwright', 'playwright-core']);


function runtimeValue(module) {
  return module?.chromium ? module : module?.default;
}


export async function detectPlaywright(importModule = (specifier) => import(specifier)) {
  for (const specifier of SPECIFIERS) {
    try {
      const imported = await importModule(specifier);
      const runtime = runtimeValue(imported);
      if (runtime?.chromium && typeof runtime.chromium.launch === 'function') {
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


export async function createPlaywrightAdapter(runtime, options = {}) {
  if (!runtime?.chromium || typeof runtime.chromium.launch !== 'function') {
    throw adapterError('ADAPTER_RUNTIME_INVALID');
  }
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
    if (typeof selected.getByRole !== 'function') throw adapterError('SEMANTIC_LOCATOR_UNAVAILABLE');
    return selected.getByRole(descriptor.role, descriptor.name === undefined ? {} : { name: descriptor.name });
  }

  const adapter = {
    id: options.id ?? 'playwright',
    observedVersion: observedVersion(runtime),
    capabilities: ADAPTER_CAPABILITIES,
    async open() {
      if (opened) return { status: 'ok', observation: 'adapter-already-open' };
      try {
        browser = await runtime.chromium.launch({ headless: true });
        context = await browser.newContext({ acceptDownloads: false, storageState: undefined });
        await context.route('**/*', async (route) => {
          const requestUrl = route.request().url();
          try {
            if (!page || route.request().frame().page() !== page) {
              await route.abort();
              return;
            }
            assertAllowedUrl(requestUrl, allowedOrigins);
            await route.continue();
          } catch {
            await route.abort();
          }
        });
        page = await context.newPage();
        context.on('page', async (popup) => { await popup.close().catch(() => {}); });
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
      await locator(request).textContent();
      return { status: 'ok', observation: 'element-present' };
    },
    async navigate(request) {
      const destination = assertAllowedUrl(request.origin, allowedOrigins);
      await requirePage().goto(destination, { waitUntil: 'domcontentloaded' });
      return { status: 'ok', observation: 'navigation-complete' };
    },
    async fill(request) {
      await locator(request).fill(request.credential);
      return { status: 'ok', observation: 'field-filled' };
    },
    async select(request) {
      await locator(request).selectOption(request.credential);
      return { status: 'ok', observation: 'option-selected' };
    },
    async click(request) {
      await locator(request).click();
      return { status: 'ok', observation: 'control-clicked' };
    },
    async submit(request) {
      await locator(request).click();
      return { status: 'ok', observation: 'form-submitted' };
    },
    async upload(request) {
      if (!artifactManager) throw adapterError('ARTIFACT_POLICY_REQUIRED');
      await locator(request).setInputFiles(artifactManager.materialize(request.artifactRef));
      return { status: 'ok', observation: 'upload-staged' };
    },
    async download() { throw adapterError('DOWNLOAD_DEFAULT_DENIED'); },
    async screenshot(request) {
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
