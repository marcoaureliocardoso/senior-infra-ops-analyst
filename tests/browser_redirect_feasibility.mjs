// F0 only: synthetic candidate, never native or production qualification.
import { normalizeOrigin } from '../skills/browser-operations/scripts/browser-contract.mjs';
import { isOperationLifetime } from '../skills/browser-operations/scripts/browser-operation-lifetime.mjs';
import { PROBE_LIMITS } from './browser_redirect_protocol.mjs';

const LABEL = /^[A-Za-z0-9._:-]{1,256}$/u;
const RESOURCE_TYPES = new Set(['Document', 'Image', 'Script', 'Fetch', 'XHR', 'Stylesheet', 'Font']);
const object = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
const identity = (path, id) => JSON.stringify([...path, id]);
const error = (code) => Object.assign(new Error(code), { code });
const probes = new WeakSet();

export function createRedirectProbe({ router, lifetime, ownership, allowedOrigins, closeOwnedContext }) {
  if (!isOperationLifetime(lifetime) || !Object.isFrozen(ownership)
      || !['contextId', 'targetId', 'frameId'].every((field) => typeof ownership[field] === 'string' && LABEL.test(ownership[field]))
      || typeof closeOwnedContext !== 'function' || !Array.isArray(allowedOrigins)
      || allowedOrigins.length < 1 || allowedOrigins.length > 16) throw error('IDENTITY_UNPROVEN');
  const owned = { ...ownership };
  const origins = new Set(allowedOrigins.map(normalizeOrigin));
  if (origins.size !== allowedOrigins.length) throw error('IDENTITY_UNPROVEN');
  const targets = new Map();
  const frames = new Map();
  const networks = new Map();
  const navigations = new Map();
  const loaders = new Set();
  const requests = new Set();
  const paused = new Map();
  let state = 'NEW';
  let stepOrigin = null;
  let reasonCode = null;
  let cleanup = 'PENDING';
  let closePromise = null;
  let unsubscribe = null;
  const checks = { routing: false, startupOrder: false, recursiveTargets: false,
    perHopAdmission: false, lifetime: false, singleDisposition: false, contentFree: false };

  function fail(code) {
    reasonCode ??= code;
    void close().catch(() => {});
    return error(reasonCode);
  }
  function check() {
    if (reasonCode) throw error(reasonCode);
    if (state === 'CLOSING' || state === 'CLOSED') throw error('IDENTITY_UNPROVEN');
    try { lifetime.assertLive(); checks.lifetime = true; } catch (e) {
      throw fail(e.code === 'OPERATION_EXPIRED' ? e.code : 'OPERATION_CLOCK_UNPROVEN');
    }
  }
  async function send(path, method, params) {
    check();
    const result = await router.send(path, method, params);
    check();
    return result;
  }
  function addTree(tree, target, parent = null) {
    const frame = tree?.frame;
    if (frames.size >= PROBE_LIMITS.frames) throw error('LIMIT_EXCEEDED');
    if (!object(frame) || typeof frame.id !== 'string' || !LABEL.test(frame.id)
        || frames.has(frame.id)
        || (parent !== null && frame.parentId !== parent)) throw error('IDENTITY_UNPROVEN');
    if (target.primary && parent === null && (frame.id !== owned.frameId || frame.parentId)) throw error('IDENTITY_UNPROVEN');
    if (!target.primary && parent === null && (!frames.has(frame.parentId)
        || frames.get(frame.parentId).target.id !== target.parentTarget)) throw error('IDENTITY_UNPROVEN');
    frames.set(frame.id, { target, parent: frame.parentId ?? null });
    if (tree.childFrames !== undefined && !Array.isArray(tree.childFrames)) throw error('PROTOCOL_INVALID');
    for (const child of tree.childFrames ?? []) addTree(child, target, frame.id);
  }
  async function attached(path, params) {
    const info = params.targetInfo;
    const targetPath = [...path, params.sessionId];
    const primary = path.length === 0 && info?.targetId === owned.targetId && info?.type === 'page';
    const parent = targets.get(JSON.stringify(path));
    if (!object(info) || info.browserContextId !== owned.contextId
        || (!primary && (info.type !== 'iframe' || !parent?.ready || info.parentId !== parent.id))
        || targets.size >= PROBE_LIMITS.targets || [...targets.values()].some((t) => t.id === info.targetId)) {
      throw error('IDENTITY_UNPROVEN');
    }
    if (params.waitingForDebugger !== true) throw error('OWNERSHIP_CONFLICT');
    const target = { path: targetPath, id: info.targetId, primary, parentTarget: parent?.id, ready: false };
    targets.set(JSON.stringify(targetPath), target);
    await send(targetPath, 'Target.setAutoAttach', { autoAttach: true, waitForDebuggerOnStart: true, flatten: false });
    await send(targetPath, 'Fetch.enable', { patterns: [{ urlPattern: '*', requestStage: 'Request' }] });
    await send(targetPath, 'Network.enable', {});
    await send(targetPath, 'Page.enable', {});
    const tree = await send(targetPath, 'Page.getFrameTree', {});
    addTree(tree.frameTree, target);
    // Mark armed before releasing native execution, never before the ack chain.
    target.ready = true;
    await send(targetPath, 'Runtime.runIfWaitingForDebugger', {});
    if (primary) { state = 'PREPARED'; checks.startupOrder = true; }
    else checks.recursiveTargets = true;
  }
  function targetFor(path, frameId) {
    const target = targets.get(JSON.stringify(path));
    if (!target?.ready || !frames.has(frameId) || frames.get(frameId).target !== target) throw error('IDENTITY_UNPROVEN');
    return target;
  }
  function network(path, params) {
    if (stepOrigin === null) throw error('IDENTITY_UNPROVEN');
    targetFor(path, params.frameId);
    if (typeof params.requestId !== 'string' || !LABEL.test(params.requestId) || typeof params.request?.url !== 'string'
        || !RESOURCE_TYPES.has(params.type)) throw error('PROTOCOL_INVALID');
    const url = params.request.url;
    normalizeOrigin(url);
    const key = identity(path, params.requestId);
    const prior = networks.get(key);
    let hops = 1;
    if (prior) {
      if (!prior.admitted || !object(params.redirectResponse)
          || ![301, 302, 303, 307, 308].includes(params.redirectResponse.status)
          || params.redirectResponse.url !== prior.url || params.frameId !== prior.frameId
          || params.type !== prior.type) throw error('PROTOCOL_INVALID');
      hops = prior.hops + 1;
    } else if (params.redirectResponse !== undefined) throw error('PROTOCOL_INVALID');
    if (hops > PROBE_LIMITS.hops || (!prior && networks.size >= PROBE_LIMITS.pending)) throw error('LIMIT_EXCEEDED');
    networks.set(key, { url, frameId: params.frameId, type: params.type, hops, admitted: false, paused: false });
  }
  async function pausedRequest(path, params) {
    check();
    if (['responseStatusCode', 'responseErrorReason', 'responseHeaders'].some((field) => Object.hasOwn(params, field))
        || typeof params.requestId !== 'string' || !LABEL.test(params.requestId)
        || typeof params.networkId !== 'string' || !LABEL.test(params.networkId)) throw error('PROTOCOL_INVALID');
    if (stepOrigin === null) throw error('IDENTITY_UNPROVEN');
    targetFor(path, params.frameId);
    const key = identity(path, params.requestId);
    const request = networks.get(identity(path, params.networkId));
    if (requests.has(key) || !request || request.paused
        || request.frameId !== params.frameId || request.type !== params.resourceType
        || request.url !== params.request?.url) throw error('PROTOCOL_INVALID');
    if (requests.size >= PROBE_LIMITS.pending || paused.size >= PROBE_LIMITS.pending) throw error('LIMIT_EXCEEDED');
    const origin = normalizeOrigin(params.request.url);
    const mainDocument = params.resourceType === 'Document' && params.frameId === owned.frameId;
    if (!origins.has(origin) || (mainDocument && origin !== stepOrigin)) throw error('IDENTITY_UNPROVEN');
    requests.add(key); paused.set(key, { path, requestId: params.requestId }); request.paused = true;
    await send(path, 'Fetch.continueRequest', { requestId: params.requestId });
    request.admitted = true; paused.delete(key);
    if (params.resourceType === 'Document') navigations.set(params.frameId, { path: [...path], url: request.url });
    checks.perHopAdmission = true; checks.singleDisposition = true;
  }
  function navigated(path, params) {
    const frame = params.frame;
    if (!object(frame) || typeof frame.id !== 'string' || typeof frame.loaderId !== 'string'
        || !LABEL.test(frame.loaderId) || stepOrigin === null) throw error('IDENTITY_UNPROVEN');
    targetFor(path, frame.id);
    const expected = navigations.get(frame.id);
    const loader = identity(path, frame.loaderId);
    if (!expected || JSON.stringify(expected.path) !== JSON.stringify(path)
        || frame.url !== expected.url || (frame.parentId ?? null) !== frames.get(frame.id).parent
        || loaders.has(loader)) throw error('IDENTITY_UNPROVEN');
    const origin = normalizeOrigin(frame.url);
    if (!origins.has(origin) || (frame.id === owned.frameId && origin !== stepOrigin)) throw error('IDENTITY_UNPROVEN');
    if (loaders.size >= PROBE_LIMITS.frames) throw error('LIMIT_EXCEEDED');
    loaders.add(loader);
    navigations.delete(frame.id);
  }
  async function handle(event) {
    if (state === 'CLOSED' || state === 'CLOSING') return;
    if (event.method === null) { fail(event.reasonCode); return; }
    try {
      check();
      const { path, method, params } = event;
      if (method === 'Target.attachedToTarget') await attached(path, params);
      else if (method === 'Fetch.requestPaused') await pausedRequest(path, params);
      else if (method === 'Network.requestWillBeSent') network(path, params);
      else if (method === 'Network.loadingFinished' || method === 'Network.loadingFailed') {
        const key = identity(path, params.requestId);
        if (!networks.has(key) || !networks.get(key).admitted) throw error('PROTOCOL_INVALID');
        networks.delete(key);
        if (method === 'Network.loadingFailed') throw error('PROTOCOL_INVALID');
      } else if (method === 'Page.frameNavigated') navigated(path, params);
      else if (method === 'Page.frameDetached' || method === 'Page.frameAttached') throw error('IDENTITY_UNPROVEN');
      // Unused native informational events cannot create authority.
    } catch (e) {
      fail(['OPERATION_EXPIRED', 'OPERATION_CLOCK_UNPROVEN', 'IDENTITY_UNPROVEN',
        'OWNERSHIP_CONFLICT', 'LIMIT_EXCEEDED', 'PUBLIC_API_UNAVAILABLE'].includes(e.code) ? e.code : 'PROTOCOL_INVALID');
    }
  }
  async function close() {
    if (closePromise) return closePromise;
    state = 'CLOSING'; stepOrigin = null;
    router.revoke();
    closePromise = (async () => {
      let timer;
      try {
        await Promise.race([Promise.resolve().then(closeOwnedContext),
          new Promise((_, reject) => { timer = setTimeout(() => reject(error('CLEANUP_FAILED')), PROBE_LIMITS.commandMs); })]);
        cleanup = 'VERIFIED';
      } catch { cleanup = 'FAILED'; reasonCode = 'CLEANUP_FAILED'; }
      finally {
        clearTimeout(timer);
        unsubscribe?.();
        try { await router.close(); } catch { cleanup = 'FAILED'; reasonCode = 'CLEANUP_FAILED'; }
        if (reasonCode === null && router.snapshot().reasonCode !== null) reasonCode = router.snapshot().reasonCode;
        targets.clear(); frames.clear(); networks.clear(); requests.clear(); paused.clear();
        navigations.clear(); loaders.clear();
        checks.contentFree = true;
        state = 'CLOSED';
      }
    })();
    return closePromise;
  }
  const probe = Object.freeze({
    async prepare() {
      if (state !== 'NEW') throw error('IDENTITY_UNPROVEN');
      state = 'PREPARING';
      unsubscribe = router.onEvent(handle);
      try { await router.start(); checks.routing = true; } catch (e) { throw fail(e.code ?? 'PUBLIC_API_UNAVAILABLE'); }
    },
    async bindStep({ origin }) {
      check();
      const selected = normalizeOrigin(origin);
      if (state !== 'PREPARED' || !origins.has(selected) || stepOrigin !== null) throw fail('IDENTITY_UNPROVEN');
      stepOrigin = selected;
    },
    async finishStep() {
      check();
      if (stepOrigin === null || networks.size || paused.size || navigations.size) {
        fail('IDENTITY_UNPROVEN'); await close(); throw error(reasonCode);
      }
      stepOrigin = null;
    },
    close,
    snapshot() {
      return Object.freeze({ state, reasonCode, cleanup, checks: Object.freeze({ ...checks }),
        deprecatedRouting: router.snapshot().deprecatedRouting, nativeStatus: 'NOT_RUN' });
    },
  });
  probes.add(probe);
  return probe;
}

export async function finalizeRedirectProbe(probe) {
  if (!probes.has(probe)) throw error('PROTOCOL_INVALID');
  await probe.close();
  const result = probe.snapshot();
  const complete = result.reasonCode === null && result.cleanup === 'VERIFIED'
    && Object.values(result.checks).every((value) => value === true);
  return Object.freeze({ schemaVersion: 1, phase: 'F0', evidenceClass: 'SYNTHETIC_ONLY',
    nativeStatus: 'NOT_RUN', candidateStatus: complete ? 'READY_FOR_F1' : 'UNAVAILABLE',
    reasonCode: result.reasonCode ?? (complete ? 'F0_COMPLETE' : 'IDENTITY_UNPROVEN'),
    deprecatedRouting: result.deprecatedRouting, checks: result.checks, cleanup: result.cleanup });
}
