import assert from 'node:assert/strict';
import test from 'node:test';
import {
  createOperationClock, createOperationLifetime, hasOperationLifetime,
} from '../../skills/browser-operations/scripts/browser-operation-lifetime.mjs';

import {
  resolveBrowserAdapter,
} from '../../skills/browser-operations/scripts/browser-adapters/index.mjs';
import {
  createPlaywrightAdapter, detectPlaywright,
} from '../../skills/browser-operations/scripts/browser-adapters/playwright.mjs';
import {
  createPuppeteerAdapter, detectPuppeteer,
} from '../../skills/browser-operations/scripts/browser-adapters/puppeteer.mjs';


function playwrightRuntime(version = '1.62.1') {
  const state = {
    launches: [], contexts: [], pages: [], closed: 0, popupClosed: 0,
    currentUrl: 'about:blank', actionTimeout: null, navigationTimeout: null,
  };
  const pageEvents = new Map();
  const contextEvents = new Map();
  const page = {
    url() { return state.currentUrl; },
    on(name, handler) { pageEvents.set(name, handler); },
    async goto(url) {
      let outcome = 'continued';
      await state.contextRoute({
        request: () => ({ url: () => url, frame: () => ({ page: () => page }) }),
        abort: async () => { outcome = 'aborted'; },
        continue: async () => {},
      });
      if (outcome === 'aborted') throw new Error('REQUEST_BLOCKED');
      state.goto = url;
      state.currentUrl = url;
    },
    getByRole(role, options) {
      return {
        async textContent() { state.locator = { role, ...options }; return 'untrusted page text'; },
        async inputValue() { state.locator = { role, ...options }; return 'selected-value'; },
        async isChecked() { state.locator = { role, ...options }; return true; },
        async fill(value) { state.fill = { role, ...options, value }; },
        async selectOption(value) { state.select = { role, ...options, value }; },
        async click() { state.click = { role, ...options }; },
      };
    },
    async screenshot() { state.screenshot = true; return Buffer.from('synthetic-image'); },
    async close() { state.closed += 1; },
  };
  const context = {
    on(name, handler) { contextEvents.set(name, handler); },
    setDefaultTimeout(value) { state.actionTimeout = value; },
    setDefaultNavigationTimeout(value) { state.navigationTimeout = value; },
    async route(_pattern, handler) { state.contextRoute = handler; },
    async newPage() { state.pages.push(page); return page; },
    async close() { state.closed += 1; },
  };
  const browser = {
    async newContext(options) { state.contexts.push(options); return context; },
    async close() { state.closed += 1; },
  };
  const runtime = { version, chromium: { async launch(options) { state.launches.push(options); return browser; } } };
  return {
    runtime, state, contextEvents, pageEvents, resources: { page, context, browser },
  };
}


function puppeteerRuntime() {
  const state = { launches: [], closed: 0, currentUrl: 'about:blank' };
  const pageEvents = new Map();
  const browserEvents = new Map();
  const page = {
    url() { return state.currentUrl; },
    async setRequestInterception(value) { state.interception = value; },
    on(name, handler) { pageEvents.set(name, handler); },
    async goto(url) { state.goto = url; state.currentUrl = url; },
    getByRole(role, options) {
      return {
        async evaluate() { state.locator = { role, ...options }; return 'untrusted page text'; },
        async textContent() { state.locator = { role, ...options }; return 'untrusted page text'; },
        async inputValue() { state.locator = { role, ...options }; return 'selected-value'; },
        async isChecked() { state.locator = { role, ...options }; return true; },
        async fill(value) { state.fill = { role, ...options, value }; },
        async select(value) { state.select = { role, ...options, value }; },
        async click() { state.click = { role, ...options }; },
      };
    },
    async screenshot() { state.screenshot = true; return Buffer.from('synthetic-image'); },
    async close() { state.closed += 1; },
  };
  const context = {
    async newPage() { return page; },
    async close() { state.closed += 1; },
  };
  const browser = {
    on(name, handler) { browserEvents.set(name, handler); },
    async createBrowserContext() { return context; },
    async close() { state.closed += 1; },
  };
  const runtime = { version: '4.5.6', async launch(options) { state.launches.push(options); return browser; } };
  return {
    runtime, state, browserEvents, pageEvents, resources: { page, context, browser },
  };
}


test('runtime detection uses only fixed recognized imports and records observed versions', async () => {
  const attempted = [];
  const detected = await detectPlaywright(async (specifier) => {
    attempted.push(specifier);
    if (specifier === 'playwright-core') return playwrightRuntime().runtime;
    throw new Error('MODULE_NOT_FOUND');
  });
  assert.deepEqual(attempted, ['playwright', 'playwright-core']);
  assert.equal(detected.id, 'playwright-core');
  assert.equal(detected.observedVersion, '1.62.1');
  assert.equal((await detectPuppeteer(async () => { throw new Error('missing'); })).state, 'UNAVAILABLE');
});


