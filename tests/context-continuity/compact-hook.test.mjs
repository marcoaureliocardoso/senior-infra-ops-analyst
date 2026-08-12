import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import { access, copyFile, mkdir, mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { Readable, Writable } from 'node:stream';
import test from 'node:test';

import {
  evaluateCompactHook,
  main,
  parseCompactEnvelope,
} from '../../skills/context-continuity/scripts/compact-hook.mjs';
import {
  activatePendingBinding,
  hasActiveBinding,
  writePendingBinding,
} from '../../skills/command-driven-operations/scripts/command-guard/binding-store.mjs';


const NOW = 1_800_000_000_000;
const BASH = process.env.BASH_PATH ?? (process.platform === 'win32' ? 'C:/Program Files/Git/bin/bash.exe' : 'bash');
const SOURCE_LAUNCHER = path.resolve('skills/context-continuity/scripts/compact-hook-launcher.sh');
const RACE_WORKER = path.resolve('tests/fixtures/compact-binding-race-worker.mjs');
const binding = Object.freeze({
  sessionId: 'compact-session',
  toolUseId: 'compact-tool',
  domain: 'https://api.example.invalid',
  identity: 'operator',
  transport: 'AUTHORIZATION',
  family: 'HTTP',
  targetClass: 'HTTP',
});


async function withState(run) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'compact-hook-'));
  try {
    await run({ OPS_COMMAND_GUARD_STATE_DIR: directory });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}


function compactEvent(phase = 'PreCompact', extra = {}) {
  return {
    session_id: binding.sessionId,
    hook_event_name: phase,
    trigger: 'manual',
    transcript_path: 'C:/SYNTH_SECRET/transcript.jsonl',
    custom_instructions: 'SYNTH_SECRET prompt content',
    compact_summary: 'SYNTH_SECRET compact summary',
    ...extra,
  };
}


test('compact envelope reads bounded identity and ignores content fields', () => {
  const result = parseCompactEnvelope(JSON.stringify(compactEvent()), 'PreCompact');
  assert.deepEqual(result, {
    sessionId: binding.sessionId,
    trigger: 'manual',
  });
  assert.doesNotMatch(JSON.stringify(result), /SYNTH_SECRET|transcript|prompt|summary/iu);
});

test('PreCompact and PostCompact silently invalidate exact session reuse', async () => {
  await withState(async (env) => {
    for (const phase of ['PreCompact', 'PostCompact']) {
      writePendingBinding(binding, env, NOW);
      activatePendingBinding(binding, env, NOW + 1);
      const result = evaluateCompactHook(JSON.stringify(compactEvent(phase)), phase, env);
      assert.deepEqual(result, { phase, invalidated: true, degraded: false });
      assert.equal(hasActiveBinding(binding, env, NOW + 2), false);
    }
  });
});

test('hook main always exits zero and emits nothing on success', async () => {
  await withState(async (env) => {
    writePendingBinding(binding, env, NOW);
    activatePendingBinding(binding, env, NOW + 1);
    let output = '';
    let error = '';
    const code = await main({
      args: ['pre'],
      input: Readable.from([JSON.stringify(compactEvent())]),
      output: new Writable({ write(chunk, _encoding, callback) { output += chunk.toString(); callback(); } }),
      error: new Writable({ write(chunk, _encoding, callback) { error += chunk.toString(); callback(); } }),
      env,
    });
    assert.equal(code, 0);
    assert.equal(output, '');
    assert.equal(error, '');
    assert.equal(hasActiveBinding(binding, env, NOW + 2), false);
  });
});

test('malformed or oversized input invalidates all reuse and warns without content', async () => {
  for (const raw of ['{', JSON.stringify({ ...compactEvent(), session_id: '' }), 'x'.repeat(65 * 1024)]) {
    await withState(async (env) => {
      writePendingBinding(binding, env, NOW);
      activatePendingBinding(binding, env, NOW + 1);
      let output = '';
      let error = '';
      const code = await main({
        args: ['pre'],
        input: Readable.from([raw]),
        output: new Writable({ write(chunk, _encoding, callback) { output += chunk.toString(); callback(); } }),
        error: new Writable({ write(chunk, _encoding, callback) { error += chunk.toString(); callback(); } }),
        env,
      });
      assert.equal(code, 0);
      assert.equal(output, '');
      assert.equal(error, 'Context continuity degraded. Credential reuse requires fresh approval.\n');
      assert.doesNotMatch(error, /SYNTH_SECRET|transcript|prompt|summary|compact-session/iu);
      assert.equal(hasActiveBinding(binding, env, NOW + 2), false);
    });
  }
});

