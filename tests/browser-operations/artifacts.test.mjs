import assert from 'node:assert/strict';
import { mkdir, mkdtemp, readFile, rm, stat, symlink, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  createArtifactManager,
} from '../../skills/browser-operations/scripts/browser-artifacts.mjs';


const POLICY = Object.freeze({
  enabled: true,
  types: ['upload', 'download', 'screenshot', 'trace'],
  purposeRef: 'change-evidence',
  sourceClasses: ['operator-upload', 'browser-viewport', 'browser-download', 'browser-trace'],
  destinationClasses: ['operation-temp'],
  maxItems: 4,
  maxBytes: 1024,
  redaction: 'required',
  retentionSeconds: 60,
});


async function fixture(run) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'browser-artifacts-'));
  try { await run(root); } finally { await rm(root, { recursive: true, force: true }); }
}


test('artifact manager writes only operation-owned restrictive files and opaque handles', async () => {
  await fixture(async (root) => {
    const manager = await createArtifactManager(POLICY, {
      root, operationId: 'op-artifact-1', now: 1000,
    });
    const handle = await manager.capture({
      type: 'trace', sourceClass: 'browser-trace', destinationClass: 'operation-temp',
      mimeType: 'application/json', suggestedName: '../../escape.json',
      data: Buffer.from('{"token":"SYNTH_SECRET_ARTIFACT_CANARY"}'),
    });
    assert.deepEqual(Object.keys(handle).sort(), [
      'artifactId', 'bytes', 'expiresAt', 'mimeType', 'redacted', 'type',
    ]);
    assert.equal(handle.redacted, true);
    const ownedPath = manager.materialize(handle.artifactId);
    assert.equal(path.dirname(ownedPath).startsWith(root), true);
    if (process.platform !== 'win32') {
      assert.equal((await stat(path.dirname(ownedPath))).mode & 0o777, 0o700);
      assert.equal((await stat(ownedPath)).mode & 0o777, 0o600);
    }
    assert.doesNotMatch(await readFile(ownedPath, 'utf8'), /SYNTH_SECRET_ARTIFACT_CANARY/u);
  });
});


test('artifact policy rejects disabled mismatched unsafe or overflowing writes', async () => {
  await fixture(async (root) => {
    await assert.rejects(() => createArtifactManager({ ...POLICY, enabled: false }, {
      root, operationId: 'op-artifact-2', now: 1000,
    }), /ARTIFACT_POLICY_INVALID/u);
    const manager = await createArtifactManager(POLICY, {
      root, operationId: 'op-artifact-2', now: 1000,
    });
    const rejected = [
      { type: 'cookie', sourceClass: 'browser-trace', destinationClass: 'operation-temp', mimeType: 'application/json', data: Buffer.from('x') },
      { type: 'trace', sourceClass: 'browser-profile', destinationClass: 'operation-temp', mimeType: 'application/json', data: Buffer.from('x') },
      { type: 'trace', sourceClass: 'browser-trace', destinationClass: 'external', mimeType: 'application/json', data: Buffer.from('x') },
      { type: 'trace', sourceClass: 'browser-trace', destinationClass: 'operation-temp', mimeType: 'text/html', data: Buffer.from('x') },
      { type: 'trace', sourceClass: 'browser-trace', destinationClass: 'operation-temp', mimeType: 'application/json', data: Buffer.alloc(1025) },
    ];
    for (const value of rejected) await assert.rejects(() => manager.capture(value), /ARTIFACT_/u);
    await assert.rejects(() => manager.capture({
      type: 'screenshot', sourceClass: 'browser-viewport', destinationClass: 'operation-temp',
      mimeType: 'image/png', data: Buffer.from('SYNTH_SECRET_BINARY_CANARY'),
    }), /ARTIFACT_REDACTOR_REQUIRED/u);
  });
});


