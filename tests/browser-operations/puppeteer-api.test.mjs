import assert from 'node:assert/strict';
import test from 'node:test';
import { createPuppeteerAdapter } from '../../skills/browser-operations/scripts/browser-adapters/puppeteer.mjs';
import { createOperationClock, createOperationLifetime } from '../../skills/browser-operations/scripts/browser-operation-lifetime.mjs';

const origin = 'https://router.example.invalid:443';
function fixture(options = {}) {
  const calls = [];
  let url = origin;
  let now = 1000;
  const clock = createOperationClock(() => now);
  const lifetime = createOperationLifetime({ expiresAt: 2000 }, clock);
  const handle = {
    async evaluate(fn) { calls.push('evaluate'); return fn({ textContent: 'Saved', value: 'selected', checked: true }); },
    async uploadFile(value) { calls.push(['upload', value]); },
    async dispose() { calls.push('dispose'); },
  };
  const locator = {
    setTimeout() { return this; },
    async click() { calls.push('click'); },
    async fill(value) { calls.push(['fill', value]); },
    async waitHandle() { calls.push('waitHandle'); options.onHandle?.(() => { now = 2000; }); return handle; },
  };
  const page = { url: () => url, on() {}, async setRequestInterception() {},
    async goto(value) { url = value; },
    locator(selector) { calls.push(['locator', selector]); return locator; }, async close() {},
  };
  const context = { async newPage() { return page; }, async close() {} };
  const runtime = { async launch() { return { on() {}, async createBrowserContext() { return context; }, async close() {} }; } };
  return { calls, handle, runtime, lifetime };
}
async function opened(options = {}) {
  const fake = fixture(options);
  const adapter = await createPuppeteerAdapter(fake.runtime, { allowedOrigins: [origin], operationLifetime: fake.lifetime,
    artifactManager: { async materialize() { return '/synthetic/upload'; } } });
  await adapter.open();
  return { ...fake, adapter };
}

test('Puppeteer role/name selectors preserve literal names and reject unrepresentable syntax', async () => {
  const { adapter, calls } = await opened();
  try {
    for (const name of [undefined, 'Save', 'Save "quoted"', "Save 'quoted'", 'Back\\slash (1) [x]']) {
      await adapter.click({ origin, locatorRole: 'button', ...(name === undefined ? {} : { locatorName: name }) });
      const selector = calls.at(-2)[1];
      const quote = name?.includes('"') ? "'" : '"';
      assert.equal(selector, `aria/[role="button"]${name === undefined ? '' : `[name=${quote}${name}${quote}]`}`);
    }
    await assert.rejects(() => adapter.click({ origin, locatorRole: 'button', locatorName: 'Both " and \' quotes' }), /SEMANTIC_LOCATOR_UNAVAILABLE/);
    await assert.rejects(() => adapter.click({ origin, locatorRole: 'button"][name="Injected' }), /SEMANTIC_LOCATOR_UNAVAILABLE/);
  } finally { await adapter.close(); }
});

test('Puppeteer uses only documented Locator and ElementHandle methods for inspect/select/verify/upload', async () => {
  const { adapter, calls } = await opened();
  try {
    await adapter.inspect({ origin, locatorRole: 'status' });
    await adapter.select({ origin, locatorRole: 'combobox', credential: 'selected' });
    for (const [predicate, expected] of [['present', ''], ['text-equals', 'Saved'],
      ['value-equals', 'selected'], ['selected-value-equals', 'selected'], ['checked', 'true']]) {
      assert.equal((await adapter.verify({ origin, locatorRole: 'status', predicate, expected, expectRef: 'state' })).status, 'met');
    }
    await adapter.upload({ origin, locatorRole: 'button', artifactRef: 'synthetic-artifact' });
    assert.ok(calls.some((value) => Array.isArray(value) && value[0] === 'fill'));
    assert.equal(calls.filter((value) => value === 'waitHandle').length, 7);
    assert.equal(calls.filter((value) => value === 'dispose').length, 7);
    assert.ok(calls.some((value) => Array.isArray(value) && value[0] === 'upload'));
  } finally { await adapter.close(); }
});

test('Puppeteer value and checked predicates do not treat missing DOM properties as empty values', async () => {
  const { adapter, handle } = await opened();
  handle.evaluate = async () => undefined;
  try {
    for (const predicate of ['value-equals', 'selected-value-equals', 'checked']) {
      assert.equal((await adapter.verify({ origin, locatorRole: 'status', predicate, expected: '' })).status, 'not-met');
    }
  } finally { await adapter.close(); }
});

test('Puppeteer disposes a late or failed handle without evaluating after expiry', async () => {
  const { adapter, calls } = await opened({ onHandle: (expire) => expire() });
  try {
    await assert.rejects(() => adapter.verify({ origin, locatorRole: 'status', predicate: 'present' }), /EXPIRED/);
    assert.equal(calls.includes('evaluate'), false);
    assert.equal(calls.at(-1), 'dispose');
  } finally { await adapter.close(); }
  const failed = await opened();
  failed.handle.evaluate = async () => { throw new Error('synthetic read failure'); };
  try {
    await assert.rejects(() => failed.adapter.inspect({ origin, locatorRole: 'status' }));
    assert.equal(failed.calls.at(-1), 'dispose');
  } finally { await failed.adapter.close(); }
});
