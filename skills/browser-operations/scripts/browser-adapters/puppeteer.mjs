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
    let found;
    if (typeof selected.getByRole === 'function') {
      found = selected.getByRole(descriptor.role, descriptor.name === undefined ? {} : { name: descriptor.name });
    } else if (typeof selected.locator === 'function') {
      const name = descriptor.name === undefined ? '' : `[name="${descriptor.name.replace(/["\\]/gu, '')}"]`;
      found = selected.locator(`::-p-aria(${descriptor.role}${name})`);
    } else {
      throw adapterError('SEMANTIC_LOCATOR_UNAVAILABLE');
    }
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
      await withBoundOrigin(request, async (selected) => {
        if (typeof selected.evaluate === 'function') {
          await live.dispatch(() => selected.evaluate((element) => element.textContent));
        } else {
          await live.dispatch(() => selected.textContent());
        }
      });
      return { status: 'ok', observation: 'element-present' };
    },
    async navigate(request) {
      await withNavigationOrigin(request, (selected, destination) =>
        live.dispatch(() => selected.goto(destination, { waitUntil: 'domcontentloaded', timeout: live.timeout() })));
      return { status: 'ok', observation: 'navigation-complete' };
    },
    async fill(request) { await withBoundOrigin(request, (selected) => live.dispatch(() => selected.fill(request.credential))); return { status: 'ok', observation: 'field-filled' }; },
    async select(request) { await withBoundOrigin(request, (selected) => live.dispatch(() => selected.select(request.credential))); return { status: 'ok', observation: 'option-selected' }; },
    async click(request) { await withBoundOrigin(request, (selected) => live.dispatch(() => selected.click())); return { status: 'ok', observation: 'control-clicked' }; },
    async submit(request) { await withBoundOrigin(request, (selected) => live.dispatch(() => selected.click())); return { status: 'ok', observation: 'form-submitted' }; },
    async upload(request) {
      if (!artifactManager) throw adapterError('ARTIFACT_POLICY_REQUIRED');
      await withBoundOrigin(request, async (selected) => {
        const materialized = await live.dispatch(() => artifactManager.materialize(request.artifactRef));
        await live.dispatch(() => selected.uploadFile(materialized));
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
        if (request.predicate === 'present') {
          if (typeof selected.textContent === 'function') await live.dispatch(() => selected.textContent());
          else await live.dispatch(() => selected.evaluate((element) => element.textContent));
          return true;
        }
        if (request.predicate === 'text-equals') {
          const value = typeof selected.textContent === 'function'
            ? await live.dispatch(() => selected.textContent())
            : await live.dispatch(() => selected.evaluate((element) => element.textContent));
          return String(value ?? '') === request.expected;
        }
        if (['value-equals', 'selected-value-equals'].includes(request.predicate)) {
          if (typeof selected.inputValue !== 'function') throw adapterError('VERIFY_UNSUPPORTED');
          return String(await live.dispatch(() => selected.inputValue())) === request.expected;
        }
        if (request.predicate === 'checked') {
          if (typeof selected.isChecked !== 'function') throw adapterError('VERIFY_UNSUPPORTED');
          return String(await live.dispatch(() => selected.isChecked())) === request.expected;
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
