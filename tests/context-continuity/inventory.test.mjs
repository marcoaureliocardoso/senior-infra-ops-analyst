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
    [{ kind: 'mcp', connectedCount: 1, visibleToolCount: 4 }, 1, 4],
    [{ kind: 'mcp', connectedCount: 2 }, 2, 0],
  ]) {
    const report = normalizeRuntimeEvidence(event ? [event] : []);
    assert.deepEqual(report.mcp, { connectedCount: connected, visibleToolCount: visible });
  }
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
