import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { pathToFileURL } from 'node:url';

import { resolveBrowserAdapter } from '../../skills/browser-operations/scripts/browser-adapters/index.mjs';
import { writePendingOperation } from '../../skills/browser-operations/scripts/browser-binding-store.mjs';
import { executeBrowserWorkflow, parseRunnerArgs } from '../../skills/browser-operations/scripts/browser-runner.mjs';
import { startBrowserFixture } from '../browser-fixture/server.mjs';


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


test('real-browser matrix inventory covers every approved scenario', () => {
  assert.equal(REAL_BROWSER_MATRIX.length, 37);
  assert.equal(new Set(REAL_BROWSER_MATRIX).size, REAL_BROWSER_MATRIX.length);
  assert.equal(typeof parseRunnerArgs, 'function');
});


function workflowToken(value) {
  return Buffer.from(JSON.stringify(value), 'utf8').toString('base64url');
}


function workflowArgs(origin) {
  return [
    '--step', 'workflow', '--operation-id', 'op-real-browser-001',
    '--session-id', 'session-real-browser-001', '--role', 'network-edge-operator',
    '--objective-ref', 'change-42', '--target', 'loopback-router',
    '--environment', 'test', '--service-origin', origin,
    '--identity-ref', 'vault:network-admin', '--credential-transport', 'vault',
    '--permission-mode', 'normal', '--action', 'navigate', '--action', 'fill',
    '--action', 'select', '--action', 'click', '--action', 'inspect',
    '--effect', 'LOW_RISK_CHANGE', '--risk', 'LOW_RISK_CHANGE',
    '--precondition-ref', 'fixture-ready', '--validation-ref', 'interface-state',
    '--compensation-ref', 'fixture-rollback', '--expires-in-seconds', '600',
    '--workflow-step', workflowToken({ step: 'navigate', origin: `${origin}/login` }),
    '--workflow-step', workflowToken({
      step: 'click', origin, locatorRole: 'link', locatorName: 'Login',
      effect: 'INTERACTIVE_STATE',
    }),
    '--workflow-step', workflowToken({
      step: 'fill', origin: `${origin}/login`, locatorRole: 'textbox',
      locatorName: 'Password', valueRef: 'env:OPS_BROWSER_VALUE_PASSWORD',
    }),
    '--workflow-step', workflowToken({
      step: 'click', origin: `${origin}/login`, locatorRole: 'button',
      locatorName: 'Continue', effect: 'INTERACTIVE_STATE',
    }),
    '--workflow-step', workflowToken({
      step: 'fill', origin: `${origin}/totp`, locatorRole: 'textbox',
      locatorName: 'Code', valueRef: 'env:OPS_BROWSER_VALUE_TOTP',
    }),
    '--workflow-step', workflowToken({
      step: 'click', origin: `${origin}/totp`, locatorRole: 'button',
      locatorName: 'Verify', effect: 'INTERACTIVE_STATE',
    }),
    '--workflow-step', workflowToken({
      step: 'select', origin: `${origin}/router`, locatorRole: 'combobox',
      locatorName: 'WAN enabled', valueRef: 'env:OPS_BROWSER_VALUE_DISABLED',
    }),
    '--workflow-step', workflowToken({
      step: 'click', origin: `${origin}/router`, locatorRole: 'button',
      locatorName: 'Save', effect: 'LOW_RISK_CHANGE',
    }),
    '--validation-step', workflowToken({ step: 'navigate', origin: `${origin}/login` }),
    '--validation-step', workflowToken({
      step: 'click', origin, locatorRole: 'link', locatorName: 'Login',
      effect: 'INTERACTIVE_STATE',
    }),
    '--validation-step', workflowToken({
      step: 'fill', origin: `${origin}/login`, locatorRole: 'textbox',
      locatorName: 'Password', valueRef: 'env:OPS_BROWSER_VALUE_PASSWORD',
    }),
    '--validation-step', workflowToken({
      step: 'click', origin: `${origin}/login`, locatorRole: 'button',
      locatorName: 'Continue', effect: 'INTERACTIVE_STATE',
    }),
    '--validation-step', workflowToken({
      step: 'fill', origin: `${origin}/totp`, locatorRole: 'textbox',
      locatorName: 'Code', valueRef: 'env:OPS_BROWSER_VALUE_TOTP',
    }),
    '--validation-step', workflowToken({
      step: 'click', origin: `${origin}/totp`, locatorRole: 'button',
      locatorName: 'Verify', effect: 'INTERACTIVE_STATE',
    }),
    '--validation-step', workflowToken({
      step: 'inspect', origin: `${origin}/router`, locatorRole: 'status',
      locatorName: 'Saved state', predicate: 'text-equals',
      expectedRef: 'env:OPS_BROWSER_VALUE_EXPECTED', expectRef: 'interface-state',
    }),
  ];
}


