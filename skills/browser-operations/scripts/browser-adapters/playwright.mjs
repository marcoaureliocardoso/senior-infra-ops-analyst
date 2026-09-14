import {
  ADAPTER_CAPABILITIES, adapterError, assertAllowedUrl, assertCurrentOrigin, closeAdapterResources,
  locatorDescriptor, normalizedAllowedOrigins, observedVersion,
} from './common.mjs';
import { normalizeOrigin } from '../browser-contract.mjs';


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
  let activeStepOrigin = null;

  function requirePage() {
    if (!opened || !page) throw adapterError('ADAPTER_NOT_OPEN');
    return page;
  }

  function locator(selected, request) {
    const descriptor = locatorDescriptor(request);
    if (typeof selected.getByRole !== 'function') throw adapterError('SEMANTIC_LOCATOR_UNAVAILABLE');
    return selected.getByRole(descriptor.role, descriptor.name === undefined ? {} : { name: descriptor.name });
  }

  function topLevelNavigation(runtimeRequest) {
    if (typeof runtimeRequest?.isNavigationRequest === 'function'
        && runtimeRequest.isNavigationRequest() !== true) return false;
    const frame = runtimeRequest?.frame?.();
    if (frame && typeof frame.page === 'function' && frame.page() !== page) return false;
    if (frame && typeof page?.mainFrame === 'function' && frame !== page.mainFrame()) return false;
    return true;
  }

  async function withBoundPageOrigin(request, action) {
    if (activeStepOrigin !== null) throw adapterError('ADAPTER_OPERATION_IN_PROGRESS');
    const selected = requirePage();
    activeStepOrigin = assertCurrentOrigin(selected, request.origin);
    try {
      const result = await action(selected);
      assertCurrentOrigin(selected, request.origin);
      return result;
    } finally {
      activeStepOrigin = null;
    }
  }

  async function withBoundOrigin(request, action) {
    return withBoundPageOrigin(request, async (selected) => {
      const selectedLocator = locator(selected, request);
      assertCurrentOrigin(selected, request.origin);
      return action(selectedLocator, selected);
    });
  }

  async function withNavigationOrigin(request, action) {
    if (activeStepOrigin !== null) throw adapterError('ADAPTER_OPERATION_IN_PROGRESS');
    const selected = requirePage();
    const destination = assertAllowedUrl(request.origin, allowedOrigins);
    activeStepOrigin = normalizeOrigin(destination);
    try {
      const result = await action(selected, destination);
      assertCurrentOrigin(selected, request.origin);
      return result;
    } finally {
      activeStepOrigin = null;
    }
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
          const runtimeRequest = route.request();
          const requestUrl = runtimeRequest.url();
          try {
            if (!page || runtimeRequest.frame().page() !== page) {
              await route.abort();
              return;
            }
            assertAllowedUrl(requestUrl, allowedOrigins);
            if (activeStepOrigin !== null && topLevelNavigation(runtimeRequest)) {
              assertAllowedUrl(requestUrl, new Set([activeStepOrigin]));
            }
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
      if (request.origin) {
        await withNavigationOrigin(request, (selected, destination) =>
          selected.goto(destination, { waitUntil: 'domcontentloaded' }));
      }
      await withBoundOrigin(request, (selected) => selected.textContent());
      return { status: 'ok', observation: 'element-present' };
    },
    async navigate(request) {
      await withNavigationOrigin(request, (selected, destination) =>
        selected.goto(destination, { waitUntil: 'domcontentloaded' }));
      return { status: 'ok', observation: 'navigation-complete' };
    },
    async fill(request) {
      await withBoundOrigin(request, (selected) => selected.fill(request.credential));
      return { status: 'ok', observation: 'field-filled' };
    },
    async select(request) {
      await withBoundOrigin(request, (selected) => selected.selectOption(request.credential));
      return { status: 'ok', observation: 'option-selected' };
    },
    async click(request) {
      await withBoundOrigin(request, (selected) => selected.click());
      return { status: 'ok', observation: 'control-clicked' };
    },
    async submit(request) {
      await withBoundOrigin(request, (selected) => selected.click());
      return { status: 'ok', observation: 'form-submitted' };
    },
    async upload(request) {
      if (!artifactManager) throw adapterError('ARTIFACT_POLICY_REQUIRED');
      await withBoundOrigin(request, (selected) =>
        selected.setInputFiles(artifactManager.materialize(request.artifactRef)));
      return { status: 'ok', observation: 'upload-staged' };
    },
    async download() { throw adapterError('DOWNLOAD_DEFAULT_DENIED'); },
    async screenshot(request) {
      if (!artifactManager) throw adapterError('ARTIFACT_POLICY_REQUIRED');
      const data = await withBoundPageOrigin(request, (selectedPage) =>
        selectedPage.screenshot({ type: 'png' }));
      const handle = await artifactManager.capture({
        type: 'screenshot', sourceClass: 'browser-viewport', destinationClass: 'operation-temp',
        mimeType: 'image/png', data,
      });
      return { status: 'ok', observation: handle.artifactId };
    },
    async trace() { throw adapterError('TRACE_NOT_ACTIVE'); },
    async validate(request) { return adapter.inspect({ ...request, locatorRole: 'status' }); },
    async verify(request) {
      const met = await withBoundOrigin(request, async (selected) => {
        if (request.predicate === 'present') {
          await selected.textContent();
          return true;
        }
        if (request.predicate === 'text-equals') {
          return String(await selected.textContent() ?? '') === request.expected;
        }
        if (['value-equals', 'selected-value-equals'].includes(request.predicate)) {
          if (typeof selected.inputValue !== 'function') throw adapterError('VERIFY_UNSUPPORTED');
          return String(await selected.inputValue()) === request.expected;
        }
        if (request.predicate === 'checked') {
          if (typeof selected.isChecked !== 'function') throw adapterError('VERIFY_UNSUPPORTED');
          return String(await selected.isChecked()) === request.expected;
        }
        throw adapterError('INVALID_PREDICATE');
      });
      return { status: met ? 'met' : 'not-met', expectRef: request.expectRef };
    },
    async close() {
      const selectedPage = page; const selectedContext = context; const selectedBrowser = browser;
      page = null; context = null; browser = null; opened = false; activeStepOrigin = null;
      await closeAdapterResources([selectedPage, selectedContext, selectedBrowser]);
    },
  };
  return Object.freeze(adapter);
}
