#!/usr/bin/env node

import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

import { validEvent } from './helpers.mjs';
import { REVIEW_REGRESSION_FIXTURES } from './review-regression-fixtures.mjs';

const scriptsDirectory = process.argv[2] ? path.resolve(process.argv[2]) : null;
if (!scriptsDirectory) throw new Error('installed scripts directory is required');
const guard = path.join(scriptsDirectory, 'command-guard');
const { parseHookEvent } = await import(pathToFileURL(path.join(guard, 'contract.mjs')));
const { analyzeCommand } = await import(pathToFileURL(path.join(guard, 'policy.mjs')));
const { redactText } = await import(pathToFileURL(path.join(guard, 'redaction.mjs')));

for (const fixture of REVIEW_REGRESSION_FIXTURES) {
  const event = parseHookEvent(JSON.stringify(validEvent({
    permission_mode: fixture.permissionMode ?? 'bypassPermissions',
    ...(fixture.cwd ? { cwd: fixture.cwd } : {}),
    tool_input: { command: fixture.command },
  })));
  const result = analyzeCommand(event, fixture.policyEnv ?? {});
  assert.equal(result.decision, fixture.expectedDecision, fixture.id);
  if (fixture.expectedRisk) assert.equal(result.risk, fixture.expectedRisk, fixture.id);
  if (fixture.expectedEnvironment) assert.equal(result.environment, fixture.expectedEnvironment, fixture.id);
  if (fixture.expectedTarget) assert.equal(result.target, fixture.expectedTarget, fixture.id);
  if (fixture.expectedModifiers) assert.deepEqual(result.modifiers.toSorted(), fixture.expectedModifiers.toSorted(), fixture.id);
  if (fixture.forbiddenText) assert.doesNotMatch(JSON.stringify(result), new RegExp(fixture.forbiddenText, 'u'));
  if (fixture.redactionForbiddenText) assert.doesNotMatch(redactText(fixture.command), new RegExp(fixture.redactionForbiddenText, 'u'));
}

process.stdout.write(`installed command guard corpus passed: ${REVIEW_REGRESSION_FIXTURES.length} fixtures\n`);