test('Playwright redirect interception requires a detected compatible interface', async () => {
  const unsupported = await detectPlaywright(async (specifier) => {
    if (specifier === 'playwright') return playwrightRuntime('1.30.0').runtime;
    throw new Error('MODULE_NOT_FOUND');
  });
  assert.equal(unsupported.state, 'AVAILABLE_UNRECOGNIZED');
  assert.equal(unsupported.observedVersion, '1.30.0');
  await assert.rejects(
    () => createPlaywrightAdapter(playwrightRuntime('1.30.0').runtime, {
      allowedOrigins: ['https://router.example.invalid:443'],
    }),
    (error) => error?.code === 'ADAPTER_RUNTIME_UNSUPPORTED',
  );
  await assert.rejects(
    () => createPlaywrightAdapter(playwrightRuntime('unknown').runtime, {
      allowedOrigins: ['https://router.example.invalid:443'],
    }),
    (error) => error?.code === 'ADAPTER_RUNTIME_UNSUPPORTED',
  );
  await assert.rejects(
    () => createPlaywrightAdapter(playwrightRuntime('1.31.0-beta.1').runtime, {
      allowedOrigins: ['https://router.example.invalid:443'],
    }),
    (error) => error?.code === 'ADAPTER_RUNTIME_UNSUPPORTED',
  );
  assert.equal((await createPlaywrightAdapter(playwrightRuntime('1.31.0').runtime, {
    allowedOrigins: ['https://router.example.invalid:443'],
  })).id, 'playwright');
  assert.equal((await createPlaywrightAdapter(playwrightRuntime('1.31.0+build.7').runtime, {
    allowedOrigins: ['https://router.example.invalid:443'],
  })).id, 'playwright');
  const resolved = await resolveBrowserAdapter({
    preference: 'playwright',
    importModule: async (specifier) => {
      if (specifier === 'playwright') return playwrightRuntime('1.30.0').runtime;
      throw new Error('MODULE_NOT_FOUND');
    },
  });
  assert.equal(resolved.state, 'AVAILABLE_UNRECOGNIZED');
  assert.equal(resolved.adapter, null);
});


test('Playwright detection reads fixed package metadata when the module omits a version', async () => {
  const runtime = playwrightRuntime().runtime;
  delete runtime.version;
  const attempted = [];
  const detected = await detectPlaywright(async (specifier) => {
    attempted.push(specifier);
    if (specifier === 'playwright') return runtime;
    if (specifier === 'playwright/package.json') return { default: { version: '1.62.1' } };
    throw new Error('MODULE_NOT_FOUND');
  });
  assert.deepEqual(attempted, ['playwright', 'playwright/package.json']);
  assert.equal(detected.state, 'AVAILABLE_RECOGNIZED');
  assert.equal(detected.observedVersion, '1.62.1');
});


test('resolver forwards JSON import attributes for fixed Playwright metadata', async () => {
  const runtime = playwrightRuntime().runtime;
  delete runtime.version;
  let metadataOptions = null;
  const resolved = await resolveBrowserAdapter({
    preference: 'playwright',
    options: { allowedOrigins: ['https://router.example.invalid:443'] },
    importModule: async (specifier, importOptions) => {
      if (specifier === 'playwright') return runtime;
      if (specifier === 'playwright/package.json') {
        metadataOptions = importOptions;
        return { default: { version: '1.62.1' } };
      }
      throw new Error('MODULE_NOT_FOUND');
    },
  });
  assert.deepEqual(metadataOptions, { with: { type: 'json' } });
  assert.equal(resolved.state, 'ACTIVE');
  assert.equal(resolved.observedVersion, '1.62.1');
});


test('resolver requires deterministic preference when both recognized runtimes exist', async () => {
  const modules = {
    playwright: playwrightRuntime().runtime,
    puppeteer: puppeteerRuntime().runtime,
  };
  const importModule = async (specifier) => {
    if (modules[specifier]) return modules[specifier];
    throw new Error('missing');
  };
  const options = { allowedOrigins: ['https://router.example.invalid:443'] };
  assert.equal((await resolveBrowserAdapter({ importModule })).state, 'CONFLICT');
  assert.equal((await resolveBrowserAdapter({ importModule, preference: 'playwright', options })).adapter.id, 'playwright');
  assert.equal((await resolveBrowserAdapter({ importModule, preference: 'unknown' })).state, 'CONFLICT');
});


test('Playwright adapter enforces origins requests popups and ephemeral context', async () => {
  const fake = playwrightRuntime();
  const adapter = await createPlaywrightAdapter(fake.runtime, {
    id: 'playwright', allowedOrigins: [
      'https://router.example.invalid:443', 'https://login.example.invalid:443',
    ],
  });
  assert.equal(Object.hasOwn(adapter, 'evaluate'), false);
  await adapter.open();
  assert.deepEqual(fake.state.launches, [{ headless: true }]);
  assert.deepEqual(fake.state.contexts, [{
    acceptDownloads: false, serviceWorkers: 'block', storageState: undefined,
  }]);
  assert.equal(fake.state.actionTimeout, 30_000);
  assert.equal(fake.state.navigationTimeout, 30_000);
  assert.doesNotMatch(JSON.stringify(await adapter.inspect({
    origin: 'https://router.example.invalid:443', locatorRole: 'status', locatorName: 'Status',
  })), /untrusted page text/u);
  assert.equal(fake.state.goto, 'https://router.example.invalid:443');
  await assert.rejects(() => adapter.navigate({ origin: 'https://escape.example.invalid:443' }), /ORIGIN_ESCAPE/u);
  await assert.rejects(() => fake.state.contextRoute({
    request: () => ({
      url: () => 'https://escape.example.invalid/a',
      frame: () => ({ page: () => fake.state.pages[0] }),
    }),
    abort: async () => { throw new Error('SUBRESOURCE_BLOCKED'); }, continue: async () => {},
  }), /SUBRESOURCE_BLOCKED/u);
  let popupRequestAborted = 0;
  const popup = { async close() { fake.state.popupClosed += 1; } };
  await fake.state.contextRoute({
    request: () => ({
      url: () => 'https://router.example.invalid/popup',
      frame: () => ({ page: () => popup }),
    }),
    abort: async () => { popupRequestAborted += 1; }, continue: async () => {},
  });
  await fake.contextEvents.get('page')(popup);
  assert.equal(popupRequestAborted, 1);
  assert.equal(fake.state.popupClosed, 1);
  await adapter.fill({
    origin: 'https://router.example.invalid:443', locatorRole: 'textbox',
    locatorName: 'Password', credential: 'SYNTH_SECRET_ADAPTER',
  });
  fake.state.currentUrl = 'https://login.example.invalid/auth';
  await assert.rejects(() => adapter.fill({
    origin: 'https://router.example.invalid:443', locatorRole: 'textbox',
    locatorName: 'Password', credential: 'SYNTH_SECRET_ADAPTER',
  }), /ORIGIN_ESCAPE/u);
  await adapter.close();
  assert.equal(fake.state.closed, 3);
});


