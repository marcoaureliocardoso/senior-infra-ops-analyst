import assert from 'node:assert/strict';
import test from 'node:test';
import { createProbeRouter } from '../browser_redirect_protocol.mjs';
import { createRedirectProbe, finalizeRedirectProbe } from '../browser_redirect_feasibility.mjs';
import { spawnSync } from 'node:child_process';
import { mkdtemp, readdir, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { fakeLifetime, flush, publicSession } from './redirect-protocol-helpers.mjs';

const ORIGIN = 'http://127.0.0.1:43111';
const CDN = 'http://127.0.0.1:43112';
const FORBIDDEN = 'http://127.0.0.1:43113';
const PRIMARY = ['child-1'];

async function fixture({ autoReply = true, closeOwnedContext, frameCount = 1, afterEnqueue } = {}) {
  const clock = fakeLifetime();
  let closed = 0;
  const wire = publicSession({ autoReply, response(method, _params, path) {
    return method === 'Page.getFrameTree' ? { frameTree: { frame: path.length === 1
      ? { id: 'frame-1', url: `${ORIGIN}/` }
      : { id: 'frame-2', parentId: 'frame-1', url: `${ORIGIN}/child` },
    ...(path.length === 1 && frameCount > 1 ? { childFrames: Array.from({ length: frameCount - 1 }, (_, i) => ({
      frame: { id: `nested-${i}`, parentId: 'frame-1', url: `${ORIGIN}/child` },
    })) } : {}) } } : {};
  } });
  const transport = createProbeRouter(wire.session, { lifetime: clock.lifetime });
  const router = afterEnqueue ? { ...transport, send(...args) {
    const result = transport.send(...args);
    afterEnqueue(wire, args);
    return result;
  } } : transport;
  const probe = createRedirectProbe({ router, lifetime: clock.lifetime,
    ownership: Object.freeze({ contextId: 'context-1', targetId: 'page-1', frameId: 'frame-1' }),
    allowedOrigins: [ORIGIN, CDN], closeOwnedContext: closeOwnedContext ?? (async () => { closed += 1; }) });
  await probe.prepare();
  wire.attach();
  await flush();
  return { ...wire, ...clock, router, probe, closed: () => closed };
}

function request(f, { id = 'request-1', networkId = 'network-1', url = `${ORIGIN}/a`,
  type = 'Document', frameId = 'frame-1', path = PRIMARY, previous = null } = {}) {
  f.emitAt(path, { method: 'Network.requestWillBeSent', params: {
    requestId: networkId, frameId, type, request: { url },
    ...(previous ? { redirectResponse: { status: 302, url: previous } } : {}),
  } });
  f.emitAt(path, { method: 'Fetch.requestPaused', params: {
    requestId: id, networkId, frameId, resourceType: type, request: { url },
  } });
}
function completed(f, networkId = 'network-1', path = PRIMARY) {
  f.emitAt(path, { method: 'Network.loadingFinished', params: { requestId: networkId, encodedDataLength: 0 } });
}
const continuations = (f) => f.calls.filter((c) => c.method === 'Fetch.continueRequest');

test('target remains paused until interception acknowledgment', async () => {
  const f = await fixture({ autoReply: false });
  assert.equal(f.calls.some((c) => c.method === 'Runtime.runIfWaitingForDebugger'), false);
  assert.equal(f.probe.snapshot().checks.startupOrder, false);
  await f.probe.close();
});

test('nested child is armed before release', async () => {
  const f = await fixture();
  f.attach(PRIMARY, { sessionId: 'iframe-1', targetInfo: {
    targetId: 'frame-target-1', type: 'iframe', browserContextId: 'context-1', parentId: 'page-1' } });
  await flush();
  const calls = f.calls.filter((c) => c.path.length === 2 && c.method !== 'Target.sendMessageToTarget');
  assert.deepEqual(calls.map((c) => c.method), ['Target.setAutoAttach', 'Fetch.enable', 'Network.enable',
    'Page.enable', 'Page.getFrameTree', 'Runtime.runIfWaitingForDebugger']);
  assert.equal(f.probe.snapshot().checks.recursiveTargets, true);
  await f.probe.close();
});

test('unowned and popup worker targets never resume', async () => {
  for (const targetInfo of [
    { targetId: 'other-page', type: 'page', browserContextId: 'context-1' },
    { targetId: 'other-worker', type: 'worker', browserContextId: 'context-1' },
    { targetId: 'foreign-frame', type: 'iframe', browserContextId: 'other-context' },
  ]) {
    const f = await fixture();
    f.attach(PRIMARY, { sessionId: 'unowned', targetInfo });
    await flush();
    assert.equal(f.calls.some((c) => c.path.includes('unowned') && c.method === 'Runtime.runIfWaitingForDebugger'), false);
    assert.equal(f.probe.snapshot().reasonCode, 'IDENTITY_UNPROVEN');
    assert.equal(f.closed(), 1);
    await f.probe.close();
  }
});

test('late frame migration loses authority', async () => {
  const f = await fixture();
  await f.probe.bindStep({ origin: ORIGIN });
  f.emitAt(PRIMARY, { method: 'Page.frameDetached', params: { frameId: 'frame-1', reason: 'swap' } });
  request(f);
  await flush();
  assert.equal(continuations(f).length, 0);
  assert.equal(f.probe.snapshot().reasonCode, 'IDENTITY_UNPROVEN');
  await f.probe.close();
});

test('each allowed redirect hop receives one unmodified continuation', async () => {
  for (const type of ['Document', 'Image', 'Script', 'Fetch', 'XHR']) {
    const f = await fixture();
    await f.probe.bindStep({ origin: ORIGIN });
    const base = type === 'Document' ? ORIGIN : CDN;
    for (let i = 0; i < 3; i += 1) {
      request(f, { id: `request-${i}`, url: `${base}/${i}`, type,
        previous: i ? `${base}/${i - 1}` : null });
      await flush();
    }
    assert.deepEqual(continuations(f).map((c) => c.params), [
      { requestId: 'request-0' }, { requestId: 'request-1' }, { requestId: 'request-2' },
    ]);
    if (type === 'Document') f.emitAt(PRIMARY, { method: 'Page.frameNavigated', params: {
      frame: { id: 'frame-1', url: `${base}/2`, loaderId: 'loader-final' } } });
    completed(f);
    await f.probe.finishStep();
    await f.probe.close();
  }
});

test('forbidden second and third hops receive none', async () => {
  for (const length of [2, 3]) {
    const f = await fixture();
    await f.probe.bindStep({ origin: ORIGIN });
    for (let i = 0; i < length; i += 1) {
      request(f, { id: `r-${i}`, url: `${i === length - 1 ? FORBIDDEN : CDN}/${i}`,
        type: 'Fetch', previous: i ? `${CDN}/${i - 1}` : null });
      await flush();
    }
    assert.equal(continuations(f).length, length - 1);
    assert.equal(f.probe.snapshot().reasonCode, 'IDENTITY_UNPROVEN');
    assert.equal(f.closed(), 1);
    await f.probe.close();
  }
});

test('main document cannot switch to another approved origin', async () => {
  const f = await fixture();
  await f.probe.bindStep({ origin: ORIGIN });
  request(f, { url: `${CDN}/login` });
  await flush();
  assert.equal(continuations(f).length, 0);
  await f.probe.close();
});

test('expired pending authorization cannot continue', async () => {
  const f = await fixture();
  await f.probe.bindStep({ origin: ORIGIN });
  f.expire();
  request(f);
  await flush();
  assert.equal(continuations(f).length, 0);
  assert.equal(f.probe.snapshot().reasonCode, 'OPERATION_EXPIRED');
  await f.probe.close();
});

test('competing owner symptom is sticky failure not a fabricated native event', async () => {
  const clock = fakeLifetime();
  const wire = publicSession();
  const router = createProbeRouter(wire.session, { lifetime: clock.lifetime });
  const probe = createRedirectProbe({ router, lifetime: clock.lifetime,
    ownership: Object.freeze({ contextId: 'context-1', targetId: 'page-1', frameId: 'frame-1' }),
    allowedOrigins: [ORIGIN], closeOwnedContext: async () => {} });
  await probe.prepare();
  wire.attach([], { waitingForDebugger: false });
  await flush();
  assert.equal(probe.snapshot().reasonCode, 'OWNERSHIP_CONFLICT');
  assert.equal(wire.calls.some((c) => c.method === 'Runtime.runIfWaitingForDebugger'), false);
  await probe.close();
});

test('between-step traffic is denied and unresolved work prevents unbinding', async () => {
  const f = await fixture();
  request(f);
  await flush();
  assert.equal(continuations(f).length, 0);
  await f.probe.close();
  const g = await fixture();
  await g.probe.bindStep({ origin: ORIGIN });
  request(g);
  await flush();
  await assert.rejects(g.probe.finishStep(), { code: 'IDENTITY_UNPROVEN' });
  assert.equal(g.closed(), 1);
  await g.probe.close();
});

test('unknown frame duplicate disposition and malformed correlation fail closed', async () => {
  for (const mutation of ['frame', 'duplicate', 'correlation']) {
    const f = await fixture();
    await f.probe.bindStep({ origin: ORIGIN });
    if (mutation !== 'correlation') request(f, { frameId: mutation === 'frame' ? 'unknown-frame' : 'frame-1' });
    await flush();
    f.emitAt(PRIMARY, { method: 'Fetch.requestPaused', params: {
      requestId: 'request-1', networkId: 'network-1', frameId: 'frame-1',
      resourceType: 'Document', request: { url: `${ORIGIN}/a` } } });
    await flush();
    assert.equal(continuations(f).length, mutation === 'duplicate' ? 1 : 0);
    assert.notEqual(f.probe.snapshot().reasonCode, null);
    await f.probe.close();
  }
});

test('redirect loop is bounded at twenty admitted hops', async () => {
  const f = await fixture();
  await f.probe.bindStep({ origin: ORIGIN });
  for (let i = 0; i < 21; i += 1) {
    request(f, { id: `r-${i}`, url: `${ORIGIN}/${i % 2}`, previous: i ? `${ORIGIN}/${(i - 1) % 2}` : null });
    await flush();
  }
  assert.equal(continuations(f).length, 20);
  assert.equal(f.probe.snapshot().reasonCode, 'LIMIT_EXCEEDED');
  await f.probe.close();
});

test('concurrent distinct requests require independent completion', async () => {
  const f = await fixture();
  await f.probe.bindStep({ origin: ORIGIN });
  request(f, { id: 'a', networkId: 'net-a', type: 'Fetch' });
  request(f, { id: 'b', networkId: 'net-b', type: 'XHR' });
  await flush();
  assert.equal(continuations(f).length, 2);
  completed(f, 'net-a'); completed(f, 'net-b');
  await f.probe.finishStep();
  await f.probe.close();
  assert.equal(f.probe.snapshot().reasonCode, null);
});

test('sixty-four admitted request identities bound the step', async () => {
  const f = await fixture();
  await f.probe.bindStep({ origin: ORIGIN });
  for (let i = 0; i < 65; i += 1) {
    request(f, { id: `r-${i}`, networkId: `n-${i}`, type: 'Image' });
    await flush();
  }
  assert.equal(continuations(f).length, 64);
  assert.equal(f.probe.snapshot().reasonCode, 'LIMIT_EXCEEDED');
  await f.probe.close();
});

async function completedCandidate(options = {}) {
  const f = await fixture(options);
  f.attach(PRIMARY, { sessionId: 'iframe-1', targetInfo: {
    targetId: 'frame-target-1', type: 'iframe', browserContextId: 'context-1', parentId: 'page-1' } });
  await flush();
  await f.probe.bindStep({ origin: ORIGIN });
  request(f);
  await flush();
  f.emitAt(PRIMARY, { method: 'Page.frameNavigated', params: {
    frame: { id: 'frame-1', url: `${ORIGIN}/a`, loaderId: 'loader-final' } } });
  completed(f);
  await f.probe.finishStep();
  return f;
}

test('finalization cannot promote synthetic evidence', async () => {
  const f = await completedCandidate();
  const report = await finalizeRedirectProbe(f.probe);
  assert.deepEqual(report, {
    schemaVersion: 1, phase: 'F0', evidenceClass: 'SYNTHETIC_ONLY', nativeStatus: 'NOT_RUN',
    candidateStatus: 'READY_FOR_F1', reasonCode: 'F0_COMPLETE', deprecatedRouting: true,
    checks: { routing: true, startupOrder: true, recursiveTargets: true, perHopAdmission: true,
      lifetime: true, singleDisposition: true, contentFree: true }, cleanup: 'VERIFIED',
  });
  assert.equal(Object.isFrozen(report), true);
  assert.equal(f.closed(), 1);
});

test('late timeout taints provisional ready', async () => {
  const f = await completedCandidate();
  f.setAutoReply(false);
  await assert.rejects(f.router.send(PRIMARY, 'Fetch.enable', {}), { code: 'LIMIT_EXCEEDED' });
  const report = await finalizeRedirectProbe(f.probe);
  assert.equal(report.candidateStatus, 'UNAVAILABLE');
  assert.equal(report.reasonCode, 'LIMIT_EXCEEDED');
});

test('failed owned cleanup dominates', async () => {
  const f = await completedCandidate({ closeOwnedContext: async () => { throw new Error('private cleanup detail'); } });
  const report = await finalizeRedirectProbe(f.probe);
  assert.equal(report.cleanup, 'FAILED');
  assert.equal(report.reasonCode, 'CLEANUP_FAILED');
  assert.equal(report.candidateStatus, 'UNAVAILABLE');
  assert.equal(JSON.stringify(report).includes('private cleanup detail'), false);
});

test('published shape rejects content unknown fields and foreign probes', async () => {
  const f = await fixture();
  await f.probe.bindStep({ origin: ORIGIN });
  f.emitAt(PRIMARY, { method: 'Network.requestWillBeSent', params: { requestId: 'n-1', frameId: 'frame-1',
    type: 'Fetch', request: { url: `${ORIGIN}/a`, headers: { 'private-field': 'synthetic private value' } } } });
  f.emitAt(PRIMARY, { method: 'Fetch.requestPaused', params: { requestId: 'r-1', networkId: 'n-1',
    frameId: 'frame-1', resourceType: 'Fetch', request: { url: `${ORIGIN}/a`, postData: 'synthetic private value' } } });
  await flush();
  completed(f, 'n-1');
  await f.probe.finishStep();
  const report = await finalizeRedirectProbe(f.probe);
  assert.deepEqual(Object.keys(report).sort(), ['candidateStatus', 'checks', 'cleanup', 'deprecatedRouting',
    'evidenceClass', 'nativeStatus', 'phase', 'reasonCode', 'schemaVersion']);
  const text = JSON.stringify(report);
  for (const forbidden of ['synthetic private value', 'frame-1', 'context-1', 'requestId', ORIGIN, 'ACTIVE']) {
    assert.equal(text.includes(forbidden), false);
  }
  await assert.rejects(finalizeRedirectProbe({ ...f.probe, extra: true }), { code: 'PROTOCOL_INVALID' });
});

test('import has no I/O in a permission-restricted child', async () => {
  const root = fileURLToPath(new URL('../../', import.meta.url));
  const directory = await mkdtemp(path.join(os.tmpdir(), 'redirect-import-'));
  try {
    const code = `import { registerHooks } from 'node:module';
      registerHooks({ resolve(specifier, context, next) {
        if (/^(?:node:)?(?:net|http|https|dns|dgram|tls)$/.test(specifier)
            || /playwright|puppeteer/.test(specifier)) throw new Error('FORBIDDEN_IMPORT');
        return next(specifier, context);
      }});
      globalThis.fetch = () => { throw new Error('FORBIDDEN_FETCH'); };
      await import(${JSON.stringify(new URL('../browser_redirect_feasibility.mjs', import.meta.url).href)});
      process.stdout.write('IMPORT_ONLY');`;
    const result = spawnSync(process.execPath, ['--permission', `--allow-fs-read=${root}`,
      '--input-type=module', '--eval', code], { cwd: directory, encoding: 'utf8', timeout: 10_000,
      env: { PATH: '/usr/bin:/bin', HOME: directory } });
    assert.equal(result.status, 0, 'restricted import must exit cleanly');
    assert.equal(result.stdout, 'IMPORT_ONLY');
    assert.equal(result.stderr, '');
    assert.deepEqual(await readdir(directory), []);
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('frame ancestry is bounded to sixty-four entries', async () => {
  const f = await fixture({ frameCount: 64 });
  assert.equal(f.probe.snapshot().checks.startupOrder, true);
  await f.probe.close();
  const g = await fixture({ frameCount: 65 });
  assert.equal(g.probe.snapshot().reasonCode, 'LIMIT_EXCEEDED');
  assert.equal(g.calls.some((c) => c.method === 'Runtime.runIfWaitingForDebugger'), false);
  await g.probe.close();
});

test('I1 revocation cancels a queued continuation before native dispatch', async () => {
  let release;
  const f = await fixture({ closeOwnedContext: () => new Promise((resolve) => { release = resolve; }) });
  await f.probe.bindStep({ origin: ORIGIN });
  request(f);
  assert.equal(continuations(f).length, 0);
  f.emitAt(PRIMARY, { method: 'Page.frameDetached', params: { frameId: 'frame-1', reason: 'swap' } });
  await flush();
  assert.equal(continuations(f).length, 0);
  release();
  await f.probe.close();
});

test('I1 revocation cancels a queued target resume before native dispatch', async () => {
  const f = await fixture({ afterEnqueue(wire, [, method]) {
    if (method === 'Runtime.runIfWaitingForDebugger') {
      wire.emitAt(PRIMARY, { method: 'Page.frameDetached', params: { frameId: 'frame-1', reason: 'swap' } });
    }
  } });
  assert.equal(f.calls.some((c) => c.method === 'Runtime.runIfWaitingForDebugger'), false);
  await f.probe.close();
});

test('I3 expected owned detach during context close preserves successful finalization', async () => {
  let wire;
  const f = await completedCandidate({ closeOwnedContext: async () => {
    wire.emitAt(PRIMARY, { method: 'Target.detachedFromTarget', params: { sessionId: 'iframe-1' } });
    wire.session.emit('Target.detachedFromTarget', { sessionId: 'child-1' });
  } });
  wire = f;
  const report = await finalizeRedirectProbe(f.probe);
  assert.equal(report.cleanup, 'VERIFIED');
  assert.equal(report.candidateStatus, 'READY_FOR_F1');
  assert.equal(report.reasonCode, 'F0_COMPLETE');
});

test('I2 response-stage pauses and non-string identities never continue', async () => {
  for (const variant of ['status', 'response-error', 'fetch-number', 'fetch-missing',
    'network-number', 'network-missing', 'fetch-network-number', 'fetch-network-missing']) {
    const f = await fixture();
    await f.probe.bindStep({ origin: ORIGIN });
    const network = { requestId: 'network-1', frameId: 'frame-1', type: 'Document', request: { url: `${ORIGIN}/a` } };
    const pause = { requestId: 'request-1', networkId: 'network-1', frameId: 'frame-1',
      resourceType: 'Document', request: { url: `${ORIGIN}/a` } };
    if (variant === 'status') pause.responseStatusCode = 200;
    if (variant === 'response-error') pause.responseErrorReason = 'Failed';
    if (variant === 'fetch-number') pause.requestId = 123;
    if (variant === 'fetch-missing') delete pause.requestId;
    if (variant === 'network-number') { network.requestId = 123; pause.networkId = 123; }
    if (variant === 'network-missing') delete network.requestId;
    if (variant === 'fetch-network-number') pause.networkId = 123;
    if (variant === 'fetch-network-missing') delete pause.networkId;
    f.emitAt(PRIMARY, { method: 'Network.requestWillBeSent', params: network });
    f.emitAt(PRIMARY, { method: 'Fetch.requestPaused', params: pause });
    await flush();
    assert.equal(continuations(f).length, 0, variant);
    assert.equal(f.probe.snapshot().checks.perHopAdmission, false, variant);
    await f.probe.close();
  }
});

test('I4 admitted same-owned-frame navigation preserves identity once', async () => {
  const f = await fixture();
  await f.probe.bindStep({ origin: ORIGIN });
  request(f);
  await flush();
  const navigation = { method: 'Page.frameNavigated', params: {
    frame: { id: 'frame-1', url: `${ORIGIN}/a`, loaderId: 'new-loader' } } };
  f.emitAt(PRIMARY, navigation);
  await flush();
  assert.equal(f.probe.snapshot().reasonCode, null);
  completed(f);
  await f.probe.finishStep();
  await f.probe.bindStep({ origin: ORIGIN });
  f.emitAt(PRIMARY, navigation);
  await flush();
  assert.equal(f.probe.snapshot().reasonCode, 'IDENTITY_UNPROVEN');
  await f.probe.close();
});
