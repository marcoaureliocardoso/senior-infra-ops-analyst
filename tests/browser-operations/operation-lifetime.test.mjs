import assert from 'node:assert/strict';
import test from 'node:test';

import {
  BrowserLifetimeError, createOperationClock, createOperationLifetime,
  hasOperationLifetime, isOperationLifetime,
} from '../../skills/browser-operations/scripts/browser-operation-lifetime.mjs';


function fails(code) {
  return (error) => error instanceof BrowserLifetimeError && error.code === code
    && error.message === code;
}


test('the original deadline permits the last millisecond and rejects equality', () => {
  let now = 999;
  const lifetime = createOperationLifetime({ expiresAt: 1000 }, createOperationClock(() => now));
  assert.equal(lifetime.assertLive(), 999);
  assert.equal(lifetime.remainingMs(), 1);
  now = 1000;
  assert.throws(() => lifetime.assertLive(), fails('OPERATION_EXPIRED'));
  assert.throws(() => lifetime.remainingMs(), fails('OPERATION_EXPIRED'));
});


test('numeric clocks preserve deterministic legitimate controls', () => {
  const lifetime = createOperationLifetime({ expiresAt: 1000 }, createOperationClock(999));
  assert.equal(lifetime.assertLive(), 999);
  assert.equal(lifetime.assertLive(), 999);
  assert.equal(lifetime.remainingMs(), 1);
});


test('default clocks sample current time at each dispatch check', () => {
  const previous = Date.now;
  let now = 998;
  try {
    Date.now = () => now;
    const lifetime = createOperationLifetime({ expiresAt: 1000 }, createOperationClock());
    assert.equal(lifetime.assertLive(), 998);
    now = 1000;
    assert.throws(() => lifetime.assertLive(), fails('OPERATION_EXPIRED'));
  } finally {
    Date.now = previous;
  }
});


for (const [label, sample] of [
  ['NaN', NaN], ['infinity', Infinity], ['negative', -1], ['fraction', 1.5],
  ['boolean', true], ['string', '999'], ['promise', Promise.resolve(999)],
]) {
  test(`${label} clock samples cannot authorize an effect or expose their value`, () => {
    const clock = createOperationClock(() => sample);
    assert.throws(() => clock.readNow(), fails('OPERATION_CLOCK_UNPROVEN'));
  });
}


test('invalid clock sources and throwing readers fail with a closed reason', () => {
  for (const source of [null, true, '999', {}, Promise.resolve(999)]) {
    assert.throws(() => createOperationClock(source), fails('OPERATION_CLOCK_UNPROVEN'));
  }
  const clock = createOperationClock(() => { throw new Error('private reader detail'); });
  assert.throws(() => clock.readNow(), fails('OPERATION_CLOCK_UNPROVEN'));
});


test('a backward or invalid clock cannot recover into renewed authority', () => {
  for (const bad of [998, NaN]) {
    let now = 999;
    const lifetime = createOperationLifetime({ expiresAt: 1100 }, createOperationClock(() => now));
    assert.equal(lifetime.assertLive(), 999);
    now = bad;
    assert.throws(() => lifetime.assertLive(), fails('OPERATION_CLOCK_UNPROVEN'));
    now = 1001;
    assert.throws(() => lifetime.assertLive(), fails('OPERATION_CLOCK_UNPROVEN'));
  }
});


test('a copied clock or lifetime cannot establish installed enforcement', () => {
  const clock = createOperationClock(999);
  const lifetime = createOperationLifetime({ expiresAt: 1000 }, clock);
  assert.throws(() => createOperationLifetime({ expiresAt: 1000 }, { ...clock }),
    fails('OPERATION_CLOCK_UNPROVEN'));
  for (const fake of [null, { ...lifetime }, { expiresAt: 1000, assertLive: async () => 999 }]) {
    assert.equal(isOperationLifetime(fake), false);
    assert.equal(hasOperationLifetime(Object.freeze({
      operationLifetime: fake, capabilities: { operationLifetime: true },
    }), fake), false);
  }
  assert.equal(isOperationLifetime(lifetime), true);
});


test('adapter eligibility requires exact immutable identity and the installed capability', () => {
  const lifetime = createOperationLifetime({ expiresAt: 1000 }, createOperationClock(999));
  const other = createOperationLifetime({ expiresAt: 1000 }, createOperationClock(999));
  const adapter = Object.freeze({ operationLifetime: lifetime, capabilities: { operationLifetime: true } });
  assert.equal(hasOperationLifetime(adapter, lifetime), true);
  assert.equal(hasOperationLifetime(adapter, other), false);
  assert.equal(hasOperationLifetime({ operationLifetime: lifetime, capabilities: { operationLifetime: true } }, lifetime), false);
  assert.equal(hasOperationLifetime(Object.freeze({ operationLifetime: lifetime, capabilities: {} }), lifetime), false);
  assert.equal(hasOperationLifetime(Object.freeze({
    get operationLifetime() { return lifetime; }, capabilities: { operationLifetime: true },
  }), lifetime), false);
  assert.throws(() => { lifetime.expiresAt = 2000; }, TypeError);
  assert.throws(() => { lifetime.assertLive = () => 999; }, TypeError);
});


test('invalid or accessor deadlines cannot replace the original binding', () => {
  for (const envelope of [null, {}, { expiresAt: 0 }, { expiresAt: NaN },
    { expiresAt: '1000' }, { expiresAt: 1000.5 }, { get expiresAt() { return 1000; } }]) {
    assert.throws(() => createOperationLifetime(envelope, createOperationClock(999)),
      fails('APPROVAL_BINDING_INVALID'));
  }
});
