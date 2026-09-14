import assert from 'node:assert/strict';
import test from 'node:test';

import {
  resolveBrowserAdapter,
} from '../../skills/browser-operations/scripts/browser-adapters/index.mjs';
import {
  createPlaywrightAdapter, detectPlaywright,
} from '../../skills/browser-operations/scripts/browser-adapters/playwright.mjs';
import {
  createPuppeteerAdapter, detectPuppeteer,
} from '../../skills/browser-operations/scripts/browser-adapters/puppeteer.mjs';


function playwrightRuntime() {
  const state = {
    launches: [], contexts: [], pages: [], closed: 0, popupClosed: 0,
    currentUrl: 'about:blank',
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
    async route(_pattern, handler) { state.contextRoute = handler; },
    async newPage() { state.pages.push(page); return page; },
    async close() { state.closed += 1; },
  };
  const browser = {
    async newContext(options) { state.contexts.push(options); return context; },
    async close() { state.closed += 1; },
  };
  const runtime = { version: '1.2.3', chromium: { async launch(options) { state.launches.push(options); return browser; } } };
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
  assert.equal(detected.observedVersion, '1.2.3');
  assert.equal((await detectPuppeteer(async () => { throw new Error('missing'); })).state, 'UNAVAILABLE');
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
  assert.deepEqual(fake.state.contexts, [{ acceptDownloads: false, storageState: undefined }]);
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