test('uploads require a regular allowlisted source and never retain the source name', async () => {
  await fixture(async (root) => {
    const uploads = path.join(root, 'approved-uploads');
    await mkdir(uploads, { mode: 0o700 });
    const source = path.join(uploads, 'operator-secret-name.txt');
    await writeFile(source, 'synthetic upload', { mode: 0o600 });
    const manager = await createArtifactManager(POLICY, {
      root, operationId: 'op-artifact-3', now: 1000, uploadRoots: [uploads],
    });
    const handle = await manager.stageUpload({
      sourcePath: source, sourceClass: 'operator-upload', mimeType: 'text/plain',
    });
    assert.doesNotMatch(manager.materialize(handle.artifactId), /operator-secret-name/u);
    await assert.rejects(() => manager.stageUpload({
      sourcePath: path.join(root, '..', 'escape.txt'), sourceClass: 'operator-upload', mimeType: 'text/plain',
    }), /ARTIFACT_SOURCE_FORBIDDEN/u);
    if (process.platform !== 'win32') {
      const link = path.join(uploads, 'link.txt');
      await symlink(source, link);
      await assert.rejects(() => manager.stageUpload({
        sourcePath: link, sourceClass: 'operator-upload', mimeType: 'text/plain',
      }), /ARTIFACT_SOURCE_FORBIDDEN/u);
    }
  });
});


test('item bounds retention expiry success and failure all clean owned artifacts', async () => {
  await fixture(async (root) => {
    const manager = await createArtifactManager({ ...POLICY, maxItems: 1 }, {
      root, operationId: 'op-artifact-4', now: 1000,
    });
    await manager.capture({
      type: 'trace', sourceClass: 'browser-trace', destinationClass: 'operation-temp',
      mimeType: 'application/json', data: Buffer.from('{}'),
    });
    await assert.rejects(() => manager.capture({
      type: 'trace', sourceClass: 'browser-trace', destinationClass: 'operation-temp',
      mimeType: 'application/json', data: Buffer.from('{}'),
    }), /ARTIFACT_ITEM_LIMIT/u);
    const owned = manager.directory;
    await manager.close({ retain: false });
    await assert.rejects(() => stat(owned));

    for (const outcome of ['success', 'failure', 'expiry']) {
      const next = await createArtifactManager(POLICY, {
        root, operationId: `op-${outcome}`, now: 1000,
      });
      await next.capture({
        type: 'trace', sourceClass: 'browser-trace', destinationClass: 'operation-temp',
        mimeType: 'application/json', data: Buffer.from('{}'),
      });
      const directory = next.directory;
      if (outcome === 'expiry') await next.expire(61_001);
      else await next.close({ retain: false, outcome });
      await assert.rejects(() => stat(directory));
    }
  });
});


test('retention fails closed and the default root is outside the repository', async () => {
  const manager = await createArtifactManager(POLICY, {
    operationId: 'op-default-root', now: 1000,
  });
  try {
    assert.equal(path.relative(process.cwd(), manager.directory).startsWith('..'), true);
    await assert.rejects(() => manager.close({ retain: true }), /ARTIFACT_RETENTION_UNAVAILABLE/u);
    await stat(manager.directory);
  } finally {
    await manager.close({ retain: false });
  }
  await assert.rejects(() => stat(manager.directory));
});


test('binary evidence requires an injected redactor proof', async () => {
  await fixture(async (root) => {
    const manager = await createArtifactManager(POLICY, {
      root, operationId: 'op-binary-redactor', now: 1000,
      redactor: async ({ data, mimeType }) => ({
        data: Buffer.from([137, 80, 78, 71]), redacted: true,
        proof: mimeType === 'image/png' && data.length > 0 ? 'trusted-image-redactor-v1' : null,
      }),
    });
    const handle = await manager.capture({
      type: 'screenshot', sourceClass: 'browser-viewport', destinationClass: 'operation-temp',
      mimeType: 'image/png', data: Buffer.from('SYNTH_SECRET_BINARY_CANARY'),
    });
    assert.equal(handle.redacted, true);
    assert.doesNotMatch(await readFile(manager.materialize(handle.artifactId), 'utf8'), /SYNTH_SECRET/u);
  });
});
