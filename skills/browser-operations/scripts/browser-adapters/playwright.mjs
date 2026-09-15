import {
  ADAPTER_CAPABILITIES, adapterError, assertAllowedUrl, assertCurrentOrigin, closeAdapterResources,
  locatorDescriptor, normalizedAllowedOrigins, observedVersion,
} from './common.mjs';
import { normalizeOrigin } from '../browser-contract.mjs';


const SPECIFIERS = Object.freeze(['playwright', 'playwright-core']);
const DEFAULT_OPERATION_TIMEOUT_MS = 30_000;
const REDIRECT_FETCH_MINIMUM = Object.freeze([1, 31, 0]);
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


function supportsRedirectFetch(version) {
  const match = /^(\d+)\.(\d+)\.(\d+)(?:\+[0-9A-Za-z.-]+)?$/u.exec(version);
  if (!match) return false;
  const observed = match.slice(1).map(Number);
  for (let index = 0; index < REDIRECT_FETCH_MINIMUM.length; index += 1) {
    if (observed[index] !== REDIRECT_FETCH_MINIMUM[index]) {
      return observed[index] > REDIRECT_FETCH_MINIMUM[index];
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
  let browser = null;
  let context = null;
  let page = null;
  let opened = false;
  let activeStepOrigin = null;
  let activeRouteFailureCode = null;

  function requirePage() {
    if (!opened || !page) throw adapterError('ADAPTER_NOT_OPEN');
    return page;
  }

  function locator(selected, request) {
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
      } catch {
        throw adapterError(activeRouteFailureCode ?? 'ADAPTER_NAVIGATION_FAILED');
      }
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
    capabilities: ADAPTER_CAPABILITIES,
    async open() {
      if (opened) return { status: 'ok', observation: 'adapter-already-open' };
      try {
        browser = await runtime.chromium.launch({ headless: true });
        context = await browser.newContext({
          acceptDownloads: false, serviceWorkers: 'block', storageState: undefined,
        });
        context.setDefaultTimeout?.(DEFAULT_OPERATION_TIMEOUT_MS);
        context.setDefaultNavigationTimeout?.(DEFAULT_OPERATION_TIMEOUT_MS);
        await context.route('**/*', async (route) => {
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
              response = await route.fetch({ maxRedirects: 0 });
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
              await route.fulfill({ response });
              return;
            } catch {
              await route.abort().catch(() => {});
              return;
            } finally {
              await response?.dispose?.().catch(() => {});
            }
          }
          try {
            await route.continue();
          } catch {
            await route.abort().catch(() => {});
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
      denyUnmanagedArtifactDispatch(request);
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
      denyUnmanagedArtifactDispatch(request);
      await withBoundOrigin(request, async (selected) => {
        if (request.locatorRole === 'link' && typeof selected.getAttribute === 'function'
            && await selected.getAttribute('download') !== null) {
          throw adapterError('DOWNLOAD_DEFAULT_DENIED');
        }
        await selected.click();
      });
      return { status: 'ok', observation: 'control-clicked' };
    },
    async submit(request) {
      denyUnmanagedArtifactDispatch(request);
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
