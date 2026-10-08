import {
  ADAPTER_CAPABILITIES, adapterError, assertAllowedUrl, assertCurrentOrigin, closeAdapterResources,
  locatorDescriptor, normalizedAllowedOrigins, observedVersion,
  createAdapterLifetime, rethrowLifetime, lifetimeFailureCode,
} from './common.mjs';
import { normalizeOrigin } from '../browser-contract.mjs';


const SPECIFIERS = Object.freeze(['playwright', 'playwright-core']);
const DEFAULT_OPERATION_TIMEOUT_MS = 30_000;
const REDIRECT_FETCH_MINIMUM = Object.freeze([1, 31, 0]);
const FETCH_TIMEOUT_MINIMUM = Object.freeze([1, 33, 0]);
const TRUSTED_ACTION_FAILURES = new Set([
  'ORIGIN_ESCAPE', 'ORIGIN_UNPROVEN', 'TOOL_TIMEOUT', 'BROWSER_CRASH',
  'DOWNLOAD_DEFAULT_DENIED', 'ARTIFACT_POLICY_REQUIRED', 'ARTIFACT_BYTE_LIMIT',
  'ARTIFACT_DATA_INVALID', 'ARTIFACT_DESTINATION_FORBIDDEN',
  'ARTIFACT_DIRECTORY_UNSAFE', 'ARTIFACT_HANDLE_UNKNOWN', 'ARTIFACT_ITEM_LIMIT',
  'ARTIFACT_MANAGER_CLOSED', 'ARTIFACT_MIME_FORBIDDEN', 'ARTIFACT_OPTIONS_INVALID',
  'ARTIFACT_PATH_ESCAPE', 'ARTIFACT_POLICY_INVALID', 'ARTIFACT_REDACTION_UNPROVEN',
  'ARTIFACT_REDACTOR_REQUIRED', 'ARTIFACT_RETENTION_UNAVAILABLE',
  'ARTIFACT_ROOT_UNSAFE', 'ARTIFACT_SOURCE_FORBIDDEN', 'ARTIFACT_TYPE_FORBIDDEN',
]);


function runtimeValue(module) {
  return module?.chromium ? module : module?.default;
}


function supportsRedirectFetch(version, minimum = REDIRECT_FETCH_MINIMUM) {
  const match = /^(\d+)\.(\d+)\.(\d+)(?:\+[0-9A-Za-z.-]+)?$/u.exec(version);
  if (!match) return false;
  const observed = match.slice(1).map(Number);
  for (let index = 0; index < minimum.length; index += 1) {
    if (observed[index] !== minimum[index]) {
      return observed[index] > minimum[index];
    }
  }
  return true;
}


async function detectedVersion(imported, specifier, importModule) {
  const direct = observedVersion(imported);
  if (direct !== 'unknown') return direct;
  try {
    const metadata = await importModule(`${specifier}/package.json`, { with: { type: 'json' } });
    return observedVersion(metadata);
  } catch {
    return 'unknown';
  }
}


export async function detectPlaywright(importModule = (specifier, options) => import(specifier, options)) {
  let unrecognized = null;
  for (const specifier of SPECIFIERS) {
    try {
      const imported = await importModule(specifier);
      const runtime = runtimeValue(imported);
      if (runtime?.chromium && typeof runtime.chromium.launch === 'function') {
        const version = await detectedVersion(imported, specifier, importModule);
        if (supportsRedirectFetch(version)) {
          return Object.freeze({
            state: 'AVAILABLE_RECOGNIZED', id: specifier, observedVersion: version,
            runtime: Object.freeze({ chromium: runtime.chromium, version }),
          });
        }
        unrecognized ??= Object.freeze({
          state: 'AVAILABLE_UNRECOGNIZED', id: specifier,
          observedVersion: version, runtime: null,
        });
      }
    } catch {
      // Optional runtime absence is an observed capability state.
    }
  }
  return unrecognized ?? Object.freeze({
    state: 'UNAVAILABLE', id: null, observedVersion: null, runtime: null,
  });
}