test('Puppeteer adapter does not claim pre-navigation popup containment', async () => {
  const fake = puppeteerRuntime();
  const adapter = await createPuppeteerAdapter(fake.runtime, {
    id: 'puppeteer', allowedOrigins: [
      'https://router.example.invalid:443', 'https://login.example.invalid:443',
    ],
  });
  await adapter.open();
  assert.equal(adapter.capabilities.popups, false);
  assert.equal(fake.state.interception, true);
  let aborted = 0;
  await fake.pageEvents.get('request')({
    url: () => 'https://escape.example.invalid/a',
    abort: async () => { aborted += 1; }, continue: async () => {},
  });
  assert.equal(aborted, 1);
  const targetPage = { async close() { fake.state.closed += 1; } };
  await fake.browserEvents.get('targetcreated')({ type: () => 'page', page: async () => targetPage });
  assert.equal(fake.state.closed, 1);
  fake.state.currentUrl = 'https://login.example.invalid/auth';
  await assert.rejects(() => adapter.click({
    origin: 'https://router.example.invalid:443', locatorRole: 'button',
  }), /ORIGIN_ESCAPE/u);
  await adapter.close();
  assert.equal(fake.state.closed, 4);
});


test('semantic actions block an allowed-origin navigation race before applying protected values', async () => {
  for (const create of [createPlaywrightAdapter, createPuppeteerAdapter]) {
    const fake = create === createPlaywrightAdapter ? playwrightRuntime() : puppeteerRuntime();
    const adapter = await create(fake.runtime, {
      id: create === createPlaywrightAdapter ? 'playwright' : 'puppeteer',
      allowedOrigins: [
        'https://router.example.invalid:443', 'https://login.example.invalid:443',
      ],
    });
    await adapter.open();
    await adapter.navigate({ origin: 'https://login.example.invalid:443' });

    let protectedValueApplied = false;
    fake.resources.page.getByRole = () => {
      fake.state.currentUrl = 'https://router.example.invalid/dashboard';
      return {
        async fill() { protectedValueApplied = true; },
      };
    };

    await assert.rejects(() => adapter.fill({
      origin: 'https://login.example.invalid:443', locatorRole: 'textbox',
      locatorName: 'Password', credential: 'SYNTH_SECRET_ADAPTER',
    }), /ORIGIN_ESCAPE/u);
    assert.equal(protectedValueApplied, false);

    fake.state.currentUrl = 'https://login.example.invalid/auth';
    fake.resources.page.getByRole = () => ({
      async fill() {
        let aborted = false;
        const syntheticNavigation = {
          url: () => 'https://router.example.invalid/dashboard',
          isNavigationRequest: () => true,
          frame: () => fake.resources.page,
          abort: async () => { aborted = true; },
          continue: async () => {},
        };
        if (create === createPlaywrightAdapter) {
          await fake.state.contextRoute({
            request: () => ({
              url: syntheticNavigation.url,
              isNavigationRequest: syntheticNavigation.isNavigationRequest,
              frame: () => ({ page: () => fake.resources.page }),
            }),
            abort: syntheticNavigation.abort,
            continue: syntheticNavigation.continue,
          });
        } else {
          await fake.pageEvents.get('request')(syntheticNavigation);
        }
        if (aborted) throw new Error('REQUEST_BLOCKED');
        fake.state.currentUrl = 'https://router.example.invalid/dashboard';
        protectedValueApplied = true;
      },
    });
    await assert.rejects(() => adapter.fill({
      origin: 'https://login.example.invalid:443', locatorRole: 'textbox',
      locatorName: 'Password', credential: 'SYNTH_SECRET_ADAPTER',
    }));
    assert.equal(protectedValueApplied, false);
    await adapter.close();
  }
});


test('navigation blocks a redirect to another envelope-allowed origin before crossing', async () => {
  for (const create of [createPlaywrightAdapter, createPuppeteerAdapter]) {
    const fake = create === createPlaywrightAdapter ? playwrightRuntime() : puppeteerRuntime();
    const adapter = await create(fake.runtime, {
      id: create === createPlaywrightAdapter ? 'playwright' : 'puppeteer',
      allowedOrigins: [
        'https://router.example.invalid:443', 'https://login.example.invalid:443',
      ],
    });
    await adapter.open();
    let crossedOrigin = false;
    fake.resources.page.goto = async (url) => {
      async function dispatch(requestUrl) {
        let aborted = false;
        const syntheticNavigation = {
          url: () => requestUrl,
          isNavigationRequest: () => true,
          frame: () => fake.resources.page,
          abort: async () => { aborted = true; },
          continue: async () => {},
        };
        if (create === createPlaywrightAdapter) {
          await fake.state.contextRoute({
            request: () => ({
              url: syntheticNavigation.url,
              isNavigationRequest: syntheticNavigation.isNavigationRequest,
              frame: () => ({ page: () => fake.resources.page }),
            }),
            abort: syntheticNavigation.abort,
            continue: syntheticNavigation.continue,
          });
        } else {
          await fake.pageEvents.get('request')(syntheticNavigation);
        }
        return aborted;
      }
      if (await dispatch(url)) throw new Error('REQUEST_BLOCKED');
      if (await dispatch('https://login.example.invalid/redirected')) {
        throw new Error('REDIRECT_BLOCKED');
      }
      crossedOrigin = true;
      fake.state.currentUrl = 'https://login.example.invalid/redirected';
    };

    await assert.rejects(() => adapter.navigate({
      origin: 'https://router.example.invalid:443',
    }));
    assert.equal(crossedOrigin, false);
    await adapter.close();
  }
});


