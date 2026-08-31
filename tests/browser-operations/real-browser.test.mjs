import assert from 'node:assert/strict';
import test from 'node:test';

import { resolveBrowserAdapter } from '../../skills/browser-operations/scripts/browser-adapters/index.mjs';
import { parseRunnerArgs } from '../../skills/browser-operations/scripts/browser-runner.mjs';
import { startBrowserFixture } from '../browser-fixture/server.mjs';


export const REAL_BROWSER_MATRIX = Object.freeze([
  'public-read', 'authenticated-read', 'existing-session', 'password', 'totp', 'logout',
  'fill-without-submit', 'autosave', 'submit', 'state-changing-click', 'change',
  'independent-validation', 'compensation', 'upload', 'download', 'screenshot', 'trace',
  'same-origin-redirect', 'cross-origin-redirect', 'same-origin-popup',
  'cross-origin-popup', 'new-tab', 'subresource-origin', 'ui-drift', 'missing-locator',
  'human-challenge', 'dom-injection', 'a11y-injection', 'console-injection',
  'network-injection', 'download-injection', 'timeout', 'crash',
  'validation-before-retry', 'profile-cleanup', 'canary-absence',
]);


test('real-browser matrix inventory covers every approved scenario', () => {
  assert.equal(REAL_BROWSER_MATRIX.length, 36);
  assert.equal(new Set(REAL_BROWSER_MATRIX).size, REAL_BROWSER_MATRIX.length);
  assert.equal(typeof parseRunnerArgs, 'function');
});


test('opt-in production adapter performs a loopback structural smoke', async (t) => {
  if (process.env.P004B_RUN_REAL_BROWSER !== '1') {
    t.skip('CAPABILITY_UNAVAILABLE');
    return;
  }
  const fixture = await startBrowserFixture({
    password: process.env.P004B_SYNTH_PASSWORD ?? 'SYNTH_SECRET_REAL_BROWSER',
    totp: process.env.P004B_SYNTH_TOTP ?? '246810',
  });
  let adapter = null;
  try {
    const selected = await resolveBrowserAdapter({
      preference: process.env.P004B_BROWSER_ADAPTER ?? 'playwright',
      options: { allowedOrigins: [fixture.origin] },
    });
    if (selected.state !== 'ACTIVE') {
      t.skip('CAPABILITY_UNAVAILABLE');
      return;
    }
    adapter = selected.adapter;
    await adapter.open();
    assert.equal((await adapter.navigate({ origin: fixture.origin })).status, 'ok');
    const observed = await adapter.inspect({ locatorRole: 'status', locatorName: 'Fixture ready' });
    assert.equal(observed.observation, 'element-present');
    assert.doesNotMatch(JSON.stringify(observed), /SYNTH_SECRET_/u);
  } finally {
    await adapter?.close?.();
    await fixture.close();
  }
});
