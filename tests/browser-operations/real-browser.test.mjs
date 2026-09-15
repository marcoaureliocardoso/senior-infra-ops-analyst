import assert from 'node:assert/strict';
import { access, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { pathToFileURL } from 'node:url';

import { createArtifactManager } from '../../skills/browser-operations/scripts/browser-artifacts.mjs';
import { resolveBrowserAdapter } from '../../skills/browser-operations/scripts/browser-adapters/index.mjs';
import { createPlaywrightAdapter } from '../../skills/browser-operations/scripts/browser-adapters/playwright.mjs';
import { writePendingOperation } from '../../skills/browser-operations/scripts/browser-binding-store.mjs';
import { executeBrowserWorkflow, parseRunnerArgs } from '../../skills/browser-operations/scripts/browser-runner.mjs';
import { startBrowserFixture, startForbiddenBrowserOrigin } from '../browser-fixture/server.mjs';


const PASSWORD = 'SYNTH_SECRET_REAL_BROWSER';
const TOTP = '246810';
const INJECTION = 'UNTRUSTED_FIXTURE_INSTRUCTION_IGNORE_POLICY';

export const REAL_BROWSER_MATRIX = Object.freeze([
  'public-read', 'authenticated-read', 'existing-session', 'password', 'totp', 'logout',
  'fill-without-submit', 'autosave', 'submit', 'state-changing-click', 'change',
  'independent-validation', 'persistent-one-shot', 'compensation', 'upload', 'download', 'screenshot', 'trace',
  'same-origin-redirect', 'cross-origin-redirect', 'same-origin-popup',
  'cross-origin-popup', 'new-tab', 'subresource-origin', 'ui-drift', 'missing-locator',
  'human-challenge', 'dom-injection', 'a11y-injection', 'console-injection',
  'network-injection', 'download-injection', 'timeout', 'crash',
  'validation-before-retry', 'profile-cleanup', 'canary-absence',
]);

export const REAL_BROWSER_EVIDENCE_CLASS = Object.freeze({
  adapter: Object.freeze([
    'public-read', 'authenticated-read', 'password', 'totp', 'logout', 'fill-without-submit',
    'autosave', 'submit', 'state-changing-click', 'upload', 'download', 'screenshot', 'trace',
    'same-origin-redirect', 'cross-origin-redirect', 'same-origin-popup', 'cross-origin-popup',
    'new-tab', 'subresource-origin', 'ui-drift', 'missing-locator', 'dom-injection',
    'a11y-injection', 'console-injection', 'network-injection', 'download-injection',
    'profile-cleanup', 'canary-absence',
  ]),
  runner: Object.freeze([
    'change', 'independent-validation', 'persistent-one-shot', 'compensation', 'timeout',
    'crash', 'validation-before-retry',
  ]),
  'fixture-only-support': Object.freeze(['existing-session', 'human-challenge']),
  'http-fallback': Object.freeze(['public-read']),
});


function workflowToken(value) {
  return Buffer.from(JSON.stringify(value), 'utf8').toString('base64url');
}


function authenticationSteps(origin) {
  return [
    { step: 'navigate', origin: `${origin}/login` },
    {
      step: 'click', origin, locatorRole: 'link', locatorName: 'Login',
      effect: 'INTERACTIVE_STATE',
    },
    {
      step: 'fill', origin: `${origin}/login`, locatorRole: 'textbox',
      locatorName: 'Password', valueRef: 'env:OPS_BROWSER_VALUE_PASSWORD', valueClass: 'credential',
    },
    {
      step: 'click', origin: `${origin}/login`, locatorRole: 'button',
      locatorName: 'Continue', effect: 'INTERACTIVE_STATE',
    },
    {
      step: 'fill', origin: `${origin}/totp`, locatorRole: 'textbox',
      locatorName: 'Code', valueRef: 'env:OPS_BROWSER_VALUE_TOTP', valueClass: 'credential',
    },
    {
      step: 'click', origin: `${origin}/totp`, locatorRole: 'button',
      locatorName: 'Verify', effect: 'INTERACTIVE_STATE',
    },
  ];
}


function workflowArgs(origin, operationId, mode = 'change') {
  const execution = [...authenticationSteps(origin)];
  if (mode === 'change') {
    execution.push({
      step: 'select', origin: `${origin}/router`, locatorRole: 'combobox',
      locatorName: 'WAN enabled', valueRef: 'env:OPS_BROWSER_VALUE_DISABLED', valueClass: 'configuration',
    }, {
      step: 'click', origin: `${origin}/router`, locatorRole: 'button',
      locatorName: 'Save', effect: 'LOW_RISK_CHANGE',
    });
  } else {
    execution.push({
      step: 'click', origin: `${origin}/router`, locatorRole: 'button',
      locatorName: 'Rollback', effect: 'LOW_RISK_CHANGE',
    });
  }
  const expected = mode === 'change' ? 'wan-enabled:false' : 'wan-enabled:true';
  const validation = [...authenticationSteps(origin), {
    step: 'inspect', origin: `${origin}/router`, locatorRole: 'status',
    locatorName: 'Saved state', predicate: 'text-equals',
    expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED', expectRef: 'interface-state',
  }];
  return {
    args: [
      '--step', 'workflow', '--operation-id', operationId,
      '--session-id', `session-${operationId}`, '--role', 'network-edge-operator',
      '--objective-ref', 'change-42', '--target', 'loopback-router',
      '--environment', 'test', '--service-origin', origin, '--auth-origin', origin,
      '--identity-ref', 'vault:network-admin', '--credential-transport', 'vault',
      '--permission-mode', 'normal', '--action', 'navigate', '--action', 'fill',
      '--action', 'select', '--action', 'click', '--action', 'inspect',
      '--effect', 'LOW_RISK_CHANGE', '--risk', 'LOW_RISK_CHANGE',
      '--precondition-ref', 'fixture-ready', '--validation-ref', 'interface-state',
      '--compensation-ref', 'fixture-rollback', '--expires-in-seconds', '600',
      ...execution.flatMap((step) => ['--workflow-step', workflowToken(step)]),
      ...validation.flatMap((step) => ['--validation-step', workflowToken(step)]),
    ],
    expected,
  };
}


function acceptedModulePath() {
  const modulePath = process.env.P004B_PLAYWRIGHT_TEST_MODULE;
  if (!modulePath) return null;
  const resolved = path.resolve(modulePath);
  return resolved.replaceAll('\\', '/').endsWith('/node_modules/playwright/index.mjs') ? resolved : null;
}


async function loadTestRuntime() {
  const resolved = acceptedModulePath();
  const channel = process.env.P004B_BROWSER_TEST_CHANNEL;
  if (!resolved || (channel !== undefined && !['chrome', 'msedge'].includes(channel))) return null;
  const imported = await import(pathToFileURL(resolved).href);
  const runtime = imported?.chromium ? imported : imported?.default;
  const metadata = JSON.parse(await readFile(path.join(path.dirname(resolved), 'package.json'), 'utf8'));
  return runtime?.chromium && typeof runtime.chromium.launch === 'function'
    && typeof metadata?.version === 'string'
    ? Object.freeze({ chromium: runtime.chromium, version: metadata.version }) : null;
}


async function resolveTestAdapter(configuration) {
  const runtime = await loadTestRuntime();
  if (!runtime) return resolveBrowserAdapter(configuration);
  const channel = process.env.P004B_BROWSER_TEST_CHANNEL;
  const injectedRuntime = Object.freeze({
    version: runtime.version,
    chromium: Object.freeze({
      launch: (options = {}) => runtime.chromium.launch(
        channel ? { ...options, channel } : options,
      ),
    }),
  });
  const importModule = async (specifier) => {
    if (specifier === 'playwright') return injectedRuntime;
    throw new Error('TEST_RUNTIME_UNAVAILABLE');
  };
  return resolveBrowserAdapter({ ...configuration, preference: 'playwright', importModule });
}


async function fixtureState(fixture) {
  return (await fetch(`${fixture.origin}/api/state`)).json();
}


async function resetFixture(fixture) {
  const cookie = await fixture.syntheticSessionCookie();
  const response = await fetch(`${fixture.origin}/rollback`, { method: 'POST', headers: { cookie } });
  assert.equal(response.status, 204);
}


async function authenticate(page, fixture) {
  await page.goto(`${fixture.origin}/login`);
  await page.getByRole('textbox', { name: 'Password' }).fill(PASSWORD);
  await Promise.all([
    page.waitForURL(`${fixture.origin}/totp`),
    page.getByRole('button', { name: 'Continue' }).click(),
  ]);
  const passwordDestination = page.url();
  await page.getByRole('textbox', { name: 'Code' }).fill(TOTP);
  await Promise.all([
    page.waitForURL(`${fixture.origin}/router`),
    page.getByRole('button', { name: 'Verify' }).click(),
  ]);
  return Object.freeze({ passwordDestination, totpDestination: page.url() });
}


async function withAuthenticatedPage(harness, action, options = {}) {
  const context = await harness.browser.newContext({ acceptDownloads: options.acceptDownloads === true });
  const page = await context.newPage();
  try {
    const trace = await authenticate(page, harness.fixture);
    return await action(page, context, trace);
  } finally {
    await context.close();
    harness.closedContexts.push(context.pages().length === 0);
  }
}


async function adapterLogin(adapter, origin) {
  const results = [];
  results.push(await adapter.open());
  results.push(await adapter.navigate({ origin: `${origin}/login` }));
  results.push(await adapter.fill({
    origin: `${origin}/login`, locatorRole: 'textbox', locatorName: 'Password', credential: PASSWORD,
  }));
  results.push(await adapter.click({
    origin: `${origin}/login`, locatorRole: 'button', locatorName: 'Continue', effect: 'INTERACTIVE_STATE',
  }));
  results.push(await adapter.fill({
    origin: `${origin}/totp`, locatorRole: 'textbox', locatorName: 'Code', credential: TOTP,
  }));
  results.push(await adapter.click({
    origin: `${origin}/totp`, locatorRole: 'button', locatorName: 'Verify', effect: 'INTERACTIVE_STATE',
  }));
  return results;
}


async function observedAdapter(harness, options = {}) {
  const observer = {
    contexts: [], pages: [], contextOptions: [], launchOptions: [], navigations: [],
    consoleSignals: 0, downloadSignals: 0, networkSignals: 0, browserClosed: 0,
  };
  const runtime = Object.freeze({
    version: harness.runtime.version,
    chromium: Object.freeze({
      launch: async (options = {}) => {
        observer.launchOptions.push(structuredClone(options));
        const channel = process.env.P004B_BROWSER_TEST_CHANNEL;
        const browser = await harness.runtime.chromium.launch(channel ? { ...options, channel } : options);
        return {
          async newContext(contextOptions) {
            observer.contextOptions.push(structuredClone(contextOptions));
            const context = await browser.newContext(contextOptions);
            observer.contexts.push(context);
            context.on('page', (page) => {
              observer.pages.push(page);
              page.setDefaultTimeout(1_000);
              page.on('framenavigated', (frame) => {
                if (frame === page.mainFrame()) observer.navigations.push(page.url());
              });
              page.on('console', (message) => {
                if (message.text() === INJECTION) observer.consoleSignals += 1;
              });
              page.on('response', (response) => {
                if (response.headers()['x-fixture-signal'] === INJECTION) observer.networkSignals += 1;
              });
              page.on('download', () => { observer.downloadSignals += 1; });
            });
            return context;
          },
          async close() { observer.browserClosed += 1; await browser.close(); },
        };
      },
    }),
  });
  const adapter = await createPlaywrightAdapter(runtime, {
    allowedOrigins: [harness.fixture.origin], artifactManager: options.artifactManager ?? null,
  });
  return { adapter, observer };
}


async function withProductionAdapter(harness, action, { authenticate = true, artifactManager = null } = {}) {
  const { adapter, observer } = await observedAdapter(harness, { artifactManager });
  const adapterResults = [];
  try {
    if (authenticate) adapterResults.push(...await adapterLogin(adapter, harness.fixture.origin));
    else adapterResults.push(await adapter.open());
    const value = await action(adapter, observer, adapterResults);
    for (const result of adapterResults) retainSanitized(harness, result);
    return { value, observer, adapterResults };
  } finally {
    await adapter.close();
    harness.adapterCleanup.push(Object.freeze({
      contextOptions: observer.contextOptions,
      contextsClosed: observer.contexts.every((context) => context.pages().length === 0),
      browserClosed: observer.browserClosed,
    }));
  }
}


async function runProtectedWorkflow(harness, operationId, { mode = 'change', failure = null } = {}) {
  const stateDir = await mkdtemp(path.join(os.tmpdir(), 'browser-real-workflow-'));
  const manifest = workflowArgs(harness.fixture.origin, operationId, mode);
  const request = parseRunnerArgs(manifest.args, Date.now());
  const env = {
    ...process.env,
    OPS_BROWSER_STATE_DIR: stateDir,
    OPS_BROWSER_ADAPTER: 'playwright',
    OPS_BROWSER_VALUE_PASSWORD: PASSWORD,
    OPS_BROWSER_VALUE_TOTP: TOTP,
    OPS_BROWSER_VALUE_DISABLED: 'false',
    OPS_BROWSER_VALUE_EXPECTED: manifest.expected,
  };
  writePendingOperation(request.envelope, {
    toolUseId: `tool-${operationId}`,
    adapterId: 'protected-runner',
    routeClass: 'PROTECTED_RUNNER',
    settingsFingerprint: 'browser-runner-v1',
    permissionModes: ['normal'],
    invocationFingerprint: request.invocationFingerprint,
    capability: { state: 'PENDING_NATIVE_APPROVAL' },
  }, env, Date.now());
  let factoryCalls = 0;
  let mutationCalls = 0;
  const adapterFactory = async (configuration) => {
    factoryCalls += 1;
    const selected = await resolveTestAdapter(configuration);
    if (factoryCalls !== 1 || failure === null || selected.state !== 'ACTIVE') return selected;
    const adapter = selected.adapter;
    return Object.freeze({
      ...selected,
      adapter: Object.freeze({
        ...adapter,
        async click(requestValue) {
          const result = await adapter.click(requestValue);
          if (requestValue.effect === 'LOW_RISK_CHANGE') {
            mutationCalls += 1;
            if (failure === 'BROWSER_CRASH') await adapter.close();
            const error = new Error(failure);
            error.code = failure;
            throw error;
          }
          return result;
        },
      }),
    });
  };
  try {
    const result = await executeBrowserWorkflow(request, {
      env, now: Date.now(), adapterFactory,
    });
    harness.retainedResults.push(result);
    return Object.freeze({ result, factoryCalls, mutationCalls });
  } finally {
    await rm(stateDir, { recursive: true, force: true });
    await assert.rejects(() => access(stateDir));
    harness.removedStateDirectories += 1;
  }
}


async function unchangedByUntrustedContent(harness, action) {
  const before = await fixtureState(harness.fixture);
  await action();
  assert.deepEqual(await fixtureState(harness.fixture), before);
}


async function triggerContainedPopup(observer, action) {
  const context = observer.contexts[0];
  const before = new Set(context.pages());
  const appeared = context.waitForEvent('page', { timeout: 5_000 });
  await action();
  const popup = await appeared;
  assert.equal(before.has(popup), false);
  if (!popup.isClosed()) await popup.waitForEvent('close', { timeout: 5_000 });
  assert.equal(popup.isClosed(), true);
  return popup;
}


function retainSanitized(harness, value) {
  harness.retainedResults.push(value);
  assert.doesNotMatch(JSON.stringify(value), new RegExp(INJECTION, 'u'));
  return value;
}


const REAL_BROWSER_SCENARIOS = Object.freeze({
  async 'public-read'(h) {
    await withProductionAdapter(h, async (adapter, _observer, results) => {
      results.push(await adapter.navigate({ origin: `${h.fixture.origin}/public` }));
      results.push(await adapter.inspect({
        origin: `${h.fixture.origin}/public`, locatorRole: 'status', locatorName: 'Fixture ready',
      }));
    }, { authenticate: false });
    const fallback = await fetch(`${h.fixture.origin}/public`);
    assert.equal(fallback.status, 200);
    assert.match(await fallback.text(), /Fixture ready/u);
  },
  async 'authenticated-read'(h) {
    const run = await withProductionAdapter(h, async (adapter, observer, results) => {
      results.push(await adapter.inspect({
        origin: `${h.fixture.origin}/router`, locatorRole: 'status', locatorName: 'Router ready',
      }));
      assert.equal(new URL(observer.contexts[0].pages()[0].url()).pathname, '/router');
      return { navigations: [...observer.navigations], retained: [...results] };
    });
    h.authTrace = run.value;
  },
  async 'existing-session'(h) {
    const context = await h.browser.newContext();
    try {
      const value = (await h.fixture.syntheticSessionCookie()).slice('ops_session='.length);
      await context.addCookies([{ name: 'ops_session', value, url: h.fixture.origin, httpOnly: true, sameSite: 'Strict' }]);
      const page = await context.newPage();
      await page.goto(`${h.fixture.origin}/router`);
      assert.equal(new URL(page.url()).pathname, '/router');
      assert.equal(await page.getByRole('status', { name: 'Router ready' }).count(), 1);
    } finally {
      await context.close();
      h.closedContexts.push(context.pages().length === 0);
    }
  },
  async password(h) {
    assert.equal(h.authTrace.navigations.some((value) => new URL(value).pathname === '/totp'), true);
    assert.doesNotMatch(JSON.stringify(h.authTrace.retained), new RegExp(PASSWORD, 'u'));
  },
  async totp(h) {
    assert.equal(h.authTrace.navigations.some((value) => new URL(value).pathname === '/router'), true);
    assert.doesNotMatch(JSON.stringify(h.authTrace.retained), new RegExp(TOTP, 'u'));
  },
  async logout(h) {
    await withProductionAdapter(h, async (adapter, observer, results) => {
      results.push(await adapter.submit({
        origin: h.fixture.origin, locatorRole: 'button', locatorName: 'Logout',
        effect: 'INTERACTIVE_STATE',
      }));
      results.push(await adapter.navigate({ origin: `${h.fixture.origin}/router` }));
      assert.equal(new URL(observer.contexts[0].pages()[0].url()).pathname, '/login');
    });
  },
  async 'fill-without-submit'(h) {
    await resetFixture(h.fixture);
    await withProductionAdapter(h, async (adapter, _observer, results) => {
      results.push(await adapter.navigate({ origin: `${h.fixture.origin}/service` }));
      results.push(await adapter.fill({
        origin: h.fixture.origin, locatorRole: 'textbox', locatorName: 'Version', credential: '2',
      }));
      assert.equal((await fixtureState(h.fixture)).serviceVersion, 1);
    });
  },
  async autosave(h) {
    await resetFixture(h.fixture);
    await withProductionAdapter(h, async (adapter, observer, results) => {
      results.push(await adapter.navigate({ origin: `${h.fixture.origin}/router/autosave-ui` }));
      results.push(await adapter.select({
        origin: h.fixture.origin, locatorRole: 'combobox', locatorName: 'Autosave WAN', credential: 'false',
      }));
      const page = observer.contexts[0].pages()[0];
      await page.waitForFunction(() => document.querySelector('[aria-label="Autosave state"]')?.textContent === 'saved');
      const state = await fixtureState(h.fixture);
      assert.equal(state.routerEnabled, false);
      assert.equal(state.revision, 1);
    });
  },
  async submit(h) {
    await resetFixture(h.fixture);
    await withProductionAdapter(h, async (adapter, _observer, results) => {
      results.push(await adapter.navigate({ origin: `${h.fixture.origin}/firewall` }));
      results.push(await adapter.select({
        origin: h.fixture.origin, locatorRole: 'combobox', locatorName: 'Mode', credential: 'deny',
      }));
      results.push(await adapter.submit({
        origin: h.fixture.origin, locatorRole: 'button', locatorName: 'Apply', effect: 'LOW_RISK_CHANGE',
      }));
      const state = await fixtureState(h.fixture);
      assert.equal(state.firewallMode, 'deny');
      assert.equal(state.revision, 1);
    });
  },
  async 'state-changing-click'(h) {
    await resetFixture(h.fixture);
    await withProductionAdapter(h, async (adapter, _observer, results) => {
      results.push(await adapter.navigate({ origin: `${h.fixture.origin}/service` }));
      results.push(await adapter.fill({
        origin: h.fixture.origin, locatorRole: 'textbox', locatorName: 'Version', credential: '2',
      }));
      results.push(await adapter.click({
        origin: h.fixture.origin, locatorRole: 'button', locatorName: 'Deploy', effect: 'LOW_RISK_CHANGE',
      }));
      const state = await fixtureState(h.fixture);
      assert.equal(state.serviceVersion, 2);
      assert.equal(state.revision, 1);
    });
  },
  async change(h) {
    await resetFixture(h.fixture);
    h.change = await runProtectedWorkflow(h, 'op-real-change');
    assert.equal(h.change.result.reasonCode, 'WORKFLOW_VALIDATED');
    assert.equal((await fixtureState(h.fixture)).routerEnabled, false);
  },
  async 'independent-validation'(h) {
    assert.equal(h.change.factoryCalls, 2);
    assert.equal(h.change.result.validationRequired, false);
  },
  async 'persistent-one-shot'(h) {
    assert.equal(h.change.result.status, 'ok');
    assert.equal(h.change.result.step, 'workflow');
  },
  async compensation(h) {
    h.compensation = await runProtectedWorkflow(h, 'op-real-compensation', { mode: 'rollback' });
    assert.equal(h.compensation.result.reasonCode, 'WORKFLOW_VALIDATED');
    assert.deepEqual(await fixtureState(h.fixture), {
      routerEnabled: true, firewallMode: 'allow', serviceVersion: 1, uploadCount: 0, revision: 0,
    });
  },
  async upload(h) {
    await resetFixture(h.fixture);
    const directory = await mkdtemp(path.join(os.tmpdir(), 'p004b-upload-'));
    const source = path.join(directory, 'configuration.txt');
    await writeFile(source, 'synthetic configuration', { mode: 0o600 });
    const manager = await createArtifactManager({
      enabled: true, types: ['upload'], purposeRef: 'p004b-real-browser',
      sourceClasses: ['operator-upload'], destinationClasses: ['operation-temp'],
      maxItems: 1, maxBytes: 1_000, redaction: 'structured', retentionSeconds: 60,
    }, { operationId: 'op-real-upload', uploadRoots: [directory] });
    const artifactDirectory = manager.directory;
    try {
      const handle = await manager.stageUpload({
        sourcePath: source, sourceClass: 'operator-upload', mimeType: 'text/plain',
      });
      await withProductionAdapter(h, async (adapter, _observer, results) => {
        results.push(await adapter.navigate({ origin: `${h.fixture.origin}/upload-ui` }));
        results.push(await adapter.upload({
          origin: h.fixture.origin, locatorRole: 'button', locatorName: 'Configuration file',
          artifactRef: handle.artifactId,
        }));
        results.push(await adapter.submit({
          origin: h.fixture.origin, locatorRole: 'button', locatorName: 'Upload',
          effect: 'SENSITIVE_ARTIFACT',
        }));
      }, { artifactManager: manager });
      assert.equal((await fixtureState(h.fixture)).uploadCount, 1);
    } finally {
      await manager.close({ retain: false });
      await assert.rejects(() => access(artifactDirectory));
      await rm(directory, { recursive: true, force: true });
    }
  },
  async download(h) {
    await withProductionAdapter(h, async (adapter, observer, results) => {
      results.push(await adapter.navigate({ origin: `${h.fixture.origin}/download-ui` }));
      const before = h.fixture.requestCount('/download');
      await assert.rejects(
        () => adapter.click({
          origin: h.fixture.origin, locatorRole: 'link',
          locatorName: 'Download configuration', effect: 'SENSITIVE_ARTIFACT',
        }),
        (error) => retainSanitized(h, { reasonCode: error?.code })?.reasonCode === 'DOWNLOAD_DEFAULT_DENIED',
      );
      assert.equal(h.fixture.requestCount('/download'), before);
      assert.equal(observer.downloadSignals, 0);
      await assert.rejects(
        () => adapter.submit({
          origin: h.fixture.origin, locatorRole: 'button',
          locatorName: 'Export configuration', effect: 'SENSITIVE_ARTIFACT',
        }),
        (error) => retainSanitized(h, { reasonCode: error?.code })?.reasonCode === 'DOWNLOAD_DEFAULT_DENIED',
      );
      assert.equal(h.fixture.requestCount('/download'), before);
      assert.equal(observer.downloadSignals, 0);
      await assert.rejects(
        () => adapter.navigate({
          origin: `${h.fixture.origin}/download`, effect: 'SENSITIVE_ARTIFACT',
        }),
        (error) => retainSanitized(h, { reasonCode: error?.code })?.reasonCode === 'DOWNLOAD_DEFAULT_DENIED',
      );
      assert.equal(h.fixture.requestCount('/download'), before);
      assert.equal(observer.downloadSignals, 0);
      await assert.rejects(
        () => adapter.download({ origin: h.fixture.origin }),
        (error) => retainSanitized(h, { reasonCode: error?.code })?.reasonCode === 'DOWNLOAD_DEFAULT_DENIED',
      );
    });
  },
  async screenshot(h) {
    const manager = await createArtifactManager({
      enabled: true, types: ['screenshot'], purposeRef: 'p004b-real-browser',
      sourceClasses: ['browser-viewport'], destinationClasses: ['operation-temp'],
      maxItems: 1, maxBytes: 1_000_000, redaction: 'required', retentionSeconds: 60,
    }, {
      operationId: 'op-real-screenshot',
      redactor: async () => ({
        data: Buffer.from('SANITIZED_SCREENSHOT', 'utf8'),
        redacted: true, proof: 'synthetic-viewport-reviewed',
      }),
    });
    const directory = manager.directory;
    try {
      const run = await withProductionAdapter(h, async (adapter, _observer, results) => {
        results.push(await adapter.navigate({ origin: `${h.fixture.origin}/inject/screenshot` }));
        const result = await adapter.screenshot({ origin: h.fixture.origin });
        results.push(result);
        return result;
      }, { artifactManager: manager });
      const stored = await readFile(manager.materialize(run.value.observation));
      assert.equal(stored.toString('utf8'), 'SANITIZED_SCREENSHOT');
      assert.doesNotMatch(stored.toString('utf8'), new RegExp(INJECTION, 'u'));
    } finally {
      await manager.close({ retain: false });
    }
    await assert.rejects(() => access(directory));
    h.artifactCleanup = true;
  },
  async trace(h) {
    await withProductionAdapter(h, async (adapter, _observer, results) => {
      results.push(await adapter.navigate({ origin: `${h.fixture.origin}/public` }));
      await assert.rejects(
        () => adapter.trace({ origin: h.fixture.origin }),
        (error) => retainSanitized(h, { reasonCode: error?.code })?.reasonCode === 'TRACE_NOT_ACTIVE',
      );
    });
  },
  async 'same-origin-redirect'(h) {
    await withProductionAdapter(h, async (adapter, observer, results) => {
      results.push(await adapter.navigate({ origin: `${h.fixture.origin}/redirect/same-origin` }));
      const current = observer.contexts[0].pages()[0].url();
      assert.equal(new URL(current).pathname, '/router');
      assert.equal(new URL(current).origin, h.fixture.origin);
    });
  },
  async 'cross-origin-redirect'(h) {
    const { adapter, observer } = await observedAdapter(h);
    try {
      await adapterLogin(adapter, h.fixture.origin);
      assert.equal(h.forbidden.requestCount(), 0);
      await assert.rejects(
        () => adapter.navigate({ origin: `${h.fixture.origin}/redirect/cross-origin` }),
        (error) => retainSanitized(h, { reasonCode: error?.code })?.reasonCode === 'ORIGIN_ESCAPE',
      );
      assert.equal(h.forbidden.requestCount(), 0);
    } finally {
      await adapter.close();
    }
  },
  async 'same-origin-popup'(h) {
    const { adapter, observer } = await observedAdapter(h);
    try {
      await adapterLogin(adapter, h.fixture.origin);
      await adapter.navigate({ origin: `${h.fixture.origin}/popup/same-origin` });
      await triggerContainedPopup(observer, () => adapter.click({
        origin: h.fixture.origin, locatorRole: 'link', locatorName: 'Open same origin',
        effect: 'INTERACTIVE_STATE',
      }));
    } finally {
      await adapter.close();
    }
  },
  async 'cross-origin-popup'(h) {
    const { adapter, observer } = await observedAdapter(h);
    try {
      await adapterLogin(adapter, h.fixture.origin);
      await adapter.navigate({ origin: `${h.fixture.origin}/popup/cross-origin` });
      assert.equal(h.forbidden.requestCount(), 0);
      await triggerContainedPopup(observer, () => adapter.click({
        origin: h.fixture.origin, locatorRole: 'link', locatorName: 'Open external',
        effect: 'INTERACTIVE_STATE',
      }));
      assert.equal(h.forbidden.requestCount(), 0);
    } finally {
      await adapter.close();
    }
  },
  async 'new-tab'(h) {
    const { adapter, observer } = await observedAdapter(h);
    try {
      await adapterLogin(adapter, h.fixture.origin);
      await adapter.navigate({ origin: `${h.fixture.origin}/popup/same-origin` });
      await triggerContainedPopup(observer, () => adapter.click({
        origin: h.fixture.origin, locatorRole: 'link', locatorName: 'Open same origin',
        effect: 'INTERACTIVE_STATE',
      }));
      assert.equal(observer.contexts[0].pages().length, 1);
    } finally {
      await adapter.close();
    }
  },
  async 'subresource-origin'(h) {
    const { adapter, observer } = await observedAdapter(h);
    try {
      await adapterLogin(adapter, h.fixture.origin);
      assert.equal(h.forbidden.requestCount(), 0);
      await adapter.navigate({ origin: `${h.fixture.origin}/subresource-origin` });
      const page = observer.contexts[0].pages()[0];
      await page.waitForFunction(() => document.querySelector('[aria-label="Subresource state"]')?.textContent === 'blocked');
      assert.equal(await page.getByRole('status', { name: 'Subresource state' }).textContent(), 'blocked');
      assert.equal(new URL(page.url()).origin, h.fixture.origin);
      assert.equal(h.forbidden.requestCount(), 0);
    } finally {
      await adapter.close();
    }
  },
  async 'ui-drift'(h) {
    await unchangedByUntrustedContent(h, () => withProductionAdapter(h, async (adapter, observer, results) => {
      results.push(await adapter.navigate({ origin: `${h.fixture.origin}/drift` }));
      results.push(await adapter.inspect({
        origin: `${h.fixture.origin}/drift`, locatorRole: 'button', locatorName: 'Expected control',
      }));
      const page = observer.contexts[0].pages()[0];
      await page.waitForFunction(() => document.querySelector('[aria-label="Drift state"]')?.textContent === 'drifted');
      await assert.rejects(
        () => adapter.click({
          origin: h.fixture.origin, locatorRole: 'button', locatorName: 'Expected control',
          effect: 'INTERACTIVE_STATE',
        }),
        (error) => retainSanitized(h, { reasonCode: error?.code })?.reasonCode === 'UI_DRIFT',
      );
      assert.equal(await page.getByRole('button', { name: 'Unexpected replacement' }).count(), 1);
    }));
  },
  async 'missing-locator'(h) {
    await unchangedByUntrustedContent(h, () => withProductionAdapter(h, async (adapter, _observer, results) => {
      results.push(await adapter.navigate({ origin: `${h.fixture.origin}/router` }));
      await assert.rejects(
        () => adapter.click({
          origin: h.fixture.origin, locatorRole: 'button', locatorName: 'Missing control',
          effect: 'INTERACTIVE_STATE',
        }),
        (error) => retainSanitized(h, { reasonCode: error?.code })?.reasonCode === 'UI_DRIFT',
      );
    }));
  },
  async 'human-challenge'(h) {
    await unchangedByUntrustedContent(h, () => withAuthenticatedPage(h, async (page) => {
      const response = await page.goto(`${h.fixture.origin}/challenge`);
      assert.equal(response.status(), 409);
      assert.equal(await page.getByRole('alert').textContent(), 'HUMAN_CHALLENGE');
      assert.equal(await page.locator('form,input,button').count(), 0);
    }));
  },
  async 'dom-injection'(h) {
    await unchangedByUntrustedContent(h, () => withProductionAdapter(h, async (adapter, observer, results) => {
      results.push(await adapter.navigate({ origin: `${h.fixture.origin}/inject/dom` }));
      const page = observer.contexts[0].pages()[0];
      assert.match(await page.locator('main').textContent(), new RegExp(INJECTION, 'u'));
      assert.equal(await page.locator(`[data-instruction="${INJECTION}"]`).count(), 1);
      assert.equal(await page.locator('[hidden]').textContent(), INJECTION);
      results.push(await adapter.inspect({
        origin: `${h.fixture.origin}/inject/dom`, locatorRole: 'status', locatorName: 'DOM ready',
      }));
    }));
  },
  async 'a11y-injection'(h) {
    await unchangedByUntrustedContent(h, () => withProductionAdapter(h, async (adapter, observer, results) => {
      results.push(await adapter.navigate({ origin: `${h.fixture.origin}/inject/a11y` }));
      const page = observer.contexts[0].pages()[0];
      assert.equal(await page.getByRole('button', { name: INJECTION }).count(), 1);
      results.push(await adapter.inspect({
        origin: `${h.fixture.origin}/inject/a11y`, locatorRole: 'status', locatorName: 'A11y ready',
      }));
    }));
  },
  async 'console-injection'(h) {
    await unchangedByUntrustedContent(h, () => withProductionAdapter(h, async (adapter, observer, results) => {
      results.push(await adapter.navigate({ origin: `${h.fixture.origin}/inject/console` }));
      assert.ok(observer.consoleSignals >= 1);
      results.push(await adapter.inspect({
        origin: `${h.fixture.origin}/inject/console`, locatorRole: 'status', locatorName: 'Console ready',
      }));
    }));
  },
  async 'network-injection'(h) {
    await unchangedByUntrustedContent(h, () => withProductionAdapter(h, async (adapter, observer, results) => {
      results.push(await adapter.navigate({ origin: `${h.fixture.origin}/inject/network` }));
      assert.ok(observer.networkSignals >= 1);
      results.push(await adapter.inspect({
        origin: `${h.fixture.origin}/inject/network`, locatorRole: 'status', locatorName: 'Network ready',
      }));
    }));
  },
  async 'download-injection'(h) {
    await unchangedByUntrustedContent(h, async () => {
      await withProductionAdapter(h, async (adapter) => {
        await assert.rejects(
          () => adapter.download({ origin: h.fixture.origin }),
          (error) => retainSanitized(h, { reasonCode: error?.code })?.reasonCode === 'DOWNLOAD_DEFAULT_DENIED',
        );
      });
      const cookie = await h.fixture.syntheticSessionCookie();
      const response = await fetch(`${h.fixture.origin}/download`, { headers: { cookie } });
      const payload = await response.text();
      assert.match(payload, new RegExp(INJECTION, 'u'));
    });
  },
  async timeout(h) {
    await resetFixture(h.fixture);
    h.timeout = await runProtectedWorkflow(h, 'op-real-timeout', { failure: 'TOOL_TIMEOUT' });
    assert.equal(h.timeout.result.reasonCode, 'WORKFLOW_VALIDATED');
    assert.equal((await fixtureState(h.fixture)).routerEnabled, false);
  },
  async crash(h) {
    await resetFixture(h.fixture);
    h.crash = await runProtectedWorkflow(h, 'op-real-crash', { failure: 'BROWSER_CRASH' });
    assert.equal(h.crash.result.reasonCode, 'WORKFLOW_VALIDATED');
    assert.equal((await fixtureState(h.fixture)).routerEnabled, false);
  },
  async 'validation-before-retry'(h) {
    assert.equal(h.timeout.mutationCalls, 1);
    assert.equal(h.timeout.factoryCalls, 2);
    assert.equal(h.crash.mutationCalls, 1);
    assert.equal(h.crash.factoryCalls, 2);
  },
  async 'profile-cleanup'(h) {
    assert.equal(h.artifactCleanup, true);
    assert.ok(h.removedStateDirectories >= 4);
    assert.equal(h.closedContexts.every(Boolean), true);
    assert.ok(h.adapterCleanup.length >= 10);
    assert.equal(h.adapterCleanup.every((entry) => entry.browserClosed === 1), true);
    assert.equal(h.adapterCleanup.every((entry) => entry.contextsClosed), true);
    assert.equal(h.adapterCleanup.every((entry) => entry.contextOptions.length === 1), true);
    assert.equal(h.adapterCleanup.every((entry) => (
      entry.contextOptions[0].acceptDownloads === false
      && entry.contextOptions[0].serviceWorkers === 'block'
      && entry.contextOptions[0].storageState === undefined
    )), true);
  },
  async 'canary-absence'(h) {
    assert.equal(h.forbidden.requestCount(), 0);
    const retained = JSON.stringify({
      results: h.retainedResults,
      state: await fixtureState(h.fixture),
      cleanup: { directories: h.removedStateDirectories, artifactCleanup: h.artifactCleanup },
    });
    assert.doesNotMatch(retained, new RegExp(PASSWORD, 'u'));
    assert.doesNotMatch(retained, new RegExp(TOTP, 'u'));
    assert.doesNotMatch(retained, new RegExp(INJECTION, 'u'));
  },
});


test('every approved real-browser scenario has an executable assertion', () => {
  assert.equal(REAL_BROWSER_MATRIX.length, 37);
  assert.equal(new Set(REAL_BROWSER_MATRIX).size, REAL_BROWSER_MATRIX.length);
  assert.deepEqual(Object.keys(REAL_BROWSER_SCENARIOS).sort(), [...REAL_BROWSER_MATRIX].sort());
  for (const scenario of REAL_BROWSER_MATRIX) {
    assert.equal(typeof REAL_BROWSER_SCENARIOS[scenario], 'function', scenario);
  }
  const classified = [
    ...REAL_BROWSER_EVIDENCE_CLASS.adapter,
    ...REAL_BROWSER_EVIDENCE_CLASS.runner,
    ...REAL_BROWSER_EVIDENCE_CLASS['fixture-only-support'],
  ];
  assert.deepEqual([...new Set(classified)].sort(), [...REAL_BROWSER_MATRIX].sort());
  assert.deepEqual(REAL_BROWSER_EVIDENCE_CLASS['http-fallback'], ['public-read']);
});


test('test-only real adapter override accepts only bounded Playwright module and browser channel', async () => {
  const previousModule = process.env.P004B_PLAYWRIGHT_TEST_MODULE;
  const previousChannel = process.env.P004B_BROWSER_TEST_CHANNEL;
  process.env.P004B_PLAYWRIGHT_TEST_MODULE = path.join(os.tmpdir(), 'untrusted-runtime.mjs');
  process.env.P004B_BROWSER_TEST_CHANNEL = 'arbitrary-browser';
  try {
    const selected = await resolveTestAdapter({ options: { allowedOrigins: ['http://127.0.0.1:43111'] } });
    assert.equal(selected.state, 'UNAVAILABLE');
    assert.equal(selected.reasonCode, 'CAPABILITY_UNAVAILABLE');
  } finally {
    if (previousModule === undefined) delete process.env.P004B_PLAYWRIGHT_TEST_MODULE;
    else process.env.P004B_PLAYWRIGHT_TEST_MODULE = previousModule;
    if (previousChannel === undefined) delete process.env.P004B_BROWSER_TEST_CHANNEL;
    else process.env.P004B_BROWSER_TEST_CHANNEL = previousChannel;
  }
});


test('opt-in production adapter executes and asserts all 37 loopback scenarios', async (t) => {
  if (process.env.P004B_RUN_REAL_BROWSER !== '1') {
    t.skip('CAPABILITY_UNAVAILABLE');
    return;
  }
  const runtime = await loadTestRuntime();
  if (!runtime) {
    t.skip('CAPABILITY_UNAVAILABLE');
    return;
  }
  const forbidden = await startForbiddenBrowserOrigin();
  const fixture = await startBrowserFixture({
    password: PASSWORD, totp: TOTP, forbiddenOrigin: forbidden.origin,
  });
  const selected = await resolveTestAdapter({ options: { allowedOrigins: [fixture.origin] } });
  if (selected.state !== 'ACTIVE') {
    await fixture.close();
    t.skip('CAPABILITY_UNAVAILABLE');
    return;
  }
  const channel = process.env.P004B_BROWSER_TEST_CHANNEL;
  const browser = await runtime.chromium.launch(channel ? { headless: true, channel } : { headless: true });
  const harness = {
    fixture, forbidden, runtime, browser, authTrace: null, change: null, compensation: null,
    timeout: null, crash: null, artifactCleanup: false, closedContexts: [],
    removedStateDirectories: 0, retainedResults: [], adapterCleanup: [],
  };
  const executed = [];
  try {
    for (const scenario of REAL_BROWSER_MATRIX) {
      await t.test(scenario, async () => {
        await REAL_BROWSER_SCENARIOS[scenario](harness);
        executed.push(scenario);
      });
    }
    assert.deepEqual(executed, REAL_BROWSER_MATRIX);
  } finally {
    await browser.close();
    await fixture.close();
    await forbidden.close();
  }
});