test('Playwright reports a blocked redirect without retaining the hostile destination', async () => {
  const fake = playwrightRuntime();
  const adapter = await createPlaywrightAdapter(fake.runtime, {
    allowedOrigins: ['https://router.example.invalid:443'],
  });
  await adapter.open();
  fake.resources.page.goto = async (url) => {
    let aborted = false;
    await fake.state.contextRoute({
      request: () => ({
        url: () => url, isNavigationRequest: () => true,
        frame: () => ({ page: () => fake.resources.page }),
      }),
      abort: async () => { aborted = true; }, continue: async () => {},
    });
    if (!aborted) {
      await fake.state.contextRoute({
        request: () => ({
          url: () => 'https://forbidden.example.invalid/UNTRUSTED_REDIRECT_CANARY',
          isNavigationRequest: () => true,
          frame: () => ({ page: () => fake.resources.page }),
        }),
        abort: async () => { aborted = true; }, continue: async () => {},
      });
    }
    if (aborted) throw new Error('https://forbidden.example.invalid/UNTRUSTED_REDIRECT_CANARY');
  };
  await assert.rejects(
    () => adapter.navigate({ origin: 'https://router.example.invalid:443' }),
    (error) => error?.code === 'ORIGIN_ESCAPE' && !String(error).includes('UNTRUSTED_REDIRECT_CANARY'),
  );
  await adapter.close();
});


test('page-bound screenshot actions enforce origin without requiring a semantic locator', async () => {
  for (const create of [createPlaywrightAdapter, createPuppeteerAdapter]) {
    const fake = create === createPlaywrightAdapter ? playwrightRuntime() : puppeteerRuntime();
    const captures = [];
    const adapter = await create(fake.runtime, {
      id: create === createPlaywrightAdapter ? 'playwright' : 'puppeteer',
      allowedOrigins: ['https://router.example.invalid:443'],
      artifactManager: {
        async capture(value) { captures.push(value); return { artifactId: 'artifact-opaque-1' }; },
      },
    });
    await adapter.open();
    await adapter.navigate({ origin: 'https://router.example.invalid:443' });
    const result = await adapter.screenshot({
      origin: 'https://router.example.invalid:443', artifactRef: 'operation-artifact-1',
    });
    assert.deepEqual(result, { status: 'ok', observation: 'artifact-opaque-1' });
    assert.equal(fake.state.screenshot, true);
    assert.equal(captures.length, 1);
    await adapter.close();
  }
});


test('Playwright semantic locator drift fails closed with a content-free reason code', async () => {
  const fake = playwrightRuntime();
  fake.resources.page.getByRole = () => ({
    async click() {
      const error = new Error('UNTRUSTED_RUNTIME_LOCATOR_DETAIL');
      error.name = 'TimeoutError';
      throw error;
    },
  });
  const adapter = await createPlaywrightAdapter(fake.runtime, {
    allowedOrigins: ['https://router.example.invalid:443'],
  });
  await adapter.open();
  await adapter.navigate({ origin: 'https://router.example.invalid:443' });
  await assert.rejects(
    () => adapter.click({
      origin: 'https://router.example.invalid:443', locatorRole: 'button',
      locatorName: 'Expected control', effect: 'INTERACTIVE_STATE',
    }),
    (error) => error?.code === 'UI_DRIFT' && !String(error).includes('UNTRUSTED_RUNTIME_LOCATOR_DETAIL'),
  );
  await adapter.close();
});


test('Playwright preserves trusted content-free failures and sanitizes other action errors', async () => {
  for (const code of ['ORIGIN_ESCAPE', 'TOOL_TIMEOUT', 'BROWSER_CRASH', 'ARTIFACT_HANDLE_UNKNOWN']) {
    const fake = playwrightRuntime();
    fake.resources.page.getByRole = () => ({
      async click() { const error = new Error('UNTRUSTED_DETAIL'); error.code = code; throw error; },
    });
    const adapter = await createPlaywrightAdapter(fake.runtime, {
      allowedOrigins: ['https://router.example.invalid:443'],
    });
    await adapter.open();
    await adapter.navigate({ origin: 'https://router.example.invalid:443' });
    await assert.rejects(
      () => adapter.click({
        origin: 'https://router.example.invalid:443', locatorRole: 'button',
        locatorName: 'Control', effect: 'INTERACTIVE_STATE',
      }),
      (error) => error?.code === code && !String(error).includes('UNTRUSTED_DETAIL'),
    );
    await adapter.close();
  }

  const fake = playwrightRuntime();
  fake.resources.page.getByRole = () => ({
    async click() { throw new Error('UNTRUSTED_RAW_ACTION_DETAIL'); },
  });
  const adapter = await createPlaywrightAdapter(fake.runtime, {
    allowedOrigins: ['https://router.example.invalid:443'],
  });
  await adapter.open();
  await adapter.navigate({ origin: 'https://router.example.invalid:443' });
  await assert.rejects(
    () => adapter.click({
      origin: 'https://router.example.invalid:443', locatorRole: 'button',
      locatorName: 'Control', effect: 'INTERACTIVE_STATE',
    }),
    (error) => error?.code === 'ADAPTER_ACTION_FAILED'
      && !String(error).includes('UNTRUSTED_RAW_ACTION_DETAIL'),
  );
  await adapter.close();
});


test('Playwright generic click denies a download link before dispatch', async () => {
  const fake = playwrightRuntime();
  let clicks = 0;
  fake.resources.page.getByRole = () => ({
    async getAttribute(name) { return name === 'download' ? '' : '/download'; },
    async click() { clicks += 1; },
  });
  const adapter = await createPlaywrightAdapter(fake.runtime, {
    allowedOrigins: ['https://router.example.invalid:443'],
  });
  await adapter.open();
  await adapter.navigate({ origin: 'https://router.example.invalid:443' });
  await assert.rejects(
    () => adapter.click({
      origin: 'https://router.example.invalid:443', locatorRole: 'link',
      locatorName: 'Download configuration', effect: 'SENSITIVE_ARTIFACT',
    }),
    (error) => error?.code === 'DOWNLOAD_DEFAULT_DENIED',
  );
  assert.equal(clicks, 0);
  await adapter.close();
});


