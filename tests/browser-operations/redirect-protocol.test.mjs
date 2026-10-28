import assert from 'node:assert/strict';
import test from 'node:test';
import { createProbeRouter } from '../browser_redirect_protocol.mjs';
import { fakeLifetime, flush, publicSession } from './redirect-protocol-helpers.mjs';

async function fixture(options = {}) {
  const clock = fakeLifetime();
  const wire = publicSession(options);
  const router = createProbeRouter(wire.session, { lifetime: clock.lifetime });
  await router.start();
  wire.attach();
  return { ...clock, ...wire, router };
}

test('nested command waits for child acknowledgment', async () => {
  const f = await fixture({ autoReply: false });
  let settled = false;
  const pending = f.router.send(['child-1'], 'Fetch.enable', { patterns: [{ requestStage: 'Request' }] })
    .then(() => { settled = true; });
  await flush();
  assert.equal(settled, false);
  const call = f.calls.at(-1);
  assert.equal(call.method, 'Fetch.enable');
  f.reply(call);
  await pending;
  assert.equal(settled, true);
  assert.equal(f.router.snapshot().pendingCommands, 0);
  await f.router.close();
});

test('cross-session response cannot resolve a command', async () => {
  const f = await fixture({ autoReply: false });
  f.attach([], { sessionId: 'child-2', targetInfo: { targetId: 'page-2', type: 'page' } });
  const pending = f.router.send(['child-1'], 'Fetch.enable', {}).catch((e) => e.code);
  await flush();
  f.emitAt(['child-2'], { id: f.calls.at(-1).id, result: {} });
  assert.equal(await pending, 'PROTOCOL_INVALID');
  assert.equal(f.router.snapshot().state, 'FAILED');
  await f.router.close();
});

test('unknown response cannot restore a failed router', async () => {
  const f = await fixture();
  f.emitAt(['child-1'], { id: 990, result: {} });
  f.emitAt(['child-1'], { id: 991, result: {} });
  await assert.rejects(f.router.send(['child-1'], 'Fetch.enable', {}), { code: 'PROTOCOL_INVALID' });
  assert.equal(f.router.snapshot().reasonCode, 'PROTOCOL_INVALID');
  await f.router.close();
});

test('duplicate child reply fails closed', async () => {
  const f = await fixture();
  await f.router.send(['child-1'], 'Fetch.enable', {});
  f.reply(f.calls.at(-1));
  assert.equal(f.router.snapshot().reasonCode, 'PROTOCOL_INVALID');
  await f.router.close();
});

test('bounded malformed messages never reach listeners', async () => {
  for (const message of ['{"id":1,"id":2,"result":{}}', '{"id":', ' '.repeat(16_385)]) {
    const f = await fixture();
    let delivered = 0;
    f.router.onEvent((event) => { if (event.method) delivered += 1; });
    f.session.emit('Target.receivedMessageFromTarget', { sessionId: 'child-1', message });
    assert.equal(delivered, 0);
    assert.equal(f.router.snapshot().state, 'FAILED');
    await f.router.close();
  }
});

test('unlisted command never dispatches', async () => {
  const f = await fixture();
  const before = f.calls.length;
  await assert.rejects(f.router.send(['child-1'], 'Page.navigate', { url: 'http://127.0.0.1/' }),
    { code: 'PROTOCOL_INVALID' });
  assert.equal(f.calls.length, before);
  await f.router.close();
});

test('expiry prevents the next public send', async () => {
  const f = await fixture();
  f.expire();
  const before = f.calls.length;
  await assert.rejects(f.router.send(['child-1'], 'Fetch.enable', {}), { code: 'OPERATION_EXPIRED' });
  assert.equal(f.calls.length, before);
  await f.router.close();
});

test('recursive routing uses acknowledged public envelopes', async () => {
  const f = await fixture();
  f.attach(['child-1'], { sessionId: 'frame-session', targetInfo: { targetId: 'frame-target', type: 'iframe' } });
  await f.router.send(['child-1', 'frame-session'], 'Network.enable', {});
  const nested = f.calls.at(-1);
  assert.deepEqual(nested.path, ['child-1', 'frame-session']);
  assert.equal(nested.method, 'Network.enable');
  assert.equal(f.router.snapshot().deprecatedRouting, true);
  await f.router.close();
  assert.equal(f.session.eventNames().length, 0);
});

test('detached session identity cannot be reused', async () => {
  const f = await fixture();
  f.session.emit('Target.detachedFromTarget', { sessionId: 'child-1' });
  f.attach();
  await assert.rejects(f.router.send(['child-1'], 'Fetch.enable', {}), { code: 'IDENTITY_UNPROVEN' });
  await f.router.close();
});

test('missing acknowledgment times out and close cancels pending work', async () => {
  const f = await fixture({ autoReply: false });
  const pending = f.router.send(['child-1'], 'Fetch.enable', {}).catch((e) => e.code);
  assert.equal(await pending, 'LIMIT_EXCEEDED');
  assert.equal(f.router.snapshot().pendingCommands, 0);
  await f.router.close();
  const g = await fixture({ autoReply: false });
  const canceled = g.router.send(['child-1'], 'Fetch.enable', {}).catch((e) => e.code);
  await g.router.close();
  assert.equal(await canceled, 'IDENTITY_UNPROVEN');
  assert.equal(g.router.snapshot().pendingCommands, 0);
});

test('target and message budgets are finite and total deadline closes admission', async () => {
  const f = await fixture();
  for (let i = 2; i <= 9; i += 1) f.attach([], { sessionId: `child-${i}` });
  assert.equal(f.router.snapshot().reasonCode, 'LIMIT_EXCEEDED');
  await f.router.close();
  const g = await fixture();
  for (let i = 0; i < 520; i += 1) g.emitAt(['child-1'], { method: 'Page.lifecycleEvent', params: { name: 'init' } });
  assert.equal(g.router.snapshot().reasonCode, 'LIMIT_EXCEEDED');
  assert.equal(g.router.snapshot().messages, 513);
  await g.router.close();
  const h = await fixture();
  await new Promise((resolve) => setTimeout(resolve, 5_030));
  assert.equal(h.router.snapshot().reasonCode, 'LIMIT_EXCEEDED');
  await h.router.close();
});