export async function createPlaywrightAdapter(runtime, options = {}) {
  if (!runtime?.chromium || typeof runtime.chromium.launch !== 'function') {
    throw adapterError('ADAPTER_RUNTIME_INVALID');
  }
  if (!supportsRedirectFetch(observedVersion(runtime))) {
    throw adapterError('ADAPTER_RUNTIME_UNSUPPORTED');
  }
  const allowedOrigins = normalizedAllowedOrigins(options.allowedOrigins);
  const artifactManager = options.artifactManager ?? null;
  const live = createAdapterLifetime(options, DEFAULT_OPERATION_TIMEOUT_MS);
  let browser = null;
  let context = null;
  let page = null;
  let opened = false;
  let activeStepOrigin = null;
  let activeRouteFailureCode = null;

  function requirePage() {
    live.check();
    if (!opened || !page) throw adapterError('ADAPTER_NOT_OPEN');
    return page;
  }

  function locator(selected, request) {
    live.check();
    const descriptor = locatorDescriptor(request);
    if (typeof selected.getByRole !== 'function') throw adapterError('SEMANTIC_LOCATOR_UNAVAILABLE');
    return selected.getByRole(descriptor.role, descriptor.name === undefined ? {} : { name: descriptor.name });
  }

  function denyUnmanagedArtifactDispatch(request) {
    if (request?.effect === 'SENSITIVE_ARTIFACT' && !artifactManager) {
      throw adapterError('DOWNLOAD_DEFAULT_DENIED');
    }
  }

  function topLevelNavigation(runtimeRequest) {
    if (typeof runtimeRequest?.isNavigationRequest === 'function'
        && runtimeRequest.isNavigationRequest() !== true) return false;
    try {
      const frame = runtimeRequest?.frame?.();
      if (!frame) return true;
      if (typeof page?.mainFrame === 'function') return frame === page.mainFrame();
      return typeof frame.page !== 'function' || frame.page() === page;
    } catch {
      return true;
    }
  }

  function belongsToPrimaryPage(runtimeRequest) {
    try {
      const frame = runtimeRequest?.frame?.();
      return Boolean(page && frame && typeof frame.page === 'function' && frame.page() === page);
    } catch {
      return false;
    }
  }

  async function withBoundPageOrigin(request, action) {
    if (activeStepOrigin !== null) throw adapterError('ADAPTER_OPERATION_IN_PROGRESS');
    const selected = requirePage();
    activeRouteFailureCode = null;
    activeStepOrigin = assertCurrentOrigin(selected, request.origin);
    try {
      const result = await action(selected);
      live.check();
      if (activeRouteFailureCode !== null) throw adapterError(activeRouteFailureCode);
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
      try {
        return await action(selectedLocator, selected);
      } catch (error) {
        rethrowLifetime(error);
        if (activeRouteFailureCode !== null) throw adapterError(activeRouteFailureCode);
        const code = typeof error?.code === 'string' ? error.code : null;
        if (code !== null && TRUSTED_ACTION_FAILURES.has(code)) throw adapterError(code);
        if (error?.name === 'TimeoutError') throw adapterError('UI_DRIFT');
        throw adapterError('ADAPTER_ACTION_FAILED');
      }
    });
  }

  async function withNavigationOrigin(request, action) {
    if (activeStepOrigin !== null) throw adapterError('ADAPTER_OPERATION_IN_PROGRESS');
    const selected = requirePage();
    const destination = assertAllowedUrl(request.origin, allowedOrigins);
    activeStepOrigin = normalizeOrigin(destination);
    activeRouteFailureCode = null;
    try {
      let result;
      try {
        result = await action(selected, destination);
      } catch (error) {
        rethrowLifetime(error);
        throw adapterError(activeRouteFailureCode ?? 'ADAPTER_NAVIGATION_FAILED');
      }
      live.check();
      if (activeRouteFailureCode !== null) throw adapterError(activeRouteFailureCode);
      assertCurrentOrigin(selected, request.origin);
      return result;
    } finally {
      activeStepOrigin = null;
    }
  }

  const adapter = {
    id: options.id ?? 'playwright',
    observedVersion: observedVersion(runtime),
    operationLifetime: live.lifetime,
    capabilities: Object.freeze({ ...ADAPTER_CAPABILITIES, operationLifetime: live.lifetime !== null }),
    async open() {
      live.check();
      if (opened) return { status: 'ok', observation: 'adapter-already-open' };
      try {
        live.check();
        browser = await runtime.chromium.launch({ headless: true,
          ...(live.lifetime ? { timeout: live.timeout() } : {}) });
        live.check();
        context = await browser.newContext({
          acceptDownloads: false, serviceWorkers: 'block', storageState: undefined,
        });
        live.check();
        context.setDefaultTimeout?.(live.timeout());
        live.check();
        context.setDefaultNavigationTimeout?.(live.timeout());
        live.check();
        await context.route('**/*', async (route) => {
          try { live.check(); } catch (error) {
            activeRouteFailureCode = error.code;
            await route.abort().catch(() => {});
            return;
          }
          const runtimeRequest = route.request();
          const requestUrl = runtimeRequest.url();
          const isTopLevel = topLevelNavigation(runtimeRequest);
          if (!belongsToPrimaryPage(runtimeRequest)) {
            await route.abort();
            return;
          }
          try {
            assertAllowedUrl(requestUrl, allowedOrigins);
            if (activeStepOrigin !== null && isTopLevel) {
              assertAllowedUrl(requestUrl, new Set([activeStepOrigin]));
            }
          } catch {
            if (isTopLevel) activeRouteFailureCode = 'ORIGIN_ESCAPE';
            await route.abort();
            return;
          }
          if (isTopLevel && typeof route.fetch === 'function' && typeof route.fulfill === 'function') {
            let response = null;
            try {
              live.check();
              response = await route.fetch({ maxRedirects: 0,
                ...(live.lifetime && supportsRedirectFetch(observedVersion(runtime), FETCH_TIMEOUT_MINIMUM)
                  ? { timeout: live.timeout() } : {}) });
              live.check();
              const headers = response.headers();
              const location = headers.location;
              const disposition = headers['content-disposition'];
              if (typeof disposition === 'string' && /^\s*attachment(?:\s*;|\s*$)/iu.test(disposition)) {
                activeRouteFailureCode = 'DOWNLOAD_DEFAULT_DENIED';
                await route.abort();
                return;
              }
              if (location) {
                const redirected = new URL(location, requestUrl).href;
                try {
                  assertAllowedUrl(redirected, allowedOrigins);
                  if (activeStepOrigin !== null) {
                    assertAllowedUrl(redirected, new Set([activeStepOrigin]));
                  }
                } catch {
                  activeRouteFailureCode = 'ORIGIN_ESCAPE';
                  await route.abort();
                  return;
                }
              }
              await live.dispatch(() => route.fulfill({ response }));
              return;
            } catch (error) {
              const reason = lifetimeFailureCode(error);
              if (reason !== null) activeRouteFailureCode = reason;
              await route.abort().catch(() => {});
              return;
            } finally {
              await response?.dispose?.().catch(() => {});
            }
          }
          try {
            await live.dispatch(() => route.continue());
          } catch (error) {
            const reason = lifetimeFailureCode(error);
            if (reason !== null) activeRouteFailureCode = reason;
            await route.abort().catch(() => {});
          }
        });
        live.check();
        page = await context.newPage();
        live.check();
        context.on('page', async (popup) => { await popup.close().catch(() => {}); });
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
      await withBoundOrigin(request, (selected) => live.dispatch(() => selected.textContent({ timeout: live.timeout() })));
      return { status: 'ok', observation: 'element-present' };
    },
    async navigate(request) {
      denyUnmanagedArtifactDispatch(request);
      await withNavigationOrigin(request, (selected, destination) =>
        live.dispatch(() => selected.goto(destination, { waitUntil: 'domcontentloaded', timeout: live.timeout() })));
      return { status: 'ok', observation: 'navigation-complete' };
    },
    async fill(request) {
      await withBoundOrigin(request, (selected) => live.dispatch(() => selected.fill(request.credential, { timeout: live.timeout() })));
      return { status: 'ok', observation: 'field-filled' };
    },
    async select(request) {
      await withBoundOrigin(request, (selected) => live.dispatch(() => selected.selectOption(request.credential, { timeout: live.timeout() })));
      return { status: 'ok', observation: 'option-selected' };
    },
    async click(request) {
      denyUnmanagedArtifactDispatch(request);
      await withBoundOrigin(request, async (selected) => {
        if (request.locatorRole === 'link' && typeof selected.getAttribute === 'function'
            && await live.dispatch(() => selected.getAttribute('download', { timeout: live.timeout() })) !== null) {
          throw adapterError('DOWNLOAD_DEFAULT_DENIED');
        }
        await live.dispatch(() => selected.click({ timeout: live.timeout() }));
      });
      return { status: 'ok', observation: 'control-clicked' };
    },
    async submit(request) {
      denyUnmanagedArtifactDispatch(request);
      await withBoundOrigin(request, (selected) => live.dispatch(() => selected.click({ timeout: live.timeout() })));
      return { status: 'ok', observation: 'form-submitted' };
    },
    async upload(request) {
      if (!artifactManager) throw adapterError('ARTIFACT_POLICY_REQUIRED');
      await withBoundOrigin(request, async (selected) => {
        const materialized = await live.dispatch(() => artifactManager.materialize(request.artifactRef));
        await live.dispatch(() => selected.setInputFiles(materialized, { timeout: live.timeout() }));
      });
      return { status: 'ok', observation: 'upload-staged' };
    },
    async download() { throw adapterError('DOWNLOAD_DEFAULT_DENIED'); },
    async screenshot(request) {
      if (!artifactManager) throw adapterError('ARTIFACT_POLICY_REQUIRED');
      const data = await withBoundPageOrigin(request, (selectedPage) =>
        live.dispatch(() => selectedPage.screenshot({ type: 'png', timeout: live.timeout() })));
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
          await live.dispatch(() => selected.textContent({ timeout: live.timeout() }));
          return true;
        }
        if (request.predicate === 'text-equals') {
          return String(await live.dispatch(() => selected.textContent({ timeout: live.timeout() })) ?? '') === request.expected;
        }
        if (['value-equals', 'selected-value-equals'].includes(request.predicate)) {
          if (typeof selected.inputValue !== 'function') throw adapterError('VERIFY_UNSUPPORTED');
          return String(await live.dispatch(() => selected.inputValue({ timeout: live.timeout() }))) === request.expected;
        }
        if (request.predicate === 'checked') {
          if (typeof selected.isChecked !== 'function') throw adapterError('VERIFY_UNSUPPORTED');
          return String(await live.dispatch(() => selected.isChecked({ timeout: live.timeout() }))) === request.expected;
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