test('Playwright denies declared artifact navigation and submit before dispatch without a policy', async () => {
  for (const action of ['navigate', 'submit']) {
    const fake = playwrightRuntime();
    let dispatches = 0;
    fake.resources.page.goto = async (url) => { dispatches += 1; fake.state.currentUrl = url; };
    fake.resources.page.getByRole = () => ({ async click() { dispatches += 1; } });
    const adapter = await createPlaywrightAdapter(fake.runtime, {
      allowedOrigins: ['https://router.example.invalid:443'],
    });
    await adapter.open();
    fake.state.currentUrl = 'https://router.example.invalid/form';
    const request = action === 'navigate'
      ? { origin: 'https://router.example.invalid/download', effect: 'SENSITIVE_ARTIFACT' }
      : {
          origin: 'https://router.example.invalid:443', locatorRole: 'button',
          locatorName: 'Export', effect: 'SENSITIVE_ARTIFACT',
        };
    await assert.rejects(
      () => adapter[action](request),
      (error) => error?.code === 'DOWNLOAD_DEFAULT_DENIED',
    );
    assert.equal(dispatches, 0);
    await adapter.close();
  }
});


test('Playwright common route fetch failure is not reclassified as origin escape', async () => {
  const fake = playwrightRuntime();
  fake.resources.page.goto = async (url) => {
    let aborted = false;
    await fake.state.contextRoute({
      request: () => ({
        url: () => url, isNavigationRequest: () => true,
        frame: () => ({ page: () => fake.resources.page }),
      }),
      fetch: async () => { throw new Error('UNTRUSTED_FETCH_FAILURE'); },
      fulfill: async () => {}, abort: async () => { aborted = true; }, continue: async () => {},
    });
    if (aborted) throw new Error('UNTRUSTED_NAVIGATION_FAILURE');
  };
  const adapter = await createPlaywrightAdapter(fake.runtime, {
    allowedOrigins: ['https://router.example.invalid:443'],
  });
  await adapter.open();
  await assert.rejects(
    () => adapter.navigate({ origin: 'https://router.example.invalid:443' }),
    (error) => error?.code === 'ADAPTER_NAVIGATION_FAILED',
  );
  await adapter.close();
});


test('Playwright route fetch disables redirects fulfills success and disposes the response', async () => {
  const fake = playwrightRuntime();
  const observed = { fetchOptions: null, fulfilled: 0, disposed: 0 };
  const response = {
    headers: () => ({ 'content-length': '128' }),
    async dispose() { observed.disposed += 1; },
  };
  fake.resources.page.goto = async (url) => {
    await fake.state.contextRoute({
      request: () => ({
        url: () => url, isNavigationRequest: () => true,
        frame: () => ({ page: () => fake.resources.page }),
      }),
      fetch: async (options) => { observed.fetchOptions = options; return response; },
      fulfill: async ({ response: selected }) => { assert.equal(selected, response); observed.fulfilled += 1; },
      abort: async () => { throw new Error('UNEXPECTED_ABORT'); }, continue: async () => {},
    });
    fake.state.currentUrl = url;
  };
  const adapter = await createPlaywrightAdapter(fake.runtime, {
    allowedOrigins: ['https://router.example.invalid:443'],
  });
  await adapter.open();
  assert.deepEqual(await adapter.navigate({ origin: 'https://router.example.invalid:443' }), {
    status: 'ok', observation: 'navigation-complete',
  });
  assert.deepEqual(observed.fetchOptions, { maxRedirects: 0 });
  assert.equal(observed.fulfilled, 1);
  assert.equal(observed.disposed, 1);
  await adapter.close();
});


test('Playwright disposes blocked redirect responses without fulfilling them', async () => {
  const fake = playwrightRuntime();
  const observed = { fulfilled: 0, aborted: 0, disposed: 0 };
  const response = {
    headers: () => ({
      'content-length': '0', location: 'https://forbidden.example.invalid/canary',
    }),
    async dispose() { observed.disposed += 1; },
  };
  fake.resources.page.goto = async (url) => {
    await fake.state.contextRoute({
      request: () => ({
        url: () => url, isNavigationRequest: () => true,
        frame: () => ({ page: () => fake.resources.page }),
      }),
      fetch: async () => response,
      fulfill: async () => { observed.fulfilled += 1; },
      abort: async () => { observed.aborted += 1; }, continue: async () => {},
    });
    if (observed.aborted) throw new Error('UNTRUSTED_NAVIGATION_FAILURE');
  };
  const adapter = await createPlaywrightAdapter(fake.runtime, {
    allowedOrigins: ['https://router.example.invalid:443'],
  });
  await adapter.open();
  await assert.rejects(
    () => adapter.navigate({ origin: 'https://router.example.invalid:443' }),
    (error) => error?.code === 'ORIGIN_ESCAPE',
  );
  assert.deepEqual(observed, { fulfilled: 0, aborted: 1, disposed: 1 });
  await adapter.close();
});


