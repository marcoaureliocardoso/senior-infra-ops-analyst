import assert from 'node:assert/strict';
import test from 'node:test';

import { COVERAGE_MANIFEST, validateCoverageManifest } from './coverage-manifest.mjs';

test('finite coverage manifest has no orphan or stale inventory item', () => {
  assert.equal(validateCoverageManifest(), true);
});

test('orphan detection reports the exact finite item', () => {
  const missing = structuredClone(COVERAGE_MANIFEST);
  missing.grammar.stage = { positive: [], boundary: [], negative: [] };
  assert.throws(() => validateCoverageManifest(missing), /orphan:grammar:stage/);

  const stale = structuredClone(COVERAGE_MANIFEST);
  stale.reasonCodes.UNREGISTERED = { positive: ['x'], boundary: [], negative: ['y'] };
  assert.throws(() => validateCoverageManifest(stale), /stale:reasonCodes:UNREGISTERED/);

  const boundary = structuredClone(COVERAGE_MANIFEST);
  boundary.limits.tokens.boundary = ['n'];
  assert.throws(() => validateCoverageManifest(boundary), /orphan:limits:tokens:boundary/);
});
