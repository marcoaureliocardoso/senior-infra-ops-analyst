import { EventEmitter } from 'node:events';
import { createOperationClock, createOperationLifetime } from '../../skills/browser-operations/scripts/browser-operation-lifetime.mjs';

export function fakeLifetime() {
  let now = 1_000;
  return { lifetime: createOperationLifetime({ expiresAt: 6_000 }, createOperationClock(() => now)),
    expire() { now = 6_000; } };
}

export async function flush() {
  for (let i = 0; i < 8; i += 1) await new Promise((resolve) => setImmediate(resolve));
}

export function publicSession({ autoReply = true, response = () => ({}) } = {}) {
  let repliesEnabled = autoReply;
  const session = new EventEmitter();
  const calls = [];
  function emitAt(path, event) {
    let nested = event;
    for (let i = path.length - 1; i >= 0; i -= 1) {
      nested = { method: 'Target.receivedMessageFromTarget', params: {
        sessionId: path[i], message: JSON.stringify(nested),
      } };
    }
    session.emit(nested.method, nested.params);
  }
  session.send = async (method, params) => {
    calls.push({ path: [], method, params });
    if (method !== 'Target.sendMessageToTarget') return response(method, params, []);
    let path = [];
    let outer = { method, params };
    while (outer.method === 'Target.sendMessageToTarget') {
      path = [...path, outer.params.sessionId];
      const message = JSON.parse(outer.params.message);
      calls.push({ path, ...message });
      if (repliesEnabled) {
        const result = response(message.method, message.params, path);
        const responsePath = [...path];
        queueMicrotask(() => emitAt(responsePath, { id: message.id, result }));
      }
      outer = message;
    }
    return {};
  };
  return { session, calls, emitAt, setAutoReply(value) { repliesEnabled = value; },
    attach(path = [], overrides = {}) {
      emitAt(path, { method: 'Target.attachedToTarget', params: {
        sessionId: 'child-1', waitingForDebugger: true,
        targetInfo: { targetId: 'page-1', type: 'page', browserContextId: 'context-1' },
        ...overrides,
      } });
    },
    reply(call, result = {}) { emitAt(call.path, { id: call.id, result }); },
  };
}