test('Playwright rejects unexpected attachment responses and disposes them', async () => {
  for (const action of ['navigate', 'submit']) {
    const fake = playwrightRuntime();
    const observed = { fulfilled: 0, aborted: 0, disposed: 0 };
    const response = {
      headers: () => ({
        'content-disposition': 'attachment; filename="fixture.json"', 'content-length': '128',
      }),
      async dispose() { observed.disposed += 1; },
    };
    const dispatch = async (url) => {
      await fake.state.contextRoute({
        request: () => ({
          url: () => url, isNavigationRequest: () => true,
          frame: () => ({ page: () => fake.resources.page }),
        }),
        fetch: async () => response,
        fulfill: async () => { observed.fulfilled += 1; },
        abort: async () => { observed.aborted += 1; }, continue: async () => {},
      });
      if (observed.aborted) throw new Error('UNTRUSTED_DOWNLOAD_FAILURE');
      fake.state.currentUrl = url;
    };
    fake.resources.page.goto = dispatch;
    fake.resources.page.getByRole = () => ({ async click() { await dispatch('https://router.example.invalid/download'); } });
    const adapter = await createPlaywrightAdapter(fake.runtime, {
      allowedOrigins: ['https://router.example.invalid:443'],
    });
    await adapter.open();
    if (action === 'submit') {
      fake.state.currentUrl = 'https://router.example.invalid/form';
      await assert.rejects(
        () => adapter.submit({
          origin: 'https://router.example.invalid:443', locatorRole: 'button',
          locatorName: 'Export', effect: 'INTERACTIVE_STATE',
        }),
        (error) => error?.code === 'DOWNLOAD_DEFAULT_DENIED',
      );
    } else {
      await assert.rejects(
        () => adapter.navigate({ origin: 'https://router.example.invalid/download' }),
        (error) => error?.code === 'DOWNLOAD_DEFAULT_DENIED',
      );
    }
    assert.deepEqual(observed, { fulfilled: 0, aborted: 1, disposed: 1 });
    await adapter.close();
  }
});


test('adapter close remains idempotent after partial open failure', async () => {
  const fake = playwrightRuntime();
  fake.runtime.chromium.launch = async () => ({
    async newContext() { throw new Error('SYNTH_OPEN_FAILURE'); },
    async close() { fake.state.closed += 1; },
  });
  const adapter = await createPlaywrightAdapter(fake.runtime, {
    id: 'playwright', allowedOrigins: ['https://router.example.invalid:443'],
  });
  await assert.rejects(() => adapter.open(), /ADAPTER_OPEN_FAILED/u);
  await adapter.close();
  assert.equal(fake.state.closed, 1);
});


test('built-in adapters aggregate close failures and remain idempotent', async () => {
  for (const create of [createPlaywrightAdapter, createPuppeteerAdapter]) {
    const fake = create === createPlaywrightAdapter ? playwrightRuntime() : puppeteerRuntime();
    const adapter = await create(fake.runtime, {
      id: create === createPlaywrightAdapter ? 'playwright' : 'puppeteer',
      allowedOrigins: ['https://router.example.invalid:443'],
    });
    await adapter.open();
    const attempts = [];
    fake.resources.page.close = async () => { attempts.push('page'); throw new Error('PAGE_CLOSE_FAILED'); };
    fake.resources.context.close = async () => { attempts.push('context'); throw new Error('CONTEXT_CLOSE_FAILED'); };
    fake.resources.browser.close = async () => { attempts.push('browser'); throw new Error('BROWSER_CLOSE_FAILED'); };
    await assert.rejects(() => adapter.close(), /ADAPTER_CLOSE_FAILED/u);
    assert.deepEqual(attempts, ['page', 'context', 'browser']);
    await adapter.close();
    assert.deepEqual(attempts, ['page', 'context', 'browser']);
  }
});


test('adapters verify predicates structurally without returning observed page values', async () => {
  for (const create of [createPlaywrightAdapter, createPuppeteerAdapter]) {
    const fake = create === createPlaywrightAdapter ? playwrightRuntime() : puppeteerRuntime();
    const adapter = await create(fake.runtime, {
      id: create === createPlaywrightAdapter ? 'playwright' : 'puppeteer',
      allowedOrigins: ['https://router.example.invalid:443'],
    });
    await adapter.open();
    await adapter.navigate({ origin: 'https://router.example.invalid:443' });
    const cases = [
      [{ origin: 'https://router.example.invalid:443', locatorRole: 'status', locatorName: 'Saved state', predicate: 'present', expected: 'ignored', expectRef: 'interface-state' }, 'met'],
      [{ origin: 'https://router.example.invalid:443', locatorRole: 'status', locatorName: 'Saved state', predicate: 'text-equals', expected: 'untrusted page text', expectRef: 'interface-state' }, 'met'],
      [{ origin: 'https://router.example.invalid:443', locatorRole: 'status', locatorName: 'Saved state', predicate: 'text-equals', expected: 'different', expectRef: 'interface-state' }, 'not-met'],
      [{ origin: 'https://router.example.invalid:443', locatorRole: 'combobox', locatorName: 'Mode', predicate: 'value-equals', expected: 'selected-value', expectRef: 'interface-state' }, 'met'],
      [{ origin: 'https://router.example.invalid:443', locatorRole: 'checkbox', locatorName: 'Enabled', predicate: 'checked', expected: 'true', expectRef: 'interface-state' }, 'met'],
      [{ origin: 'https://router.example.invalid:443', locatorRole: 'combobox', locatorName: 'Mode', predicate: 'selected-value-equals', expected: 'selected-value', expectRef: 'interface-state' }, 'met'],
    ];
    for (const [request, status] of cases) {
      const result = await adapter.verify(request);
      assert.deepEqual(result, { status, expectRef: 'interface-state' });
      assert.equal(Object.hasOwn(result, 'observed'), false);
      assert.doesNotMatch(JSON.stringify(result), /untrusted page text|selected-value/u);
    }
    await adapter.close();
  }
});


function lifetimeFixture() {
  let now = 999;
  return {
    lifetime: createOperationLifetime({ expiresAt: 1000 }, createOperationClock(() => now)),
    expire() { now = 1000; },
  };
}


const LIFETIME_ORIGIN = 'https://router.example.invalid:443';
const expired = (error) => error?.code === 'OPERATION_EXPIRED';