test('duplicate security identity and concurrent delivery stay fail-safe', async () => {
  await withState(async (env) => {
    writePendingBinding(binding, env, NOW);
    activatePendingBinding(binding, env, NOW + 1);
    const duplicate = '{"session_id":"compact-session","session_id":"other","hook_event_name":"PreCompact","trigger":"auto"}';
    assert.throws(() => parseCompactEnvelope(duplicate, 'PreCompact'), /duplicate JSON key/u);
    const events = Array.from({ length: 8 }, () =>
      Promise.resolve().then(() => evaluateCompactHook(JSON.stringify(compactEvent('PreCompact', { trigger: 'auto' })), 'PreCompact', env)));
    const results = await Promise.all(events);
    assert.equal(results.every(({ degraded }) => degraded === false), true);
    assert.equal(hasActiveBinding(binding, env, NOW + 2), false);
  });
});

async function waitForFile(target, timeoutMs = 2_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      await access(target);
      return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 10));
    }
  }
  throw new Error(`timed out waiting for ${target}`);
}

function runRaceWorker(args) {
  const child = spawn(process.execPath, [RACE_WORKER, ...args], {
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let stderr = '';
  child.stderr.on('data', (chunk) => { stderr += chunk; });
  const completed = new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('exit', (code) => code === 0 ? resolve() : reject(new Error(stderr || `worker exited ${code}`)));
  });
  return { child, completed };
}

test('cross-process PostToolUse cannot resurrect reuse after PreCompact', async () => {
  await withState(async (env) => {
    const signal = path.join(env.OPS_COMMAND_GUARD_STATE_DIR, 'activate.ready');
    const compactSignal = path.join(env.OPS_COMMAND_GUARD_STATE_DIR, 'compact.ready');
    const release = path.join(env.OPS_COMMAND_GUARD_STATE_DIR, 'activate.release');
    writePendingBinding(binding, env, NOW);
    const activating = runRaceWorker([
      'activate', env.OPS_COMMAND_GUARD_STATE_DIR, signal, release,
    ]);
    await waitForFile(signal);
    const compacting = runRaceWorker([
      'compact', env.OPS_COMMAND_GUARD_STATE_DIR, compactSignal, release,
    ]);
    await waitForFile(compactSignal);
    await writeFile(release, 'release', 'utf8');
    await Promise.all([activating.completed, compacting.completed]);
    assert.equal(hasActiveBinding(binding, env, NOW + 2), false);
  });
});

test('an unavailable or stale binding lock fails closed for credential reuse', async () => {
  await withState(async (env) => {
    writePendingBinding(binding, env, NOW);
    activatePendingBinding(binding, env, NOW + 1);
    const stateName = (await readdir(env.OPS_COMMAND_GUARD_STATE_DIR)).find((name) => name.endsWith('.json'));
    assert.ok(stateName);
    await mkdir(path.join(env.OPS_COMMAND_GUARD_STATE_DIR, `${stateName}.lock`));
    assert.equal(hasActiveBinding(binding, env, NOW + 2), false);
  });
});

async function launcherFixture(transform = (source) => source) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'compact-launcher-'));
  const scripts = path.join(root, 'scripts');
  await mkdir(scripts, { recursive: true });
  const launcher = path.join(scripts, 'compact-hook-launcher.sh');
  await writeFile(launcher, transform(await readFile(SOURCE_LAUNCHER, 'utf8')), 'utf8');
  await copyFile(path.resolve('skills/context-continuity/scripts/compact-hook.mjs'), path.join(scripts, 'compact-hook.mjs'));
  return { root, launcher };
}


test('launcher returns zero and no output for successful compact hook', async () => {
  await withState(async (env) => {
    const result = spawnSync(BASH, [SOURCE_LAUNCHER, 'pre'], {
      input: JSON.stringify(compactEvent()),
      encoding: 'utf8',
      env: { ...process.env, ...env },
    });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, '');
    assert.equal(result.stderr, '');
  });
});

test('launcher missing runtime fallback invalidates only bounded state files', async () => {
  await withState(async (env) => {
    const fixture = await launcherFixture((source) => source.replace(
      'NODE_BIN="$(command -v node 2>/dev/null)"',
      'NODE_BIN=""',
    ));
    try {
      const validName = `${'a'.repeat(64)}.json`;
      const validPath = path.join(env.OPS_COMMAND_GUARD_STATE_DIR, validName);
      const unrelatedPath = path.join(env.OPS_COMMAND_GUARD_STATE_DIR, 'operator.json');
      await writeFile(validPath, '{"version":1,"pending":[{}],"active":[{}]}\n', 'utf8');
      await writeFile(unrelatedPath, '{"keep":true}\n', 'utf8');
      const result = spawnSync(BASH, [fixture.launcher, 'pre'], {
        input: JSON.stringify(compactEvent()),
        encoding: 'utf8',
        env: { ...process.env, ...env },
      });
      assert.equal(result.status, 0);
      assert.equal(result.stdout, '');
      assert.equal(result.stderr, 'Context continuity degraded. Credential reuse requires fresh approval.\n');
      assert.equal(await readFile(validPath, 'utf8'), '{"version":1,"pending":[],"active":[]}\n');
      assert.equal(await readFile(unrelatedPath, 'utf8'), '{"keep":true}\n');
    } finally {
      await rm(fixture.root, { recursive: true, force: true });
    }
  });
});
