import assert from 'node:assert/strict';
import test from 'node:test';

import {
  applyOwnedMainSessionHooks,
  desiredMainSessionHooks,
  emptyMainSessionOwnership,
  inspectMainSessionGuard,
  parseStrictSettings,
  removeOwnedMainSessionHooks,
} from '../../skills/command-driven-operations/scripts/main-session-settings.mjs';


const posixRoot = '/opt/nori/skills/command-driven-operations';

function desired(overrides = {}) {
  return desiredMainSessionHooks({
    skillRoot: posixRoot,
    platform: 'linux',
    runtimeIdentity: 'claude-observed',
    ...overrides,
  });
}

function localScope(settings) {
  return [{ name: 'local', precedence: 3, settings }];
}

test('strict settings parser accepts object roots and rejects duplicate keys', () => {
  assert.deepEqual(
    parseStrictSettings('{"hooks":{},"statusLine":{"type":"command"}}'),
    { hooks: {}, statusLine: { type: 'command' } },
  );
  for (const raw of [
    '{"hooks":{},"hooks":{}}',
    '{"hooks":{"PreToolUse":[],"PreToolUse":[]}}',
    '{"hooks":{"PreToolUse":[{"matcher":"Bash","matcher":"*"}]}}',
  ]) {
    assert.throws(() => parseStrictSettings(raw), /duplicate JSON key/u, raw);
  }
});

test('strict settings parser rejects scalar oversized and over-deep input', () => {
  for (const raw of ['null', '[]', 'true', '"settings"']) {
    assert.throws(() => parseStrictSettings(raw), /root must be an object/u);
  }
  assert.throws(
    () => parseStrictSettings(`{"value":"${'x'.repeat(1024 * 1024)}"}`),
    /exceeds limit/u,
  );
  let nested = '{}';
  for (let index = 0; index < 66; index += 1) nested = `{"child":${nested}}`;
  assert.throws(() => parseStrictSettings(nested), /nesting exceeds limit/u);
});

test('desired hooks use one exact complete Bash lifecycle on POSIX and Windows', () => {
  const posix = desired();
  assert.deepEqual(posix.hooks.map(({ event, matcher }) => [event, matcher]), [
    ['PreToolUse', 'Bash'],
    ['PostToolUse', 'Bash'],
  ]);
  assert.deepEqual(posix.hooks.map(({ group }) => group.hooks[0].args), [
    ['pre'],
    ['post'],
  ]);
  assert.equal(
    posix.hooks.every(({ group }) =>
      group.hooks[0].command === `${posixRoot}/scripts/command-guard-launcher.sh`),
    true,
  );
  assert.equal(posix.hooks.every(({ group }) => group.hooks[0].timeout === 7), true);

  const windows = desiredMainSessionHooks({
    skillRoot: 'C:\\Nori Skills\\command-driven-operations',
    platform: 'win32',
    runtimeIdentity: 'claude-observed',
  });
  assert.equal(
    windows.hooks[0].group.hooks[0].command,
    'C:\\Nori Skills\\command-driven-operations\\scripts\\command-guard-launcher.sh',
  );
  assert.doesNotThrow(() => desired({ skillRoot: `/${'a'.repeat(300)}` }));
  assert.throws(
    () => desired({ skillRoot: `/${'a'.repeat(4096)}` }),
    /skillRoot must be a bounded path/u,
  );
});

test('apply preserves unrelated settings and is idempotent', () => {
  const compactGroup = {
    hooks: [{ type: 'command', command: '/operator/compact', args: ['pre'] }],
  };
  const current = {
    model: 'operator-model',
    permissions: { allow: ['Read'] },
    env: { OTHER: 'SYNTH_SECRET_not_reported' },
    statusLine: { type: 'command', command: '/operator/status' },
    mcpServers: { operator: { command: '/operator/mcp' } },
    hooks: {
      PreCompact: [compactGroup],
      PreToolUse: [{ matcher: 'Read', hooks: [{ type: 'command', command: '/operator/read' }] }],
    },
  };
  const first = applyOwnedMainSessionHooks({
    current,
    desired: desired(),
    ownership: emptyMainSessionOwnership(),
  });
  const second = applyOwnedMainSessionHooks({
    current: first.settings,
    desired: desired(),
    ownership: first.ownership,
  });
  assert.deepEqual(second, first);
  assert.deepEqual(first.settings.hooks.PreCompact, [compactGroup]);
  assert.equal(first.settings.hooks.PreToolUse.length, 2);
  assert.equal(first.settings.hooks.PostToolUse.length, 1);
  assert.equal(first.settings.env.OTHER, 'SYNTH_SECRET_not_reported');
  assert.equal(JSON.stringify(first.ownership).includes('SYNTH_SECRET'), false);
  assert.equal(JSON.stringify(first.ownership).includes('operator-model'), false);
});

test('apply rejects incomplete desired lifecycle and unowned identical hooks', () => {
  const complete = desired();
  assert.throws(
    () => applyOwnedMainSessionHooks({
      current: {},
      desired: { ...complete, hooks: complete.hooks.slice(0, 1) },
      ownership: emptyMainSessionOwnership(),
    }),
    /DESIRED_HOOKS_INCOMPLETE/u,
  );
  const existing = {
    hooks: {
      PreToolUse: [complete.hooks[0].group],
      PostToolUse: [complete.hooks[1].group],
    },
  };
  assert.throws(
    () => applyOwnedMainSessionHooks({
      current: existing,
      desired: complete,
      ownership: emptyMainSessionOwnership(),
    }),
    /HOOK_ALREADY_PRESENT_UNOWNED/u,
  );
});