async function resolveTestAdapter(configuration) {
  const modulePath = process.env.P004B_PLAYWRIGHT_TEST_MODULE;
  if (!modulePath) return resolveBrowserAdapter(configuration);
  const resolvedModulePath = path.resolve(modulePath);
  const normalizedModulePath = resolvedModulePath.replaceAll('\\', '/');
  const channel = process.env.P004B_BROWSER_TEST_CHANNEL;
  if (!normalizedModulePath.endsWith('/node_modules/playwright/index.mjs')
      || (channel !== undefined && !['chrome', 'msedge'].includes(channel))) {
    return Object.freeze({ state: 'UNAVAILABLE', reasonCode: 'CAPABILITY_UNAVAILABLE', adapter: null });
  }
  const imported = await import(pathToFileURL(resolvedModulePath).href);
  const runtime = imported?.chromium ? imported : imported?.default;
  if (!runtime?.chromium || typeof runtime.chromium.launch !== 'function') {
    return Object.freeze({ state: 'UNAVAILABLE', reasonCode: 'CAPABILITY_UNAVAILABLE', adapter: null });
  }
  const injectedRuntime = Object.freeze({
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


test('opt-in production adapter completes a one-shot loopback workflow with fresh validation', async (t) => {
  if (process.env.P004B_RUN_REAL_BROWSER !== '1') {
    t.skip('CAPABILITY_UNAVAILABLE');
    return;
  }
  const fixture = await startBrowserFixture({
    password: process.env.P004B_SYNTH_PASSWORD ?? 'SYNTH_SECRET_REAL_BROWSER',
    totp: process.env.P004B_SYNTH_TOTP ?? '246810',
  });
  const stateDir = await mkdtemp(path.join(os.tmpdir(), 'browser-real-workflow-'));
  try {
    const selected = await resolveTestAdapter({
      preference: process.env.P004B_BROWSER_ADAPTER ?? 'playwright',
      options: { allowedOrigins: [fixture.origin] },
    });
    if (selected.state !== 'ACTIVE') {
      t.skip('CAPABILITY_UNAVAILABLE');
      return;
    }
    const request = parseRunnerArgs(workflowArgs(fixture.origin), Date.now());
    const env = {
      ...process.env,
      OPS_BROWSER_STATE_DIR: stateDir,
      OPS_BROWSER_ADAPTER: process.env.P004B_BROWSER_ADAPTER ?? 'playwright',
      OPS_BROWSER_VALUE_PASSWORD: process.env.P004B_SYNTH_PASSWORD ?? 'SYNTH_SECRET_REAL_BROWSER',
      OPS_BROWSER_VALUE_TOTP: process.env.P004B_SYNTH_TOTP ?? '246810',
      OPS_BROWSER_VALUE_DISABLED: 'false',
      OPS_BROWSER_VALUE_EXPECTED: 'wan-enabled:false',
    };
    writePendingOperation(request.envelope, {
      toolUseId: 'tool-real-browser-001',
      adapterId: 'protected-runner',
      routeClass: 'PROTECTED_RUNNER',
      settingsFingerprint: 'browser-runner-v1',
      permissionModes: ['normal'],
      invocationFingerprint: request.invocationFingerprint,
      capability: { state: 'PENDING_NATIVE_APPROVAL' },
    }, env, Date.now());
    const result = await executeBrowserWorkflow(request, {
      env, now: Date.now(), adapterFactory: resolveTestAdapter,
    });
    const structuralState = await (await fetch(`${fixture.origin}/api/state`)).json();
    assert.equal(result.reasonCode, 'WORKFLOW_VALIDATED', JSON.stringify({
      reasonCode: result.reasonCode,
      routerEnabled: structuralState.routerEnabled,
      revision: structuralState.revision,
    }));
    assert.doesNotMatch(JSON.stringify(result), /SYNTH_SECRET_/u);
    assert.equal(structuralState.routerEnabled, false);
  } finally {
    await rm(stateDir, { recursive: true, force: true });
    await fixture.close();
  }
});
