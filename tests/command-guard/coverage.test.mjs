import assert from 'node:assert/strict';
import test from 'node:test';

import { COVERAGE_MANIFEST, validateCoverageManifest } from './coverage-manifest.mjs';
import { executeCoverageFixture } from './coverage-fixtures.mjs';
import { createFixtureLedger } from './fixture-ledger.mjs';

test('finite coverage manifest has no orphan or stale inventory item', () => {
  assert.equal(validateCoverageManifest(), true);
});

test('every finite inventory fixture executes semantic assertions', () => {
  const fixtures = Object.entries(COVERAGE_MANIFEST).flatMap(([category, entries]) =>
    Object.entries(entries).flatMap(([item, { executable }]) =>
      executable.map((id) => ({ id, category, item }))));
  const ledger = createFixtureLedger(fixtures.map(({ id }) => id));
  for (const fixture of fixtures) {
    executeCoverageFixture(fixture);
    ledger.record(fixture.id);
  }
  assert.equal(ledger.assertComplete(), true);
});

test('orphan detection reports the exact finite item', () => {
  const missing = structuredClone(COVERAGE_MANIFEST);
  missing.grammar.stage = { executable: [] };
  assert.throws(() => validateCoverageManifest(missing), /orphan:grammar:stage/);

  const stale = structuredClone(COVERAGE_MANIFEST);
  stale.reasonCodes.UNREGISTERED = { executable: ['x'] };
  assert.throws(() => validateCoverageManifest(stale), /stale:reasonCodes:UNREGISTERED/);

  const executable = structuredClone(COVERAGE_MANIFEST);
  executable.reviewRegressions['RV02-PS-OUTER-SEQUENCE'].executable = [];
  assert.throws(
    () => validateCoverageManifest(executable),
    /orphan:reviewRegressions:RV02-PS-OUTER-SEQUENCE/u,
  );
});
