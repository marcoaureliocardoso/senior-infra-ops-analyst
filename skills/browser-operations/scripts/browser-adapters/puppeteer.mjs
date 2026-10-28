import {
  PUPPETEER_CAPABILITIES, adapterError, assertAllowedUrl, assertCurrentOrigin, closeAdapterResources,
  locatorDescriptor, normalizedAllowedOrigins, observedVersion,
  createAdapterLifetime, rethrowLifetime,
} from './common.mjs';
import { normalizeOrigin } from '../browser-contract.mjs';


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
  const live = createAdapterLifetime(options);
  let browser = null;
  let context = null;
  let page = null;
  let opened = false;
  let activeStepOrigin = null;

  function requirePage() {
    live.check();
    if (!opened || !page) throw adapterError('ADAPTER_NOT_OPEN');
    return page;
  }

  function locator(selected, request) {
    live.check();
    const descriptor = locatorDescriptor(request);
    if (typeof selected.locator !== 'function' || !/^[a-z][a-z0-9-]*$/u.test(descriptor.role)) {
      throw adapterError('SEMANTIC_LOCATOR_UNAVAILABLE');
    }
    // The supported aria/ prefix avoids a second CSS parser. Puppeteer's ARIA
    // handler preserves attribute values literally (it does not unescape them).
    // Choose an absent delimiter; never strip or rewrite an accessible name.
    let name = '';
    if (descriptor.name !== undefined) {
      const quote = descriptor.name.includes('"') ? "'" : '"';
      if (descriptor.name.includes(quote) || /[\r\n\0]/u.test(descriptor.name)) {
        throw adapterError('SEMANTIC_LOCATOR_UNAVAILABLE');
      }
      name = `[name=${quote}${descriptor.name}${quote}]`;
    }
    const found = selected.locator(`aria/[role="${descriptor.role}"]${name}`);
    if (live.lifetime && typeof found.setTimeout === 'function') {
      live.check();
      return found.setTimeout(live.timeout());
    }
    return found;
  }

  function topLevelNavigation(runtimeRequest) {
    if (typeof runtimeRequest?.isNavigationRequest === 'function'
        && runtimeRequest.isNavigationRequest() !== true) return false;
    const frame = runtimeRequest?.frame?.();
    if (frame && typeof page?.mainFrame === 'function' && frame !== page.mainFrame()) return false;
    return true;
  }

  async function withBoundPageOrigin(request, action) {
    if (activeStepOrigin !== null) throw adapterError('ADAPTER_OPERATION_IN_PROGRESS');
    const selected = requirePage();
    activeStepOrigin = assertCurrentOrigin(selected, request.origin);
    try {
      const result = await action(selected);
      live.check();
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

  async function withElementHandle(selected, request, action) {
    live.check();
    // Retain the acquired handle even when the await crosses the deadline, so
    // cleanup still disposes it without authorizing another browser action.
    const handle = await selected.waitHandle();
    try {
      live.check();
      assertCurrentOrigin(requirePage(), request.origin);
      return await live.dispatch(() => action(handle));
    } finally {
      await handle.dispose();
    }
  }

  async function withNavigationOrigin(request, action) {
    if (activeStepOrigin !== null) throw adapterError('ADAPTER_OPERATION_IN_PROGRESS');
    const selected = requirePage();
    const destination = assertAllowedUrl(request.origin, allowedOrigins);
    activeStepOrigin = normalizeOrigin(destination);
    try {
      const result = await action(selected, destination);
      live.check();
      assertCurrentOrigin(selected, request.origin);
      return result;
    } finally {
      activeStepOrigin = null;
    }
  }

  const adapter = {
    id: options.id ?? 'puppeteer',
    observedVersion: observedVersion(runtime),
    operationLifetime: live.lifetime,
    capabilities: Object.freeze({ ...PUPPETEER_CAPABILITIES, operationLifetime: live.lifetime !== null }),
    async open() {
      live.check();
      if (opened) return { status: 'ok', observation: 'adapter-already-open' };
      try {
        live.check();
        browser = await runtime.launch({ headless: true,
          ...(live.lifetime ? { timeout: live.timeout() } : {}) });
        live.check();
        const createContext = browser.createBrowserContext ?? browser.createIncognitoBrowserContext;
        if (typeof createContext !== 'function') throw adapterError('EPHEMERAL_CONTEXT_UNAVAILABLE');
        context = await createContext.call(browser);
        live.check();
        page = await context.newPage();
        live.check();
        if (live.lifetime) {
          page.setDefaultTimeout?.(live.timeout());
          live.check();
          page.setDefaultNavigationTimeout?.(live.timeout());
          live.check();
        }
        await page.setRequestInterception(true);
        live.check();
        page.on('request', async (request) => {
          try {
            live.check();
            assertAllowedUrl(request.url(), allowedOrigins);
            if (activeStepOrigin !== null && topLevelNavigation(request)) {
              assertAllowedUrl(request.url(), new Set([activeStepOrigin]));
            }
            await live.dispatch(() => request.continue());
          } catch {
            await request.abort();
          }
        });
        browser.on('targetcreated', async (target) => {
          if (target.type() === 'page') await (await target.page())?.close?.().catch(() => {});
        });
        opened = true;
        return { status: 'ok', observation: 'ephemeral-context-open' };
      } catch (error) {
        try {
          await closeAdapterResources([page, context, browser]);
        } finally {
          page = null; context = null; browser = null; opened = false;
        }
        rethrowLifetime(error);
        throw adapterError('ADAPTER_OPEN_FAILED');
      }
    },
    async inspect(request) {
      if (request.origin) {
        await withNavigationOrigin(request, (selected, destination) =>
          live.dispatch(() => selected.goto(destination, { waitUntil: 'domcontentloaded', timeout: live.timeout() })));
      }
      await withBoundOrigin(request, (selected) => withElementHandle(selected, request,
        (handle) => handle.evaluate((element) => element.textContent)));
      return { status: 'ok', observation: 'element-present' };
    },
    async navigate(request) {
      await withNavigationOrigin(request, (selected, destination) =>
        live.dispatch(() => selected.goto(destination, { waitUntil: 'domcontentloaded', timeout: live.timeout() })));
      return { status: 'ok', observation: 'navigation-complete' };
    },
    async fill(request) { await withBoundOrigin(request, (selected) => live.dispatch(() => selected.fill(request.credential))); return { status: 'ok', observation: 'field-filled' }; },
    async select(request) { await withBoundOrigin(request, (selected) => live.dispatch(() => selected.fill(request.credential))); return { status: 'ok', observation: 'option-selected' }; },
    async click(request) { await withBoundOrigin(request, (selected) => live.dispatch(() => selected.click())); return { status: 'ok', observation: 'control-clicked' }; },
    async submit(request) { await withBoundOrigin(request, (selected) => live.dispatch(() => selected.click())); return { status: 'ok', observation: 'form-submitted' }; },
    async upload(request) {
      if (!artifactManager) throw adapterError('ARTIFACT_POLICY_REQUIRED');
      await withBoundOrigin(request, async (selected) => {
        const materialized = await live.dispatch(() => artifactManager.materialize(request.artifactRef));
        await withElementHandle(selected, request, (handle) => handle.uploadFile(materialized));
      });
      return { status: 'ok', observation: 'upload-staged' };
    },
    async download() { throw adapterError('DOWNLOAD_DEFAULT_DENIED'); },
    async screenshot(request) {
      if (!artifactManager) throw adapterError('ARTIFACT_POLICY_REQUIRED');
      const data = await withBoundPageOrigin(request, (selectedPage) =>
        live.dispatch(() => selectedPage.screenshot({ type: 'png' })));
      const handle = await live.dispatch(() => artifactManager.capture({
        type: 'screenshot', sourceClass: 'browser-viewport', destinationClass: 'operation-temp',
        mimeType: 'image/png', data,
      }));
      return { status: 'ok', observation: handle.artifactId };
    },
    async trace() { throw adapterError('TRACE_NOT_ACTIVE'); },
    async validate(request) { return adapter.inspect({ ...request, locatorRole: 'status' }); },
    async verify(request) {
      const met = await withBoundOrigin(request, async (selected) => {
        if (!['present', 'text-equals', 'value-equals', 'selected-value-equals', 'checked'].includes(request.predicate)) {
          throw adapterError('INVALID_PREDICATE');
        }
        return withElementHandle(selected, request, async (handle) => {
          if (request.predicate === 'present') return true;
          const value = request.predicate === 'text-equals'
            ? await handle.evaluate((element) => element.textContent)
            : request.predicate === 'checked'
              ? await handle.evaluate((element) => element.checked)
              : await handle.evaluate((element) => element.value);
          if (request.predicate === 'checked') return typeof value === 'boolean' && String(value) === request.expected;
          if (request.predicate !== 'text-equals') return typeof value === 'string' && value === request.expected;
          return String(value ?? '') === request.expected;
        });
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
