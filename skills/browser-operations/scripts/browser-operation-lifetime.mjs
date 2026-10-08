const clocks = new WeakSet();
const lifetimes = new WeakSet();
const FAILURE_CODES = new Set([
  'OPERATION_EXPIRED', 'OPERATION_CLOCK_UNPROVEN',
  'APPROVAL_BINDING_INVALID', 'OPERATION_LIFETIME_UNPROVEN',
]);


export class BrowserLifetimeError extends Error {
  constructor(code) {
    const selected = FAILURE_CODES.has(code) ? code : 'OPERATION_LIFETIME_UNPROVEN';
    super(selected);
    this.name = 'BrowserLifetimeError';
    this.code = selected;
  }
}


export function createOperationClock(source) {
  if (source !== undefined && typeof source !== 'number' && typeof source !== 'function') {
    throw new BrowserLifetimeError('OPERATION_CLOCK_UNPROVEN');
  }
  const read = source === undefined ? () => Date.now()
    : typeof source === 'number' ? () => source : source;
  let previous = null;
  let unproven = false;
  const clock = Object.freeze({
    readNow() {
      if (unproven) throw new BrowserLifetimeError('OPERATION_CLOCK_UNPROVEN');
      let sample;
      try { sample = read(); } catch { unproven = true; }
      if (unproven || !Number.isSafeInteger(sample) || sample < 0
          || (previous !== null && sample < previous)) {
        unproven = true;
        throw new BrowserLifetimeError('OPERATION_CLOCK_UNPROVEN');
      }
      previous = sample;
      return sample;
    },
  });
  clocks.add(clock);
  return clock;
}


export function createOperationLifetime(envelope, clock) {
  if (!clocks.has(clock)) throw new BrowserLifetimeError('OPERATION_CLOCK_UNPROVEN');
  const deadline = envelope && Object.getOwnPropertyDescriptor(envelope, 'expiresAt');
  if (!deadline || !Object.hasOwn(deadline, 'value')
      || !Number.isSafeInteger(deadline.value) || deadline.value <= 0) {
    throw new BrowserLifetimeError('APPROVAL_BINDING_INVALID');
  }
  const expiresAt = deadline.value;
  const assertLive = () => {
    const now = clock.readNow();
    if (now >= expiresAt) throw new BrowserLifetimeError('OPERATION_EXPIRED');
    return now;
  };
  const lifetime = Object.freeze({
    expiresAt,
    assertLive,
    remainingMs() { return expiresAt - assertLive(); },
  });
  lifetimes.add(lifetime);
  return lifetime;
}


export function isOperationLifetime(value) {
  return lifetimes.has(value);
}


export function hasOperationLifetime(adapter, lifetime) {
  if (!isOperationLifetime(lifetime) || !adapter) return false;
  try {
    const installed = Object.getOwnPropertyDescriptor(adapter, 'operationLifetime');
    return Boolean(installed && Object.hasOwn(installed, 'value')
      && installed.writable === false && installed.configurable === false
      && installed.value === lifetime && adapter.capabilities?.operationLifetime === true);
  } catch {
    return false;
  }
}