test('built-in adapters install exact immutable lifetime identity, never a forged callback', async () => {
  for (const create of [createPlaywrightAdapter, createPuppeteerAdapter]) {
    const fake = create === createPlaywrightAdapter ? playwrightRuntime() : puppeteerRuntime();
    const { lifetime } = lifetimeFixture();
    const adapter = await create(fake.runtime, { allowedOrigins: [LIFETIME_ORIGIN], operationLifetime: lifetime });
    assert.equal(hasOperationLifetime(adapter, lifetime), true);
    const standalone = await create(fake.runtime, { allowedOrigins: [LIFETIME_ORIGIN] });
    assert.equal(hasOperationLifetime(standalone, lifetime), false);
    await assert.rejects(() => create(fake.runtime, {
      allowedOrigins: [LIFETIME_ORIGIN], operationLifetime: { ...lifetime },
    }), (error) => error?.code === 'OPERATION_LIFETIME_UNPROVEN');
  }
});


test('Playwright expiry inside link metadata blocks the following click and permits cleanup', async () => {
  const fake = playwrightRuntime();
  const clock = lifetimeFixture();
  const calls = [];
  fake.resources.page.getByRole = () => ({
    async getAttribute(name) { assert.equal(name, 'download'); calls.push('attribute'); clock.expire(); return null; },
    async click() { calls.push('click'); },
  });
  const adapter = await createPlaywrightAdapter(fake.runtime, {
    allowedOrigins: [LIFETIME_ORIGIN], operationLifetime: clock.lifetime,
  });
  await adapter.open();
  fake.state.currentUrl = LIFETIME_ORIGIN;
  await assert.rejects(() => adapter.click({ origin: LIFETIME_ORIGIN, locatorRole: 'link' }), expired);
  assert.deepEqual(calls, ['attribute']);
  await adapter.close();
  assert.equal(fake.state.closed, 3);
});


for (const [family, create, makeRuntime] of [
  ['Playwright', createPlaywrightAdapter, playwrightRuntime],
  ['Puppeteer', createPuppeteerAdapter, puppeteerRuntime],
]) {
  test(`${family} expiry during navigation blocks the later inspection read`, async () => {
    const fake = makeRuntime();
    const clock = lifetimeFixture();
    const calls = [];
    fake.resources.page.goto = async () => { calls.push('navigate'); fake.state.currentUrl = LIFETIME_ORIGIN; clock.expire(); };
    fake.resources.page.getByRole = () => ({
      async textContent() { calls.push('read'); return 'fixture'; },
      async evaluate() { calls.push('read'); return 'fixture'; },
    });
    const adapter = await create(fake.runtime, { allowedOrigins: [LIFETIME_ORIGIN], operationLifetime: clock.lifetime });
    await adapter.open();
    await assert.rejects(() => adapter.inspect({ origin: LIFETIME_ORIGIN, locatorRole: 'status' }), expired);
    assert.deepEqual(calls, ['navigate']);
    await adapter.close();
    assert.equal(fake.state.closed, 3);
  });

  test(`${family} expiry after screenshot blocks artifact capture`, async () => {
    const fake = makeRuntime();
    const clock = lifetimeFixture();
    const calls = [];
    fake.resources.page.screenshot = async () => { calls.push('screenshot'); clock.expire(); return Buffer.from('fixture'); };
    const adapter = await create(fake.runtime, {
      allowedOrigins: [LIFETIME_ORIGIN], operationLifetime: clock.lifetime,
      artifactManager: { async capture() { calls.push('capture'); return { artifactId: 'fixture-artifact' }; } },
    });
    await adapter.open();
    fake.state.currentUrl = LIFETIME_ORIGIN;
    await assert.rejects(() => adapter.screenshot({ origin: LIFETIME_ORIGIN }), expired);
    assert.deepEqual(calls, ['screenshot']);
    await adapter.close();
    assert.equal(fake.state.closed, 3);
  });

  test(`${family} expiry during materialization blocks the browser upload`, async () => {
    const fake = makeRuntime();
    const clock = lifetimeFixture();
    const calls = [];
    fake.resources.page.getByRole = () => ({
      async setInputFiles() { calls.push('upload'); },
      async uploadFile() { calls.push('upload'); },
    });
    const adapter = await create(fake.runtime, {
      allowedOrigins: [LIFETIME_ORIGIN], operationLifetime: clock.lifetime,
      artifactManager: { materialize(ref) { assert.equal(ref, 'fixture-artifact'); calls.push('materialize'); clock.expire(); return '/fixture'; } },
    });
    await adapter.open();
    fake.state.currentUrl = LIFETIME_ORIGIN;
    await assert.rejects(() => adapter.upload({ origin: LIFETIME_ORIGIN, locatorRole: 'button', artifactRef: 'fixture-artifact' }), expired);
    assert.deepEqual(calls, ['materialize']);
    await adapter.close();
    assert.equal(fake.state.closed, 3);
  });

  test(`${family} expired delayed requests abort without any network dispatch`, async () => {
    const fake = makeRuntime();
    const clock = lifetimeFixture();
    const calls = [];
    const adapter = await create(fake.runtime, { allowedOrigins: [LIFETIME_ORIGIN], operationLifetime: clock.lifetime });
    await adapter.open();
    clock.expire();
    const request = {
      url: () => LIFETIME_ORIGIN, frame: () => ({ page: () => fake.resources.page }),
      async continue() { calls.push('continue'); }, async abort() { calls.push('abort'); },
    };
    if (family === 'Playwright') {
      await fake.state.contextRoute({
        request: () => request, continue: request.continue, abort: request.abort,
        async fetch() { calls.push('fetch'); return {}; }, async fulfill() { calls.push('fulfill'); },
      });
    } else {
      await fake.pageEvents.get('request')(request);
    }
    assert.deepEqual(calls, ['abort']);
    await adapter.close();
    assert.equal(fake.state.closed, 3);
  });

  test(`${family} a live numeric control succeeds but a late locator result is not success`, async () => {
    const fake = makeRuntime();
    const clock = lifetimeFixture();
    const adapter = await create(fake.runtime, { allowedOrigins: [LIFETIME_ORIGIN], operationLifetime: clock.lifetime });
    await adapter.open();
    fake.state.currentUrl = LIFETIME_ORIGIN;
    assert.equal((await adapter.fill({ origin: LIFETIME_ORIGIN, locatorRole: 'textbox', credential: 'fixture-value' })).status, 'ok');
    fake.resources.page.getByRole = () => ({ async inputValue() { clock.expire(); return 'fixture-value'; } });
    await assert.rejects(() => adapter.verify({
      origin: LIFETIME_ORIGIN, locatorRole: 'textbox', predicate: 'value-equals', expected: 'fixture-value', expectRef: 'fixture-state',
    }), expired);
    await adapter.close();
    assert.equal(fake.state.closed, 3);
  });
}


