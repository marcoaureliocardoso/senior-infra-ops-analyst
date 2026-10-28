// Test-only public-CDP candidate. Never imported by production adapters.
import { isOperationLifetime } from '../skills/browser-operations/scripts/browser-operation-lifetime.mjs';
import { parseStrictObject } from '../skills/context-continuity/scripts/settings.mjs';

export const PROBE_LIMITS = Object.freeze({ targets: 8, frames: 64, pending: 64,
  messages: 512, bytes: 16_384, hops: 20, commandMs: 1_000, totalMs: 5_000 });
const METHODS = new Set(['Target.setAutoAttach', 'Target.closeTarget', 'Network.enable',
  'Fetch.enable', 'Fetch.continueRequest', 'Fetch.failRequest', 'Page.enable',
  'Page.getFrameTree', 'Runtime.runIfWaitingForDebugger']);
const ROOT_EVENTS = ['Target.attachedToTarget', 'Target.detachedFromTarget',
  'Target.receivedMessageFromTarget'];
const LABEL = /^[A-Za-z0-9._:-]{1,256}$/u;
const object = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
const key = (path) => JSON.stringify(path);
const failure = (code) => Object.assign(new Error(code), { code });

export function createProbeRouter(rootSession, { lifetime } = {}) {
  let state = 'NEW';
  let reasonCode = null;
  let messages = 0;
  let serial = 0;
  let deadline = null;
  const routes = new Set([key([])]);
  const seen = new Set();
  const pending = new Map();
  const listeners = new Set();
  const installed = new Map();

  function notify(event) {
    for (const listener of listeners) {
      try { Promise.resolve(listener(event)).catch(() => fail('PROTOCOL_INVALID')); }
      catch { fail('PROTOCOL_INVALID'); }
    }
  }
  function fail(code) {
    if (reasonCode !== null || state === 'CLOSED') return;
    reasonCode = code;
    state = 'FAILED';
    clearTimeout(deadline);
    for (const entry of pending.values()) { clearTimeout(entry.timer); entry.reject(failure(code)); }
    pending.clear();
    // Local transport failure, not a fabricated native protocol event.
    notify({ method: null, reasonCode: code });
  }
  function check() {
    if (reasonCode !== null) throw failure(reasonCode);
    if (state !== 'STARTED') throw failure('IDENTITY_UNPROVEN');
    try { lifetime.assertLive(); } catch (error) {
      fail(error.code === 'OPERATION_EXPIRED' ? error.code : 'OPERATION_CLOCK_UNPROVEN');
      throw failure(reasonCode);
    }
  }
  function bounded(value) {
    const text = JSON.stringify(value);
    if (typeof text !== 'string' || Buffer.byteLength(text) > PROBE_LIMITS.bytes) throw failure('LIMIT_EXCEEDED');
    return parseStrictObject(text);
  }
  function receive(path, event) {
    if (state === 'REVOKED') {
      try {
        bounded(event);
        if (++messages > PROBE_LIMITS.messages) throw failure('LIMIT_EXCEEDED');
        if (!routes.has(key(path))) throw failure('IDENTITY_UNPROVEN');
        if (event.method === 'Target.receivedMessageFromTarget') {
          const p = event.params;
          if (!object(p) || typeof p.sessionId !== 'string' || !LABEL.test(p.sessionId)
              || typeof p.message !== 'string' || Buffer.byteLength(p.message) > PROBE_LIMITS.bytes) throw failure('PROTOCOL_INVALID');
          receive([...path, p.sessionId], parseStrictObject(p.message));
        } else if (event.method === 'Target.detachedFromTarget') {
          const child = [...path, event.params?.sessionId];
          if (!routes.has(key(child))) throw failure('IDENTITY_UNPROVEN');
          for (const route of routes) {
            const parts = JSON.parse(route);
            if (child.every((id, i) => parts[i] === id)) routes.delete(route);
          }
        } else if (event.method === 'Target.attachedToTarget') throw failure('OWNERSHIP_CONFLICT');
        // Observations and late replies while closing cannot re-open admission.
      } catch (e) { fail(['IDENTITY_UNPROVEN', 'LIMIT_EXCEEDED', 'OWNERSHIP_CONFLICT'].includes(e.code) ? e.code : 'PROTOCOL_INVALID'); }
      return;
    }
    if (state !== 'STARTED') return;
    try {
      check();
      messages += 1;
      if (messages > PROBE_LIMITS.messages || path.length > PROBE_LIMITS.targets) throw failure('LIMIT_EXCEEDED');
      if (!routes.has(key(path)) || !object(event)) throw failure('IDENTITY_UNPROVEN');
      bounded(event);
      if (Object.hasOwn(event, 'id')) {
        if (!Number.isSafeInteger(event.id) || Object.hasOwn(event, 'method')
            || Object.hasOwn(event, 'result') === Object.hasOwn(event, 'error')) throw failure('PROTOCOL_INVALID');
        const entryKey = `${key(path)}:${event.id}`;
        const entry = pending.get(entryKey);
        if (!entry) throw failure('PROTOCOL_INVALID');
        if (Object.hasOwn(event, 'error')) throw failure('PUBLIC_API_UNAVAILABLE');
        if (!object(event.result)) throw failure('PROTOCOL_INVALID');
        pending.delete(entryKey);
        clearTimeout(entry.timer);
        entry.resolve(event.result);
        return;
      }
      const { method, params } = event;
      if (typeof method !== 'string' || !/^[A-Za-z]+\.[A-Za-z]+$/u.test(method) || !object(params)) throw failure('PROTOCOL_INVALID');
      if (method === 'Target.receivedMessageFromTarget') {
        if (!LABEL.test(params.sessionId) || typeof params.message !== 'string') throw failure('PROTOCOL_INVALID');
        if (Buffer.byteLength(params.message) > PROBE_LIMITS.bytes) throw failure('LIMIT_EXCEEDED');
        receive([...path, params.sessionId], parseStrictObject(params.message));
        return;
      }
      if (method === 'Target.attachedToTarget') {
        if (typeof params.sessionId !== 'string' || !LABEL.test(params.sessionId)) throw failure('IDENTITY_UNPROVEN');
        const child = key([...path, params.sessionId]);
        if (seen.has(child)) throw failure('IDENTITY_UNPROVEN');
        if (seen.size >= PROBE_LIMITS.targets) throw failure('LIMIT_EXCEEDED');
        seen.add(child);
        routes.add(child);
      } else if (method === 'Target.detachedFromTarget') {
        throw failure('IDENTITY_UNPROVEN');
      }
      notify({ path: [...path], method, params });
    } catch (error) {
      fail(['IDENTITY_UNPROVEN', 'LIMIT_EXCEEDED', 'PUBLIC_API_UNAVAILABLE',
        'OPERATION_EXPIRED', 'OPERATION_CLOCK_UNPROVEN'].includes(error.code) ? error.code : 'PROTOCOL_INVALID');
    }
  }
  async function dispatch(path, method, params, internal = false) {
    check();
    if (!Array.isArray(path) || !routes.has(key(path)) || path.some((id) => typeof id !== 'string' || !LABEL.test(id))) {
      fail('IDENTITY_UNPROVEN'); throw failure(reasonCode);
    }
    if ((!METHODS.has(method) && !(internal && method === 'Target.sendMessageToTarget')) || !object(params)) {
      fail('PROTOCOL_INVALID'); throw failure(reasonCode);
    }
    try { bounded(params); } catch { fail('LIMIT_EXCEEDED'); throw failure(reasonCode); }
    if (pending.size >= PROBE_LIMITS.pending) { fail('LIMIT_EXCEEDED'); throw failure(reasonCode); }
    const id = ++serial;
    const entryKey = `${key(path)}:${id}`;
    let entry;
    const reply = new Promise((resolve, reject) => {
      entry = { resolve, reject, timer: setTimeout(() => fail('LIMIT_EXCEEDED'),
        Math.min(PROBE_LIMITS.commandMs, lifetime.remainingMs())) };
      pending.set(entryKey, entry);
    });
    if (path.length === 0) {
      Promise.resolve().then(() => { check(); return rootSession.send(method, params); }).then((result) => {
        check();
        receive([], { id, result });
      }).catch((error) => fail(error.code === 'OPERATION_EXPIRED' ? error.code : 'PUBLIC_API_UNAVAILABLE'));
      return reply;
    }
    const delivery = dispatch(path.slice(0, -1), 'Target.sendMessageToTarget', {
      sessionId: path.at(-1), message: JSON.stringify({ id, method, params }),
    }, true);
    // Both delivery and the actual child reply must succeed.
    return Promise.all([delivery, reply]).then(([, result]) => { check(); return result; });
  }
  const router = {
    async start() {
      if (state !== 'NEW') throw failure('IDENTITY_UNPROVEN');
      if (!isOperationLifetime(lifetime) || !rootSession
          || ['send', 'on', 'off'].some((name) => typeof rootSession[name] !== 'function')) {
        fail('PUBLIC_API_UNAVAILABLE'); throw failure(reasonCode);
      }
      state = 'STARTED';
      check();
      for (const name of ROOT_EVENTS) {
        const listener = (params) => receive([], { method: name, params });
        installed.set(name, listener); rootSession.on(name, listener);
      }
      const closed = () => fail('PUBLIC_API_UNAVAILABLE');
      installed.set('close', closed); rootSession.on('close', closed);
      deadline = setTimeout(() => fail('LIMIT_EXCEEDED'), Math.min(PROBE_LIMITS.totalMs, lifetime.remainingMs()));
      await dispatch([], 'Target.setAutoAttach', { autoAttach: true, waitForDebuggerOnStart: true, flatten: false });
    },
    send: (path, method, params) => dispatch(path, method, params),
    onEvent(listener) {
      if (typeof listener !== 'function' || state === 'CLOSED') throw failure('PROTOCOL_INVALID');
      listeners.add(listener); return () => listeners.delete(listener);
    },
    revoke() {
      if (state === 'CLOSED' || state === 'REVOKED') return;
      state = 'REVOKED';
      clearTimeout(deadline);
      if (pending.size) reasonCode ??= 'IDENTITY_UNPROVEN';
      for (const entry of pending.values()) { clearTimeout(entry.timer); entry.reject(failure(reasonCode ?? 'IDENTITY_UNPROVEN')); }
      pending.clear();
    },
    async close() {
      if (pending.size) fail('IDENTITY_UNPROVEN');
      router.revoke();
      state = 'CLOSED'; clearTimeout(deadline);
      for (const [name, listener] of installed) rootSession.off(name, listener);
      installed.clear(); listeners.clear(); routes.clear(); seen.clear();
    },
    snapshot: () => Object.freeze({ state, reasonCode, messages, pendingCommands: pending.size,
      knownSessions: Math.max(0, routes.size - 1), deprecatedRouting: true }),
  };
  return Object.freeze(router);
}
