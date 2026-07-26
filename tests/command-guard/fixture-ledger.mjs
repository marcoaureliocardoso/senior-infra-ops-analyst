export function createFixtureLedger(expectedIds) {
  const declared = new Set();
  for (const id of expectedIds) {
    if (declared.has(id)) throw new Error(`fixture-declared-twice:${id}`);
    declared.add(id);
  }
  const executed = new Set();
  return Object.freeze({
    record(id) {
      if (!declared.has(id)) throw new Error(`fixture-not-declared:${id}`);
      if (executed.has(id)) throw new Error(`fixture-executed-twice:${id}`);
      executed.add(id);
    },
    assertComplete() {
      for (const id of declared) {
        if (!executed.has(id)) throw new Error(`fixture-not-executed:${id}`);
      }
      return true;
    },
    executedIds() {
      return Object.freeze([...executed]);
    },
  });
}
