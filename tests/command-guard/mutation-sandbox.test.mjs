import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { pathToFileURL } from 'node:url';

import { copyMutationSandbox } from './mutation-sandbox.mjs';
import { validEvent } from './helpers.mjs';

test('mutation sandbox retains the canonical browser parser dependency', async (t) => {
  const temporary = await mkdtemp(path.join(os.tmpdir(), 'ops-guard-mutation-sandbox-'));
  t.after(() => rm(temporary, { recursive: true, force: true }));

  const root = await copyMutationSandbox({
    sourceScripts: path.resolve('skills/command-driven-operations/scripts'),
    sourceBrowserScripts: path.resolve('skills/browser-operations/scripts'),
    temporary,
  });
  const moduleUrl = (file) => pathToFileURL(path.join(root, 'command-guard', file)).href;
  const { parseHookEvent } = await import(moduleUrl('contract.mjs'));
  const { analyzeCommand } = await import(moduleUrl('policy.mjs'));
  const event = parseHookEvent(JSON.stringify(validEvent({ tool_input: { command: 'unknown-command' } })));

  assert.equal(analyzeCommand(event).decision, 'deny');
});
