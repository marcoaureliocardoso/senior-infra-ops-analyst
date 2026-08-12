import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtemp, readdir, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  COMPACT_SUGGESTION,
  DEFAULT_THRESHOLD,
  effectiveThreshold,
  main,
  renderStatusLine,
} from '../../skills/context-continuity/scripts/context-statusline.mjs';


const entrypoint = path.resolve('skills/context-continuity/scripts/context-statusline.mjs');


test('status line accepts only configured ASCII integer thresholds from 70 through 75', () => {
  assert.equal(DEFAULT_THRESHOLD, 72);
  for (let threshold = 70; threshold <= 75; threshold += 1) {
    assert.equal(
      effectiveThreshold({ CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: String(threshold) }),
      threshold,
    );
  }
});

test('status line falls back to 72 for missing or invalid threshold values', () => {
  for (const value of [undefined, '', ' 72', '72 ', '72.0', '069', '69', '76', 'text', 72]) {
    const environment = value === undefined
      ? {}
      : { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: value };
    assert.equal(effectiveThreshold(environment), 72, JSON.stringify(value));
  }
});


test('status line renders documented used or remaining percentage', () => {
  assert.equal(renderStatusLine({ context_window: { used_percentage: 72 } }), 'ctx 72%');
  assert.equal(renderStatusLine({ context_window: { remaining_percentage: 28 } }), 'ctx 72%');
  assert.equal(
    renderStatusLine(
      { context_window: { used_percentage: 72.4 } },
      { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '75' },
    ),
    'ctx 72%',
  );
});

test('status line warns only when native used percentage is strictly above threshold', () => {
  const atThreshold = renderStatusLine(
    { context_window: { used_percentage: 72 } },
    { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '72' },
  );
  const fractionAbove = renderStatusLine(
    { context_window: { used_percentage: 72.1 } },
    { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '72' },
  );
  assert.equal(atThreshold, 'ctx 72%');
  assert.equal(fractionAbove, `ctx 72%\n${COMPACT_SUGGESTION}`);
});

test('status line honors every supported configured threshold', () => {
  for (let threshold = 70; threshold <= 75; threshold += 1) {
    const environment = { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: String(threshold) };
    assert.equal(
      renderStatusLine({ context_window: { used_percentage: threshold } }, environment),
      `ctx ${threshold}%`,
    );
    assert.equal(
      renderStatusLine({ context_window: { used_percentage: threshold + 0.1 } }, environment),
      `ctx ${threshold}%\n${COMPACT_SUGGESTION}`,
    );
  }
});

test('status line uses default threshold for invalid configuration', () => {
  assert.equal(
    renderStatusLine(
      { context_window: { used_percentage: 72.1 } },
      { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '76' },
    ),
    `ctx 72%\n${COMPACT_SUGGESTION}`,
  );
});

test('remaining percentage never triggers compact suggestion', () => {
  assert.equal(
    renderStatusLine(
      { context_window: { remaining_percentage: 20 } },
      { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '70' },
    ),
    'ctx 80%',
  );
});

test('status line renders neutral state when context usage is unavailable', () => {
  for (const value of [
    null,
    {},
    { context_window: null },
    { context_window: { used_percentage: null } },
    { context_window: { used_percentage: -1 } },
    { context_window: { used_percentage: 101 } },
    { context_window: { used_percentage: '72' } },
  ]) assert.equal(renderStatusLine(value), 'ctx --', JSON.stringify(value));
});

test('status line executable writes one line and no local artifact', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'context-status-'));
  try {
    const result = spawnSync(process.execPath, [entrypoint], {
      input: JSON.stringify({
        context_window: { used_percentage: 70 },
        model: { display_name: 'SYNTH_SECRET_ignored' },
      }),
      encoding: 'utf8',
      cwd: directory,
    });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, 'ctx 70%\n');
    assert.equal(result.stderr, '');
    assert.deepEqual(await readdir(directory), []);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('status line main degrades malformed and oversized input without failing', async () => {
  for (const input of ['{', 'x'.repeat(65 * 1024)]) {
    let output = '';
    const code = await main({
      input: (await import('node:stream')).Readable.from([input]),
      output: new (await import('node:stream')).Writable({
        write(chunk, _encoding, callback) {
          output += chunk.toString();
          callback();
        },
      }),
    });
    assert.equal(code, 0);
    assert.equal(output, 'ctx --\n');
  }
});
