import assert from 'node:assert/strict';
import test from 'node:test';

import { startBrowserFixture } from '../browser-fixture/server.mjs';


const PASSWORD = 'SYNTH_SECRET_FIXTURE_PASSWORD';
const TOTP = '246810';


async function post(url, body, headers = {}) {
  return fetch(url, {
    method: 'POST', redirect: 'manual', headers: {
      'content-type': 'application/x-www-form-urlencoded', ...headers,
    }, body,
  });
}


test('fixture binds only to loopback on an ephemeral port and closes cleanly', async () => {
  await assert.rejects(() => startBrowserFixture({
    host: '0.0.0.0', password: PASSWORD, totp: TOTP,
  }), /LOOPBACK_REQUIRED/u);
  const fixture = await startBrowserFixture({ password: PASSWORD, totp: TOTP });
  try {
    assert.match(fixture.origin, /^http:\/\/(?:127\.0\.0\.1|\[::1\]):[1-9][0-9]*$/u);
    assert.equal((await fetch(`${fixture.origin}/public`)).status, 200);
  } finally {
    await fixture.close();
  }
  await assert.rejects(() => fetch(`${fixture.origin}/public`));
});


test('password TOTP and HttpOnly session protect every infrastructure UI', async () => {
  const fixture = await startBrowserFixture({ password: PASSWORD, totp: TOTP });
  try {
    for (const route of ['/router', '/firewall', '/service', '/observability']) {
      assert.equal((await fetch(`${fixture.origin}${route}`, { redirect: 'manual' })).status, 302);
    }
    const login = await post(`${fixture.origin}/login`, `password=${encodeURIComponent(PASSWORD)}`);
    assert.equal(login.status, 302);
    const preauth = login.headers.get('set-cookie');
    assert.match(preauth, /HttpOnly/u);
    assert.doesNotMatch(preauth, new RegExp(PASSWORD, 'u'));
    const totp = await post(`${fixture.origin}/totp`, `totp=${TOTP}`, { cookie: preauth });
    assert.equal(totp.status, 302);
    const session = totp.headers.get('set-cookie');
    assert.match(session, /HttpOnly/u);
    for (const route of ['/router', '/firewall', '/service', '/observability']) {
      assert.equal((await fetch(`${fixture.origin}${route}`, { headers: { cookie: session } })).status, 200);
    }
    assert.equal((await post(`${fixture.origin}/logout`, '', { cookie: session })).status, 302);
  } finally {
    await fixture.close();
  }
});


test('autosave submit change rollback upload and download expose independent structural state', async () => {
  const fixture = await startBrowserFixture({ password: PASSWORD, totp: TOTP });
  try {
    const session = await fixture.syntheticSessionCookie();
    const headers = { cookie: session };
    await post(`${fixture.origin}/router/autosave`, 'interface=wan&enabled=false', headers);
    await post(`${fixture.origin}/firewall/apply`, 'mode=deny', headers);
    await post(`${fixture.origin}/service/deploy`, 'version=2', headers);
    const upload = await fetch(`${fixture.origin}/upload`, {
      method: 'POST', headers: { ...headers, 'content-type': 'application/octet-stream' },
      body: Buffer.from('synthetic configuration'),
    });
    assert.equal(upload.status, 204);
    const state = await (await fetch(`${fixture.origin}/api/state`)).json();
    assert.deepEqual(state, {
      routerEnabled: false, firewallMode: 'deny', serviceVersion: 2,
      uploadCount: 1, revision: 3,
    });
    await post(`${fixture.origin}/rollback`, '', headers);
    assert.equal((await (await fetch(`${fixture.origin}/api/state`)).json()).revision, 0);
    const download = await fetch(`${fixture.origin}/download`, { headers });
    assert.equal(download.headers.get('content-disposition'), 'attachment; filename="fixture-config.json"');
    assert.ok(Number(download.headers.get('content-length')) < 1024);
  } finally {
    await fixture.close();
  }
});


test('redirect popup challenge drift and injection routes are deterministic and bounded', async () => {
  const fixture = await startBrowserFixture({ password: PASSWORD, totp: TOTP });
  try {
    const session = await fixture.syntheticSessionCookie();
    const headers = { cookie: session };
    const expectations = [
      ['/redirect/same-origin', 302], ['/redirect/cross-origin', 302],
      ['/popup/same-origin', 200], ['/popup/cross-origin', 200],
      ['/challenge', 409], ['/drift', 200], ['/inject/dom', 200],
      ['/inject/a11y', 200], ['/inject/console', 200], ['/inject/network', 200],
    ];
    for (const [route, status] of expectations) {
      const response = await fetch(`${fixture.origin}${route}`, { headers, redirect: 'manual' });
      assert.equal(response.status, status, route);
      assert.ok(Number(response.headers.get('content-length') ?? 0) <= 4096, route);
    }
    assert.equal((await fetch(`${fixture.origin}/redirect/same-origin`, { headers, redirect: 'manual' })).headers.get('location'), '/router');
    assert.equal((await fetch(`${fixture.origin}/redirect/cross-origin`, { headers, redirect: 'manual' })).headers.get('location'), 'https://escape.example.invalid/');
    assert.equal((await fetch(`${fixture.origin}/inject/network`, { headers })).headers.get('x-fixture-signal'), 'untrusted-network-data');
  } finally {
    await fixture.close();
  }
});


test('fixture never includes configured credential canaries in state or public responses', async () => {
  const fixture = await startBrowserFixture({ password: PASSWORD, totp: TOTP });
  try {
    const values = [
      JSON.stringify(await (await fetch(`${fixture.origin}/api/state`)).json()),
      await (await fetch(`${fixture.origin}/public`)).text(),
      JSON.stringify(fixture.structuralSummary()),
    ].join('\n');
    assert.doesNotMatch(values, new RegExp(PASSWORD, 'u'));
    assert.doesNotMatch(values, new RegExp(TOTP, 'u'));
  } finally {
    await fixture.close();
  }
});
