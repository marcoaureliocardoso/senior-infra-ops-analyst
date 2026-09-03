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
  const state = { launches: [], contexts: [], pages: [], closed: 0, popupClosed: 0 };
  const pageEvents = new Map();
  const contextEvents = new Map();
  const page = {
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
  return { runtime, state, contextEvents, pageEvents };
}


function puppeteerRuntime() {
  const state = { launches: [], closed: 0 };
  const pageEvents = new Map();
  const browserEvents = new Map();
  const page = {
    async setRequestInterception(value) { state.interception = value; },
    on(name, handler) { pageEvents.set(name, handler); },
    async goto(url) { state.goto = url; },
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
  return { runtime, state, browserEvents, pageEvents };
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
    id: 'playwright', allowedOrigins: ['https://router.example.invalid:443'],
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
  await adapter.fill({ locatorRole: 'textbox', locatorName: 'Password', credential: 'SYNTH_SECRET_ADAPTER' });
  await adapter.close();
  assert.equal(fake.state.closed, 3);
});


test('Puppeteer adapter does not claim pre-navigation popup containment', async () => {
  const fake = puppeteerRuntime();
  const adapter = await createPuppeteerAdapter(fake.runtime, {
    id: 'puppeteer', allowedOrigins: ['https://router.example.invalid:443'],
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
  await adapter.close();
  assert.equal(fake.state.closed, 4);
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


test('adapters verify predicates structurally without returning observed page values', async () => {
  for (const create of [createPlaywrightAdapter, createPuppeteerAdapter]) {
    const fake = create === createPlaywrightAdapter ? playwrightRuntime() : puppeteerRuntime();
    const adapter = await create(fake.runtime, {
      id: create === createPlaywrightAdapter ? 'playwright' : 'puppeteer',
      allowedOrigins: ['https://router.example.invalid:443'],
    });
    await adapter.open();
    const cases = [
      [{ locatorRole: 'status', locatorName: 'Saved state', predicate: 'present', expected: 'ignored', expectRef: 'interface-state' }, 'met'],
      [{ locatorRole: 'status', locatorName: 'Saved state', predicate: 'text-equals', expected: 'untrusted page text', expectRef: 'interface-state' }, 'met'],
      [{ locatorRole: 'status', locatorName: 'Saved state', predicate: 'text-equals', expected: 'different', expectRef: 'interface-state' }, 'not-met'],
      [{ locatorRole: 'combobox', locatorName: 'Mode', predicate: 'value-equals', expected: 'selected-value', expectRef: 'interface-state' }, 'met'],
      [{ locatorRole: 'checkbox', locatorName: 'Enabled', predicate: 'checked', expected: 'true', expectRef: 'interface-state' }, 'met'],
      [{ locatorRole: 'combobox', locatorName: 'Mode', predicate: 'selected-value-equals', expected: 'selected-value', expectRef: 'interface-state' }, 'met'],
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
