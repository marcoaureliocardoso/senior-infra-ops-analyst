import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

import {
  collectStaticInventory,
  findForbiddenKeys,
  normalizeRuntimeEvidence,
} from '../../skills/context-continuity/scripts/context-inventory.mjs';


const ROOT = path.resolve('.');
const FIXTURES = path.resolve('tests/fixtures/context-continuity');
const ENTRYPOINT = path.resolve('skills/context-continuity/scripts/context-inventory.mjs');


async function jsonl(name) {
  return (await readFile(path.join(FIXTURES, name), 'utf8'))
    .trim().split(/\r?\n/u).map((line) => JSON.parse(line));
}


test('inventory measures every registered skill and subagent', async () => {
  const report = await collectStaticInventory(ROOT);
  assert.equal(report.schemaVersion, 1);
  assert.equal(report.skills.count, 25);
  assert.equal(report.subagents.count, 12);
  assert.equal(report.skills.items.every(({ id, bodyBytes, descriptionBytes }) =>
    id && bodyBytes > 0 && descriptionBytes > 0), true);
  assert.equal(report.subagents.items.every(({ id, definitionBytes, preloadBytes }) =>
    id && definitionBytes > 0 && preloadBytes > 0), true);
  assert.equal(report.mcp.packageServerCount, 0);
  const skillBytes = new Map(report.skills.items.map(({ id, bodyBytes }) => [id, bodyBytes]));
  const diagnostic = report.subagents.items.find(({ id }) => id === 'diagnostic-operator');
  assert.equal(
    diagnostic.preloadBytes,
    skillBytes.get('command-driven-operations') + skillBytes.get('infrastructure-troubleshooting'),
  );
  assert.equal('tokens' in report, false);
  assert.deepEqual(findForbiddenKeys(report), []);
});


test('retained runtime schema cannot carry content', () => {
  const events = [
    { kind: 'context', stage: 'before', percent: 73, prompt: 'synthetic prompt SYNTH_SECRET' },
    { kind: 'task', action: 'created', family: 'TaskCreate', identifier: 'task-a', tool_input: 'SYNTH_SECRET' },
    { kind: 'task', action: 'completed', family: 'TaskUpdate', identifier: 'task-a', response: 'tool output' },
    { kind: 'compact', phase: 'PreCompact', custom_instructions: 'SYNTH_SECRET prompt' },
    { kind: 'compact', phase: 'PostCompact', compact_summary: 'SYNTH_SECRET summary' },
    { kind: 'task', action: 'observed-after', family: 'TaskCreate', identifier: 'task-a', transcript: 'SYNTH_SECRET' },
    { kind: 'context', stage: 'after', percent: 21, content: 'SYNTH_SECRET' },
  ];
  const report = normalizeRuntimeEvidence(events);
  assert.deepEqual(findForbiddenKeys(report), []);
  assert.doesNotMatch(JSON.stringify(report), /SYNTH_SECRET|synthetic prompt|tool output|summary/iu);
  assert.equal(report.context.deltaPercent, -52);
  assert.equal(report.context.compactionCount, 1);
  assert.equal(report.tasks.createdCount, 1);
  assert.equal(report.tasks.completedCount, 1);
  assert.equal(report.tasks.survivedCompaction, true);
});

test('task survival requires ordered PreCompact PostCompact and later observation', () => {
  for (const events of [
    [
      { kind: 'task', action: 'created', family: 'TaskCreate', identifier: 'task-a' },
      { kind: 'task', action: 'observed-after', family: 'TaskCreate', identifier: 'task-a' },
      { kind: 'compact', phase: 'PreCompact' },
      { kind: 'compact', phase: 'PostCompact' },
    ],
    [
      { kind: 'task', action: 'created', family: 'TaskCreate', identifier: 'task-a' },
      { kind: 'compact', phase: 'PostCompact' },
      { kind: 'task', action: 'observed-after', family: 'TaskCreate', identifier: 'task-a' },
    ],
    [
      { kind: 'task', action: 'created', family: 'TaskCreate', identifier: 'task-a' },
      { kind: 'compact', phase: 'PreCompact' },
      { kind: 'task', action: 'observed-after', family: 'TaskCreate', identifier: 'task-a' },
      { kind: 'compact', phase: 'PostCompact' },
    ],
  ]) {
    const report = normalizeRuntimeEvidence(events);
    assert.equal(report.tasks.survivedCompaction, false);
  }
  assert.equal(normalizeRuntimeEvidence([
    { kind: 'compact', phase: 'PostCompact' },
  ]).context.compactionCount, 0);
});


test('tool search fixtures produce honest capability reason codes', async () => {
  const available = normalizeRuntimeEvidence(await jsonl('tool-search-available.jsonl'));
  assert.equal(available.tools.searchAvailable, true);
  assert.equal(available.tools.reasonCode, 'TOOL_SEARCH_AVAILABLE');
  assert.equal(available.tools.visibleCountBefore, 18);
  assert.equal(available.tools.visibleCountAfter, 7);

  const unavailable = normalizeRuntimeEvidence(await jsonl('tool-search-unavailable.jsonl'));
  assert.equal(unavailable.tools.searchAvailable, false);
  assert.equal(unavailable.tools.reasonCode, 'TOOL_SEARCH_UNAVAILABLE_GATEWAY');

  const unobserved = normalizeRuntimeEvidence([]);
  assert.equal(unobserved.tools.searchAvailable, false);
  assert.equal(unobserved.tools.reasonCode, 'TOOL_SEARCH_NOT_OBSERVED');
});


