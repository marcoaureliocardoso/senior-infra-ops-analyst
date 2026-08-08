import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtemp, readdir, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  main,
  renderStatusLine,
} from '../../skills/context-continuity/scripts/context-statusline.mjs';


const entrypoint = path.resolve('skills/context-continuity/scripts/context-statusline.mjs');


test('status line renders documented used or remaining percentage', () => {
  assert.equal(renderStatusLine({ context_window: { used_percentage: 72 } }), 'ctx 72%');
  assert.equal(renderStatusLine({ context_window: { remaining_percentage: 28 } }), 'ctx 72%');
  assert.equal(renderStatusLine({ context_window: { used_percentage: 72.4 } }), 'ctx 72%');
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