test('apply rejects forged desired identities and duplicate ownership entries', () => {
  const complete = desired();
  const forged = structuredClone(complete);
  forged.hooks[0].group.hooks[0].command = '/forged/guard';
  assert.throws(
    () => applyOwnedMainSessionHooks({
      current: {}, desired: forged, ownership: emptyMainSessionOwnership(),
    }),
    /DESIRED_HOOKS_INCOMPLETE/u,
  );

  const applied = applyOwnedMainSessionHooks({
    current: {}, desired: complete, ownership: emptyMainSessionOwnership(),
  });
  const duplicate = structuredClone(applied.ownership);
  duplicate.entries.push(structuredClone(duplicate.entries[0]));
  assert.throws(
    () => removeOwnedMainSessionHooks({ current: applied.settings, ownership: duplicate }),
    /OWNERSHIP_CONFLICT/u,
  );
});

test('owned removal deletes exact entries and preserves operator changes', () => {
  const applied = applyOwnedMainSessionHooks({
    current: { hooks: { Stop: [{ hooks: [{ type: 'command', command: '/operator/stop' }] }] } },
    desired: desired(),
    ownership: emptyMainSessionOwnership(),
  });
  const exact = removeOwnedMainSessionHooks({
    current: applied.settings,
    ownership: applied.ownership,
  });
  assert.deepEqual(exact.settings.hooks, {
    Stop: [{ hooks: [{ type: 'command', command: '/operator/stop' }] }],
  });
  assert.deepEqual(exact.conflicts, []);

  const changed = structuredClone(applied.settings);
  changed.hooks.PreToolUse[0].hooks[0].timeout = 30;
  const drifted = removeOwnedMainSessionHooks({
    current: changed,
    ownership: applied.ownership,
  });
  assert.equal(drifted.settings.hooks.PreToolUse[0].hooks[0].timeout, 30);
  assert.deepEqual(drifted.conflicts, ['hooks.PreToolUse']);
  assert.equal(drifted.settings.hooks.PostToolUse, undefined);
});

test('inspection distinguishes absent configured unproven and active states', () => {
  const wanted = desired();
  const absent = inspectMainSessionGuard({
    scopes: localScope({}),
    desired: wanted,
    ownership: emptyMainSessionOwnership(),
    capabilities: { hooks: true },
  });
  assert.deepEqual(absent, {
    state: 'ABSENT',
    reasonCode: 'MISSING_HOOKS',
    preHookExact: false,
    postHookExact: false,
    liveProof: false,
  });

  const applied = applyOwnedMainSessionHooks({
    current: {}, desired: wanted, ownership: emptyMainSessionOwnership(),
  });
  const unproven = inspectMainSessionGuard({
    scopes: localScope(applied.settings),
    desired: wanted,
    ownership: applied.ownership,
    capabilities: { hooks: true },
  });
  assert.equal(unproven.state, 'CONFIGURED_UNPROVEN');
  assert.equal(unproven.reasonCode, 'EXACT_SETTINGS_ONLY');
  assert.equal(unproven.liveProof, false);

  const active = inspectMainSessionGuard({
    scopes: localScope(applied.settings),
    desired: wanted,
    ownership: applied.ownership,
    capabilities: { hooks: true },
    liveProof: {
      command: 'printf P005_GUARD_PROBE',
      decision: 'deny',
      reasonCode: 'DENY_UNKNOWN_COMMAND',
      configurationIdentity: wanted.configurationIdentity,
    },
  });
  assert.equal(active.state, 'ACTIVE');
  assert.equal(active.reasonCode, 'EXACT_LIVE_PROOF');
  assert.equal(active.liveProof, true);
});

test('inspection rejects stale proof ownership drift managed policy and missing capability', () => {
  const wanted = desired();
  const applied = applyOwnedMainSessionHooks({
    current: {}, desired: wanted, ownership: emptyMainSessionOwnership(),
  });
  const staleProof = {
    command: 'printf P005_GUARD_PROBE',
    decision: 'deny',
    reasonCode: 'DENY_UNKNOWN_COMMAND',
    configurationIdentity: 'stale-runtime-or-settings',
  };
  assert.equal(inspectMainSessionGuard({
    scopes: localScope(applied.settings), desired: wanted,
    ownership: applied.ownership, capabilities: { hooks: true },
    liveProof: staleProof,
  }).state, 'CONFIGURED_UNPROVEN');
  assert.deepEqual(inspectMainSessionGuard({
    scopes: localScope(applied.settings), desired: wanted,
    ownership: emptyMainSessionOwnership(), capabilities: { hooks: true },
  }), {
    state: 'CONFLICT',
    reasonCode: 'OWNERSHIP_DRIFT',
    preHookExact: true,
    postHookExact: true,
    liveProof: false,
  });
  assert.equal(inspectMainSessionGuard({
    scopes: [
      ...localScope(applied.settings),
      { name: 'managed', precedence: 5, settings: { allowManagedHooksOnly: true } },
    ],
    desired: wanted, ownership: applied.ownership, capabilities: { hooks: true },
  }).reasonCode, 'MANAGED_POLICY_BLOCK');
  assert.equal(inspectMainSessionGuard({
    scopes: localScope(applied.settings), desired: wanted,
    ownership: applied.ownership, capabilities: { hooks: false },
  }).state, 'UNSUPPORTED');
});