test('MCP measurements retain counts only', () => {
  for (const [event, connected, visible] of [
    [undefined, 0, 0],
    [{ kind: 'mcp', connectedCount: 1, visibleToolCount: 4, beforePercent: 2, afterPercent: 3 }, 1, 4],
    [{ kind: 'mcp', connectedCount: 2 }, 2, 0],
  ]) {
    const report = normalizeRuntimeEvidence(event ? [event] : []);
    assert.equal(report.mcp.connectedCount, connected);
    assert.equal(report.mcp.visibleToolCount, visible);
  }
  assert.deepEqual(normalizeRuntimeEvidence([{
    kind: 'mcp', connectedCount: 1, visibleToolCount: 1, beforePercent: 2, afterPercent: 5,
  }]).mcp, { connectedCount: 1, visibleToolCount: 1, beforePercent: 2, afterPercent: 5, deltaPercent: 3 });
});

test('per-role context observations retain aggregate percentages only', () => {
  const report = normalizeRuntimeEvidence([
    { kind: 'context-role', role: 'main', percent: 4, prompt: 'SYNTH_SECRET' },
    { kind: 'context-role', role: 'diagnostic-operator', percent: 9, response: 'SYNTH_SECRET' },
  ]);
  assert.equal(report.context.roleCount, 2);
  assert.equal(report.context.rolePercentMin, 4);
  assert.equal(report.context.rolePercentMax, 9);
  assert.doesNotMatch(JSON.stringify(report), /main|diagnostic-operator|SYNTH_SECRET/u);
});

test('session continuity records resume rewind and isolated clear as booleans', () => {
  const report = normalizeRuntimeEvidence([
    { kind: 'session', action: 'resume-tasks', session_id: 'SYNTH_SECRET' },
    { kind: 'session', action: 'rewind-tasks', transcript: 'SYNTH_SECRET' },
    { kind: 'session', action: 'rewind-context' },
    { kind: 'session', action: 'rewind-authorization-invalid' },
    { kind: 'session', action: 'clear-isolated', prompt: 'SYNTH_SECRET' },
  ]);
  assert.deepEqual(report.session, {
    resumeTasksObserved: true,
    rewindTasksObserved: true,
    rewindContextObserved: true,
    rewindAuthorizationInvalidated: true,
    isolatedClearObserved: true,
  });
  assert.doesNotMatch(JSON.stringify(report), /SYNTH_SECRET|session_id|transcript|prompt/u);
});

test('repeated skill use retains count and aggregate context percentages', () => {
  const report = normalizeRuntimeEvidence([
    { kind: 'skill-use', percent: 6, skill: 'SYNTH_SECRET' },
    { kind: 'skill-use', percent: 8, response: 'SYNTH_SECRET' },
  ]);
  assert.equal(report.context.skillUseCount, 2);
  assert.equal(report.context.skillPercentMin, 6);
  assert.equal(report.context.skillPercentMax, 8);
  assert.doesNotMatch(JSON.stringify(report), /SYNTH_SECRET|"skill":|"response":/u);
});


test('window evidence gates the exceptional absolute override', () => {
  const consistent = normalizeRuntimeEvidence([{
    kind: 'window', reportedWindow: 64000, observedWindow: 64000,
  }]);
  assert.deepEqual(consistent.window, {
    reportedWindow: 64000,
    observedWindow: 64000,
    reasonCode: 'WINDOW_REPORTING_CONSISTENT',
    absoluteOverrideEvidenceGated: false,
  });
  const divergent = normalizeRuntimeEvidence([{
    kind: 'window', reportedWindow: 128000, observedWindow: 64000,
    absoluteOverrideApplied: true,
  }]);
  assert.equal(divergent.window.reasonCode, 'WINDOW_REPORTING_DIVERGENCE');
  assert.equal(divergent.window.absoluteOverrideEvidenceGated, true);
});


test('runtime identifiers are bounded and untrusted labels are not copied', () => {
  const report = normalizeRuntimeEvidence([{
    kind: 'runtime', claudeCode: '2.9.1', nori: '0.4.0', modelLabel: 'deepseek-chat',
    providerLabel: 'deepseek', platform: 'win32', secret: 'SYNTH_SECRET',
  }]);
  assert.deepEqual(report.runtime, {
    claudeCode: '2.9.1', nori: '0.4.0', modelLabel: 'deepseek-chat',
    providerLabel: 'deepseek', platform: 'win32',
  });
  assert.throws(() => normalizeRuntimeEvidence([{
    kind: 'runtime', claudeCode: 'value with spaces',
  }]), /invalid runtime identifier/u);
});


test('CLI emits one content-free document and refuses output paths', () => {
  const result = spawnSync(process.execPath, [
    ENTRYPOINT, '--root', ROOT, '--runtime-jsonl',
    path.join(FIXTURES, 'tool-search-available.jsonl'),
  ], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  const report = JSON.parse(result.stdout);
  assert.deepEqual(findForbiddenKeys(report), []);
  assert.equal(report.runtime.tools.reasonCode, 'TOOL_SEARCH_AVAILABLE');

  const refused = spawnSync(process.execPath, [
    ENTRYPOINT, '--root', ROOT, '--output', 'inventory.json',
  ], { encoding: 'utf8' });
  assert.equal(refused.status, 1);
  assert.equal(refused.stdout, '');
  assert.equal(refused.stderr, 'Context inventory failed safely.\n');
});