test('Playwright late fetched responses are aborted and disposed rather than fulfilled', async () => {
  const fake = playwrightRuntime();
  const clock = lifetimeFixture();
  const calls = [];
  const adapter = await createPlaywrightAdapter(fake.runtime, { allowedOrigins: [LIFETIME_ORIGIN], operationLifetime: clock.lifetime });
  await adapter.open();
  await fake.state.contextRoute({
    request: () => ({ url: () => LIFETIME_ORIGIN, frame: () => ({ page: () => fake.resources.page }) }),
    async fetch() { calls.push('fetch'); clock.expire(); return { headers: () => ({}), async dispose() { calls.push('dispose'); } }; },
    async fulfill() { calls.push('fulfill'); }, async abort() { calls.push('abort'); },
  });
  assert.deepEqual(calls, ['fetch', 'abort', 'dispose']);
  await adapter.close();
  assert.equal(fake.state.closed, 3);
});


test('expiry during browser launch captures ownership before blocking context creation', async () => {
  for (const create of [createPlaywrightAdapter, createPuppeteerAdapter]) {
    const fake = create === createPlaywrightAdapter ? playwrightRuntime() : puppeteerRuntime();
    const clock = lifetimeFixture();
    let contexts = 0;
    const launch = async () => { clock.expire(); return fake.resources.browser; };
    if (create === createPlaywrightAdapter) {
      fake.runtime.chromium.launch = launch;
      fake.resources.browser.newContext = async () => { contexts += 1; return fake.resources.context; };
    } else {
      fake.runtime.launch = launch;
      fake.resources.browser.createBrowserContext = async () => { contexts += 1; return fake.resources.context; };
    }
    const adapter = await create(fake.runtime, { allowedOrigins: [LIFETIME_ORIGIN], operationLifetime: clock.lifetime });
    await assert.rejects(() => adapter.open(), expired);
    assert.equal(contexts, 0);
    assert.equal(fake.state.closed, 1);
    await adapter.close();
    assert.equal(fake.state.closed, 1);
  }
});


test('untrusted route error codes cannot masquerade as lifetime failures', async () => {
  const fake = playwrightRuntime();
  const { lifetime } = lifetimeFixture();
  fake.resources.page.goto = async () => {
    let aborted = false;
    await fake.state.contextRoute({
      request: () => ({ url: () => LIFETIME_ORIGIN, frame: () => ({ page: () => fake.resources.page }) }),
      async fetch() { throw Object.assign(new Error('fixture failure'), { code: 'OPERATION_UNRECOGNIZED' }); },
      async fulfill() { assert.fail('failed fetch cannot fulfill'); },
      async abort() { aborted = true; },
    });
    if (aborted) throw new Error('REQUEST_BLOCKED');
  };
  const adapter = await createPlaywrightAdapter(fake.runtime, { allowedOrigins: [LIFETIME_ORIGIN], operationLifetime: lifetime });
  await adapter.open();
  await assert.rejects(() => adapter.navigate({ origin: LIFETIME_ORIGIN }),
    (error) => error?.code === 'ADAPTER_NAVIGATION_FAILED');
  await adapter.close();
});


test('supported fetch interfaces narrow timeouts without limiting the detected major version', async () => {
  for (const version of ['1.33.0', '2.0.0']) {
    const fake = playwrightRuntime(version);
    const { lifetime } = lifetimeFixture();
    const calls = [];
    const adapter = await createPlaywrightAdapter(fake.runtime, { allowedOrigins: [LIFETIME_ORIGIN], operationLifetime: lifetime });
    await adapter.open();
    await fake.state.contextRoute({
      request: () => ({ url: () => LIFETIME_ORIGIN, frame: () => ({ page: () => fake.resources.page }) }),
      async fetch(options) { calls.push(options); return { headers: () => ({}), async dispose() {} }; },
      async fulfill() {}, async abort() { assert.fail('live request must not abort'); },
    });
    assert.deepEqual(calls, [{ maxRedirects: 0, timeout: 1 }]);
    await adapter.close();
  }
});


test('failed disposal after a late launch is reported rather than hidden by expiry', async () => {
  for (const create of [createPlaywrightAdapter, createPuppeteerAdapter]) {
    const fake = create === createPlaywrightAdapter ? playwrightRuntime() : puppeteerRuntime();
    const clock = lifetimeFixture();
    const launch = async () => { clock.expire(); return fake.resources.browser; };
    if (create === createPlaywrightAdapter) fake.runtime.chromium.launch = launch;
    else fake.runtime.launch = launch;
    fake.resources.browser.close = async () => { throw new Error('fixture disposal failure'); };
    const adapter = await create(fake.runtime, { allowedOrigins: [LIFETIME_ORIGIN], operationLifetime: clock.lifetime });
    await assert.rejects(() => adapter.open(), (error) => error?.code === 'ADAPTER_CLOSE_FAILED');
  }
});
