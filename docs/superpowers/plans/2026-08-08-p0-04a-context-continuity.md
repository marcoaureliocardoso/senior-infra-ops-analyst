# P0-04A Context Continuity and Preventive Compaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add native, capability-based continuity controls that preserve operational state across Claude Code compaction without retaining conversation content or stale credential authorization.

**Architecture:** A new `context-continuity` skill owns pure settings merge logic,
an explicit local configurator, a stateless status line, content-free compaction
hooks, and a numeric inventory collector. Root instructions and all 12 subagents
carry the durable semantic contract, while the existing command-guard binding
store gains atomic session invalidation. Deterministic tests, isolated Nori
installation, and live DeepSeek probes establish behavior without pinning
runtimes or context-window size.

**Tech Stack:** Node.js built-ins and native test runner, Bash, Python `unittest`, Claude Code native settings/hooks/task tools/status line, Nori Skillsets, GitHub Actions.

## Global Constraints

- Keep Claude Code auto-compaction enabled.
- Default `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` to configurable value `72`; preserve an existing value from 70 through 75.
- Never set `CLAUDE_CODE_AUTO_COMPACT_WINDOW` during normal configuration.
- Use an absolute-window override only after controlled evidence proves incorrect provider or gateway reporting and the operator approves it.
- Do not pin Claude Code, Nori, DeepSeek, provider, gateway, model, Node.js, or context-window size.
- Hooks always exit `0` and never persist transcript, prompt, compact summary, model output, raw event, command, secret, credential, or secret-derived identifier.
- Compaction invalidates unprovable authorization and literal-credential reuse.
- Preserve unrelated operator settings and hooks; rollback removes only values still proven to be P0-04A-owned.
- Use native task tools detected at runtime: `TaskCreate`/`TaskGet`/`TaskList`/`TaskUpdate` or `TodoWrite`.
- Retained context evidence contains only counts, bytes, percentages, booleans, reason codes, bounded timestamps, and non-secret runtime identifiers.
- P0-04B browser automation remains out of scope except for generic MCP/tool-search context measurements.
- Production behavior uses only native Node.js modules and existing package runtimes; add no npm dependency.
- Reverify behavior-sensitive Claude Code facts in current official Claude Code documentation and Nori ownership semantics in current official Nori source immediately before implementing the affected task; record versions only as observations.
- The definitive unversioned `C:\projects\senior-infra-ops-analyst\TODO-AI-FIRST.md` remains incomplete until merge to `main`, passing CI/Security, real validation, and independent review.

## File Structure

### New production files

- `skills/context-continuity/SKILL.md`: operator-facing capability, setup, recovery, and privacy instructions.
- `skills/context-continuity/nori.json`: Nori skill metadata.
- `skills/context-continuity/scripts/settings.mjs`: strict JSON parsing, scope discovery, desired settings, merge, inspection, ownership, and owned-only removal.
- `skills/context-continuity/scripts/configure-context-continuity.mjs`: `--check`, `--apply`, and `--remove-owned` CLI.
- `skills/context-continuity/scripts/context-statusline.mjs`: stdin JSON to one stateless context indicator.
- `skills/context-continuity/scripts/compact-hook.mjs`: bounded PreCompact/PostCompact parsing and exact-session invalidation.
- `skills/context-continuity/scripts/compact-hook-launcher.sh`: deadline, runtime fallback, always-zero exit, and all-binding invalidation fallback.
- `skills/context-continuity/scripts/context-inventory.mjs`: content-free static inventory and runtime-evidence normalization.

### New test files

- `tests/context-continuity/settings.test.mjs`: strict settings and CLI contracts.
- `tests/context-continuity/statusline.test.mjs`: status-line parsing and side-effect contract.
- `tests/context-continuity/compact-hook.test.mjs`: hook envelope, state, fallback, and sensitive-field tests.
- `tests/context-continuity/inventory.test.mjs`: static inventory and retained-evidence schema.
- `tests/context_continuity_install_policy.py`: canonical source and installed subagent hook policy.
- `tests/test-context-continuity-instructions.py`: root instruction and skill registration regressions.
- `tests/test-context-continuity-install-policy.py`: 12-agent source and installed hook regressions.
- `tests/test-live-context-continuity-safety.py`: live-harness isolation, retention, and provider-safety contract.
- `tests/live-context-continuity-smoke.sh`: opt-in Nori/Claude Code/DeepSeek validation.
- `tests/fixtures/context-continuity/*.jsonl`: synthetic, content-free runtime parser fixtures only.

### Existing files modified

- `AGENTS.md`: Compact Instructions and native task-list continuity rules.
- `nori.json`, `skills.json`: register the 25th skill and release metadata.
- `subagents/*.md`: native PreCompact/PostCompact hook block for all 12 roles.
- `skills/command-driven-operations/scripts/command-guard/binding-store.mjs`: atomic session and all-session invalidation.
- `tests/command-guard/binding-store.test.mjs`: authorization invalidation regression.
- `tests/validate-content.py`, `tests/validate-installed-subagents.py`, `tests/validate-package.sh`: package and installed-artifact enforcement.
- `tests/test-installed-subagents.py`, `tests/test-subagent-frontmatter.py`: installed and frontmatter negative fixtures.
- `tests/validation-notes.md`: deterministic and live execution policy.
- `README.md`, `docs.md`, `CHANGELOG.md`, `.nori-version`: implemented behavior and `0.12.0` release metadata.
- `docs/architecture/ADR-005-context-continuity-and-preventive-compaction.md`: implementation and validation evidence.

---

### Task 1: Add the durable continuity contract and register the skill

**Files:**
- Create: `skills/context-continuity/SKILL.md`
- Create: `skills/context-continuity/nori.json`
- Create: `tests/test-context-continuity-instructions.py`
- Modify: `AGENTS.md`
- Modify: `nori.json`
- Modify: `skills.json`
- Modify: `tests/validate-content.py`
- Modify: `tests/validate-schema.py`

**Interfaces:**
- Produces skill ID `context-continuity` and a Nori-installed script root at `{{skills_dir}}/context-continuity/scripts`.
- Produces exact root heading `## Context continuity and compaction` with one `<required>` block.
- Requires a native task list for long work and semantic detection of either task-tool family.
- Establishes the post-compaction rule that authorization is invalid unless current native state proves it again.

- [ ] **Step 1: Write failing root-contract tests**

Create `tests/test-context-continuity-instructions.py` using the repository-copy pattern from `tests/test-subagent-frontmatter.py`:

```python
REQUIRED = (
    "## Context continuity and compaction",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE",
    "TaskCreate`/`TaskGet`/`TaskList`/`TaskUpdate",
    "`TodoWrite`",
    "authorization or credential reuse",
    "transcript, prompt, compact summary, or secret",
    "Immediate next action",
)

def test_current_package_accepts_continuity_contract(self) -> None:
    result = self.run_validator()
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

def test_each_continuity_clause_is_required(self) -> None:
    for clause in REQUIRED:
        with self.subTest(clause=clause):
            self.agents.write_text(
                self.original.replace(clause, f"omitted-{len(clause)}", 1),
                encoding="utf-8",
            )
            result = self.run_validator()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing context continuity clause", result.stdout)
            self.agents.write_text(self.original, encoding="utf-8")
```

Add schema regressions that require `context-continuity` in both manifests and reject duplicate or missing registration.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
python tests/test-context-continuity-instructions.py
python tests/test-schema-validation.py
```

Expected: instruction tests fail because the heading and skill do not exist; manifest fixture fails when the required 25th skill is absent.

- [ ] **Step 3: Add the minimal Compact Instructions**

Insert this exact compact block in `AGENTS.md` immediately after `Native command authorization and credentials`:

```markdown
## Context continuity and compaction
<required>
1. Keep auto-compaction enabled. Prefer `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` from 70 through 75; the package default is 72. Never assume an absolute context size.
2. For long work, maintain the native task list. Use `TaskCreate`/`TaskGet`/`TaskList`/`TaskUpdate` when available or `TodoWrite` on runtimes that expose that interface. Read it immediately after compaction.
3. Compact the minimum operational ledger: current objective and completion criteria; scope exclusions; approved decisions and rejected alternatives; evidence and artifact locations; branch, commits, files, tests, blockers, residual risks, rollback, and Immediate next action.
4. Treat compaction as invalidating any authorization or credential reuse that current native state cannot prove again. Reprompt before literal credential reuse.
5. Never preserve transcript, prompt, compact summary, or secret as a continuity artifact. Preserve references and non-secret results, not conversation content.
6. When context pressure persists, inspect `/context`, narrow skills and MCPs, read large artifacts in chunks, use focused `/compact` instructions, and state what `/rewind`, `/clear`, or `/resume` invalidates.
</required>
```

- [ ] **Step 4: Add the skill metadata and operator instructions**

Create `skills/context-continuity/nori.json`:

```json
{
  "name": "context-continuity",
  "version": "1.0.0",
  "type": "skill",
  "description": "Use for long Claude Code work, context pressure, compaction recovery, native task continuity, local preventive-compaction configuration, or context-cost measurement."
}
```

Create `skills/context-continuity/SKILL.md` with frontmatter matching that description and sections `When to use`, `Capability check`, `Configure`, `During long work`, `After compaction`, `Recovery`, `Privacy`, and `Limitations`. The command surface is exact:

```bash
node "${SKILL_ROOT}/scripts/configure-context-continuity.mjs" --check --scope project
node "${SKILL_ROOT}/scripts/configure-context-continuity.mjs" --apply --scope project
node "${SKILL_ROOT}/scripts/configure-context-continuity.mjs" --apply --scope project --status-line
node "${SKILL_ROOT}/scripts/configure-context-continuity.mjs" --remove-owned --scope project
node "${SKILL_ROOT}/scripts/context-inventory.mjs" --root PROJECT_ROOT
```

State that `${SKILL_ROOT}` means the installed `context-continuity` directory and must be resolved before execution; do not embed a fixed home or Nori path.

- [ ] **Step 5: Register and validate the skill**

Append `context-continuity` once to root `nori.json` and add
`"context-continuity": "*"` to `skills.json`. Extend `tests/validate-content.py` with:

```python
CONTINUITY_CLAUSES = (
    "## Context continuity and compaction",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE",
    "TaskCreate`/`TaskGet`/`TaskList`/`TaskUpdate",
    "`TodoWrite`",
    "authorization or credential reuse",
    "transcript, prompt, compact summary, or secret",
    "Immediate next action",
)
for clause in CONTINUITY_CLAUSES:
    if clause not in agents_text:
        err(f"missing context continuity clause: {clause}")
```

Run:

```powershell
python tests/test-context-continuity-instructions.py
python tests/test-schema-validation.py
python tests/validate-content.py
```

Expected: all pass.

- [ ] **Step 6: Commit the durable contract**

```powershell
git add AGENTS.md nori.json skills.json skills/context-continuity `
  tests/test-context-continuity-instructions.py tests/validate-content.py `
  tests/validate-schema.py tests/test-schema-validation.py
git commit -m "feat: add context continuity contract"
```

---

### Task 2: Implement conflict-aware local settings ownership

**Files:**
- Create: `skills/context-continuity/scripts/settings.mjs`
- Create: `skills/context-continuity/scripts/configure-context-continuity.mjs`
- Create: `tests/context-continuity/settings.test.mjs`
- Modify: `skills/context-continuity/SKILL.md`
- Modify: `tests/validate-package.sh`

**Interfaces:**
- `parseStrictObject(text: string, source: string) -> object` rejects invalid JSON, non-object roots, and duplicate keys at every depth.
- `discoverSettingScopes({repoRoot, claudeConfigDir, platform, managedPath}) -> Scope[]`, where `Scope` is `{name, path, precedence, writable}`.
- `desiredOwnedSettings({skillRoot, includeStatusLine, nodeBin, platform}) -> object` returns only `env`, `hooks`, and optional `statusLine` fragments.
- `inspectContinuity({scopes, desired, ownership}) -> Report` returns status and reason codes without environment values.
- `applyOwnedSettings({current, ownership, desired}) -> {settings, ownership}` is pure and conflict-aware.
- `removeOwnedSettings({current, ownership}) -> {settings, ownership, conflicts}` removes only exact owned values.
- `quoteStatusCommand(nodeBin: string, scriptPath: string, platform: string) -> string` quotes exactly two literal path arguments for the selected platform.
- `probeClaudeCapabilities({claudeBin, run}) -> object` inspects bounded local help output and returns booleans plus a bounded observed version; it never starts a model request.
- CLI accepts exactly one of `--check`, `--apply`, `--remove-owned`; `--scope project|user`; optional `--root PATH`, `--claude-config-dir PATH`, `--managed-settings PATH`, and `--status-line`.
- Exit `0`: requested operation is safe and complete. Exit `1`: invalid input or invariant failure. Exit `2`: operator-visible conflict or disabled auto-compaction.

- [ ] **Step 1: Write strict parser and merge tests**

Create table-driven Node tests for:

```javascript
test('strict parser rejects duplicate keys at every depth', () => {
  for (const raw of [
    '{"env":{},"env":{}}',
    '{"env":{"A":"1","A":"2"}}',
    '{"hooks":{"PreCompact":[],"PreCompact":[]}}',
  ]) assert.throws(() => parseStrictObject(raw, 'fixture'), /duplicate JSON key/u);
});

test('apply preserves unrelated settings and chooses 72 only when absent', () => {
  const current = { model: 'operator-model', env: { OTHER: 'keep' }, hooks: { Stop: [{ hooks: [] }] } };
  const result = applyOwnedSettings({ current, ownership: emptyOwnership(), desired: desiredOwnedSettings({ skillRoot: '/installed/context-continuity', includeStatusLine: false, nodeBin: '/usr/bin/node', platform: 'linux' }) });
  assert.equal(result.settings.model, 'operator-model');
  assert.equal(result.settings.env.OTHER, 'keep');
  assert.equal(result.settings.env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE, '72');
  assert.deepEqual(result.settings.hooks.Stop, current.hooks.Stop);
  assert.equal('CLAUDE_CODE_AUTO_COMPACT_WINDOW' in result.settings.env, false);
});

test('existing 70 through 75 is preserved and outside range conflicts', () => {
  for (const value of ['70', '71', '72', '73', '74', '75']) {
    const report = inspectFixture({ env: { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: value } });
    assert.equal(report.blockers.length, 0, value);
    assert.equal(report.effective.autoCompactPercent, Number(value));
  }
  for (const value of ['1', '69', '76', '100', 'text']) {
    assert.match(inspectFixture({ env: { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: value } }).blockers[0].code, /AUTOCOMPACT_PERCENT_CONFLICT/u);
  }
});
```

Add cases for `autoCompactEnabled: false`, `DISABLE_AUTO_COMPACT`,
`DISABLE_COMPACT`, conflicting higher-precedence managed/user/project/local
values, symlink targets, nonexistent parents, owner-only removal, changed-owned
values, repeat apply, repeat removal, Windows/POSIX paths, and output scans that
reject values of keys matching `TOKEN|KEY|SECRET|PASSWORD|CREDENTIAL|AUTH`.
Add an existing `PreCompact` and `PostCompact` handler fixture and prove apply
appends exactly one owned handler while removal deletes only that exact handler.
Add bounded `claude --help`, `claude mcp --help`, missing binary, timeout, and
unrecognized future-help fixtures for `probeClaudeCapabilities`.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
node --test tests/context-continuity/settings.test.mjs
```

Expected: FAIL with module-not-found for `settings.mjs`.

- [ ] **Step 3: Implement strict JSON and scope discovery**

In `settings.mjs`, export frozen reason codes and implement a character scanner
that tracks object key sets at every `{}` depth before calling `JSON.parse`.
The scanner must understand JSON escapes and strings so braces or colons inside
strings never affect structure. Then implement:

```javascript
export const OWNERSHIP_VERSION = 1;
export const DEFAULT_PERCENT = '72';
export const ALLOWED_PERCENT = Object.freeze(new Set(['70', '71', '72', '73', '74', '75']));

export function discoverSettingScopes({ repoRoot, claudeConfigDir, platform = process.platform, managedPath }) {
  const managed = managedPath ?? documentedManagedPath(platform);
  return Object.freeze([
    { name: 'managed', path: managed, precedence: 4, writable: false },
    { name: 'user', path: path.join(claudeConfigDir, 'settings.json'), precedence: 1, writable: true },
    { name: 'project', path: path.join(repoRoot, '.claude', 'settings.json'), precedence: 2, writable: true },
    { name: 'local', path: path.join(repoRoot, '.claude', 'settings.local.json'), precedence: 3, writable: true },
  ]);
}
```

`documentedManagedPath()` returns the current official platform path for
Windows, macOS, or Linux. Tests own the path contract; versions never do.

- [ ] **Step 4: Implement desired settings and ownership**

Generate only these settings when `includeStatusLine` is false:

```javascript
export function desiredOwnedSettings({ skillRoot, includeStatusLine = false, nodeBin = process.execPath, platform = process.platform }) {
  const launcher = path.join(skillRoot, 'scripts', 'compact-hook-launcher.sh');
  const desired = {
    env: { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: DEFAULT_PERCENT },
    hooks: {
      PreCompact: [{ hooks: [{ type: 'command', command: launcher, args: ['pre'], timeout: 5 }] }],
      PostCompact: [{ hooks: [{ type: 'command', command: launcher, args: ['post'], timeout: 5 }] }],
    },
  };
  if (includeStatusLine) desired.statusLine = {
    type: 'command', command: quoteStatusCommand(nodeBin, path.join(skillRoot, 'scripts', 'context-statusline.mjs'), platform),
  };
  return Object.freeze(desired);
}
```

`applyOwnedSettings` merges `env` by key, appends the exact owned hook only
when no deep-equal entry exists, and treats an identical unowned hook as safe
but unowned. It never replaces a hook array. `removeOwnedSettings` filters only
deep-equal entries recorded in ownership and removes an empty event key or
empty `hooks`/`env` parent only when P0-04A made it empty.

Store ownership adjacent to the selected settings file as
`.context-continuity-owned.json`. It contains only `version`, selected scope,
canonical setting paths, and exact non-secret values. Reject symlink settings
and ownership files. Write both through owner-only temporary files and atomic
rename; if the second write fails, restore the first from an owner-only
temporary backup before returning failure.

- [ ] **Step 5: Implement CLI without secret output**

`--check` emits one JSON object with this allowlist:

```javascript
const publicReport = {
  schemaVersion: 1,
  operation,
  scope,
  settingsPath,
  autoCompactEnabled,
  autoCompactPercent,
  hooks: { preCompact: boolean, postCompact: boolean },
  statusLine: { requested: boolean, owned: boolean, conflict: boolean },
  capabilities,
  blockers: blockers.map(({ code, scope }) => ({ code, scope })),
};
```

`probeClaudeCapabilities` runs only bounded local commands with a 2-second
deadline:

```javascript
const probes = Object.freeze([
  { id: 'cli', args: ['--help'] },
  { id: 'mcp', args: ['mcp', '--help'] },
  { id: 'version', args: ['--version'] },
]);
```

It derives `resume`, `rewind`, `agent`, `mcp`, and `printStreamJson` booleans
from literal help flags and reports unknown features as false with reason code
`CAPABILITY_NOT_OBSERVED`. Native task tools and tool search are deliberately
left `unknown` here because only a model session can observe them; Task 7 fills
those fields without converting absence into success.

Never include arbitrary key names or values. `--apply` first runs the same
inspection and refuses blocker codes. `--remove-owned` removes only exact
matches recorded in ownership and leaves conflicts unchanged.

- [ ] **Step 6: Verify GREEN and CLI behavior**

Run:

```powershell
node --test tests/context-continuity/settings.test.mjs
$sandbox = Join-Path $env:TEMP 'p0-04a-settings-fixture'
node skills/context-continuity/scripts/configure-context-continuity.mjs --apply --scope project --root $sandbox --claude-config-dir (Join-Path $sandbox 'home')
node skills/context-continuity/scripts/configure-context-continuity.mjs --check --scope project --root $sandbox --claude-config-dir (Join-Path $sandbox 'home')
node skills/context-continuity/scripts/configure-context-continuity.mjs --remove-owned --scope project --root $sandbox --claude-config-dir (Join-Path $sandbox 'home')
```

Expected: tests pass; apply/check/remove exit `0`; reports contain no fixture
secret values; normal settings never contain `CLAUDE_CODE_AUTO_COMPACT_WINDOW`.

- [ ] **Step 7: Add the suite to the package gate and commit**

Add `node --test tests/context-continuity/settings.test.mjs` before content
validation in `tests/validate-package.sh`, then run it once through Git Bash.

```powershell
git add skills/context-continuity tests/context-continuity/settings.test.mjs `
  tests/validate-package.sh
git commit -m "feat: configure preventive compaction safely"
```

---

### Task 3: Add the opt-in stateless status line

**Files:**
- Create: `skills/context-continuity/scripts/context-statusline.mjs`
- Create: `tests/context-continuity/statusline.test.mjs`
- Modify: `skills/context-continuity/scripts/settings.mjs`
- Modify: `tests/context-continuity/settings.test.mjs`
- Modify: `tests/validate-package.sh`

**Interfaces:**
- `renderStatusLine(value: unknown) -> string` returns exactly `ctx NN%` for a finite percentage from 0 through 100, otherwise `ctx --`.
- `main({input, output}) -> Promise<number>` reads at most 64 KiB, writes one line, performs no other I/O, and returns `0` for missing, null, malformed, or forward-compatible input.
- Settings installation occurs only with explicit `--status-line` and conflicts with an unowned effective status line.

- [ ] **Step 1: Write failing status-line tests**

```javascript
test('renders documented used percentage', () => {
  assert.equal(renderStatusLine({ context_window: { used_percentage: 72 } }), 'ctx 72%');
  assert.equal(renderStatusLine({ context_window: { remaining_percentage: 28 } }), 'ctx 72%');
});

test('renders neutral state for unavailable or unsafe values', () => {
  for (const value of [null, {}, { context_window: null }, { context_window: { used_percentage: null } }, { context_window: { used_percentage: -1 } }, { context_window: { used_percentage: 101 } }]) {
    assert.equal(renderStatusLine(value), 'ctx --');
  }
});

test('executable writes no files and one bounded line', () => {
  const result = spawnSync(process.execPath, [ENTRYPOINT], { input: JSON.stringify({ context_window: { used_percentage: 70 }, model: { display_name: 'secret-looking-but-ignored' } }), encoding: 'utf8', cwd: emptyDirectory });
  assert.equal(result.status, 0);
  assert.equal(result.stdout, 'ctx 70%\n');
  assert.equal(result.stderr, '');
  assert.deepEqual(readdirSync(emptyDirectory), []);
});
```

- [ ] **Step 2: Run tests and verify RED**

Run `node --test tests/context-continuity/statusline.test.mjs`.

Expected: FAIL because `context-statusline.mjs` does not exist.

- [ ] **Step 3: Implement the renderer**

Use documented fields only:

```javascript
export function renderStatusLine(value) {
  const context = value && typeof value === 'object' ? value.context_window : null;
  const used = context?.used_percentage;
  const remaining = context?.remaining_percentage;
  const percent = Number.isFinite(used) ? used : Number.isFinite(remaining) ? 100 - remaining : null;
  return percent !== null && percent >= 0 && percent <= 100 ? `ctx ${Math.round(percent)}%` : 'ctx --';
}
```

Implement a bounded stdin reader; catch every parse/read error and emit
`ctx --\n`. Do not import `fs`, `net`, `http`, `https`, or `child_process`.

- [ ] **Step 4: Prove opt-in ownership behavior**

Extend settings tests so default apply omits `statusLine`, `--status-line`
installs it when absent, an unowned existing status line produces
`STATUS_LINE_CONFLICT`, and removal preserves a value changed after apply.

- [ ] **Step 5: Run GREEN, integrate, and commit**

```powershell
node --test tests/context-continuity/statusline.test.mjs tests/context-continuity/settings.test.mjs
git add skills/context-continuity/scripts tests/context-continuity `
  tests/validate-package.sh
git commit -m "feat: add opt-in context status line"
```

---

### Task 4: Invalidate credential reuse with non-blocking compact hooks

**Files:**
- Create: `skills/context-continuity/scripts/compact-hook.mjs`
- Create: `skills/context-continuity/scripts/compact-hook-launcher.sh`
- Create: `tests/context-continuity/compact-hook.test.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/binding-store.mjs`
- Modify: `tests/command-guard/binding-store.test.mjs`
- Modify: `tests/validate-package.sh`

**Interfaces:**
- `invalidateSessionBindings(sessionId: string, env = process.env) -> boolean` atomically replaces one state with empty pending/active arrays.
- `invalidateAllBindings(env = process.env) -> number` invalidates only regular non-symlink `^[a-f0-9]{64}\.json$` state files under the exact command-guard state directory.
- `parseCompactEnvelope(raw: string, expectedPhase: 'PreCompact'|'PostCompact') -> {sessionId, trigger}` reads only bounded identity fields.
- `evaluateCompactHook(raw, phase, env) -> {phase, invalidated, degraded}` never returns content.
- `main({input,error,env,args}) -> Promise<0>` always returns `0`; success is silent and degraded state writes one constant warning to stderr.
- Launcher accepts exactly `pre` or `post`, enforces a 3-second inner deadline, and exits `0` on every path.

- [ ] **Step 1: Write RED authorization tests**

Extend `tests/command-guard/binding-store.test.mjs`:

```javascript
test('compaction invalidates pending and active reuse for only that session', async () => {
  await withState(async (env) => {
    const other = { ...binding, sessionId: 'other-session', toolUseId: 'other-tool' };
    writePendingBinding(binding, env, NOW);
    activatePendingBinding(binding, env, NOW + 1);
    writePendingBinding(other, env, NOW);
    activatePendingBinding(other, env, NOW + 1);
    assert.equal(invalidateSessionBindings(binding.sessionId, env), true);
    assert.equal(hasActiveBinding(binding, env, NOW + 2), false);
    assert.equal(hasActiveBinding(other, env, NOW + 2), true);
  });
});
```

Add a full flow fixture: first literal use `ask`, matching post activates,
second use `allow`, PreCompact invalidates, third use returns `ask` again.

- [ ] **Step 2: Run binding tests and verify RED**

Run:

```powershell
node --test tests/command-guard/binding-store.test.mjs
```

Expected: FAIL because `invalidateSessionBindings` is not exported.

- [ ] **Step 3: Implement atomic invalidation**

Reuse `requiredBounded`, `statePath`, `emptyState`, and `writeState`:

```javascript
function atomicWriteTarget(target, state) {
  const temporary = `${target}.${process.pid}.${randomBytes(8).toString('hex')}.tmp`;
  const serialized = `${JSON.stringify(state)}\n`;
  if (Buffer.byteLength(serialized, 'utf8') > MAX_STATE_BYTES) throw new Error('binding state size exceeded');
  writeFileSync(temporary, serialized, { encoding: 'utf8', mode: 0o600, flag: 'wx' });
  chmodSync(temporary, 0o600);
  renameSync(temporary, target);
}

export function invalidateSessionBindings(sessionId, env = process.env) {
  const bounded = requiredBounded(sessionId, 'sessionId');
  writeState(bounded, emptyState(), env);
  return true;
}

export function invalidateAllBindings(env = process.env) {
  const directory = stateDirectory(env);
  if (!existsSync(directory)) return 0;
  let count = 0;
  for (const name of readdirSync(directory)) {
    if (!/^[a-f0-9]{64}\.json$/u.test(name)) continue;
    const target = path.join(directory, name);
    const info = lstatSync(target);
    if (!info.isFile() || info.isSymbolicLink()) continue;
    atomicWriteTarget(target, emptyState());
    count += 1;
  }
  return count;
}
```

Refactor the existing `writeState` to call `atomicWriteTarget`; retain its
directory creation and owner-only permission checks. Import `readdirSync` and
do not follow directory or file symlinks.

- [ ] **Step 4: Write RED hook privacy and exit tests**

Cover exact PreCompact/PostCompact events, `manual`/`auto` trigger, missing or
oversized session IDs, invalid UTF-8, 64-KiB bound, deeply nested unknown data,
duplicate identity keys, transcript paths, custom instructions, compact
summaries, synthetic secrets, storage failure, deadline, missing Node, and
concurrent delivery. Required assertions:

```javascript
assert.equal(result.status, 0);
assert.equal(result.stdout, '');
assert.doesNotMatch(retainedState, /SYNTH_SECRET|transcript|prompt|summary|command/iu);
assert.match(result.stderr, /Context continuity degraded\./u);
```

For successful events, stderr is empty and only the targeted session becomes
unbound. For malformed identity, invoke all-binding invalidation and verify no
active binding remains.

- [ ] **Step 5: Implement the content-free hook**

Use a 64-KiB reader and access only:

```javascript
const eventName = value.hook_event_name;
const sessionId = boundedIdentifier(value.session_id, 'session_id');
const trigger = value.trigger === 'manual' || value.trigger === 'auto' ? value.trigger : 'unknown';
```

Never spread or serialize `value`. On any exception, call
`invalidateAllBindings(env)`, write only `Context continuity degraded. Credential reuse requires fresh approval.\n`, and return `0`.

The launcher uses stdin directly without a temporary payload file:

```bash
#!/usr/bin/env bash
set +e
PATH="/usr/bin:/bin:${PATH:-}"
export PATH
umask 077
phase="${1:-invalid}"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" 2>/dev/null && pwd -P)"
node_bin="$(command -v node 2>/dev/null)"
timeout_bin="$(command -v timeout 2>/dev/null)"
if [[ "$phase" =~ ^(pre|post)$ && -n "$node_bin" && -n "$timeout_bin" ]]; then
  "$timeout_bin" --signal=TERM --kill-after=1s 3s "$node_bin" "$script_dir/compact-hook.mjs" "$phase"
  status=$?
else
  status=1
fi
if [[ $status -ne 0 ]]; then
  state_dir="${OPS_COMMAND_GUARD_STATE_DIR:-${HOME:?}/.claude/senior-infra-ops-analyst/command-guard-state}"
  if [[ -d "$state_dir" && ! -L "$state_dir" ]]; then
    for target in "$state_dir"/*.json; do
      [[ -f "$target" && ! -L "$target" ]] || continue
      name="${target##*/}"
      [[ "$name" =~ ^[0-9a-f]{64}\.json$ ]] || continue
      temporary="$target.$$.${RANDOM}.tmp"
      if (umask 077; printf '%s\n' '{"version":1,"pending":[],"active":[]}' > "$temporary") &&
         chmod 600 "$temporary" && mv -f -- "$temporary" "$target"; then
        :
      else
        rm -f -- "$temporary"
      fi
    done
  fi
  printf '%s\n' 'Context continuity degraded. Credential reuse requires fresh approval.' >&2
fi
exit 0
```

The fallback must not print paths or file contents. Add fixtures for unmatched
globs, symlinks, near-match names, failed rename, and an unset `HOME`; every
case still exits `0` and never changes a non-matching file.

- [ ] **Step 6: Verify hook behavior and package integration**

```powershell
node --test tests/context-continuity/compact-hook.test.mjs `
  tests/command-guard/binding-store.test.mjs
& 'C:\Program Files\Git\bin\bash.exe' -lc 'export PATH=/usr/bin:/mingw64/bin:$PATH; bash -n skills/context-continuity/scripts/compact-hook-launcher.sh; node --test tests/context-continuity/compact-hook.test.mjs'
```

Expected: all tests pass; every launcher fixture exits `0`; credential reuse
returns `ask` after compaction.

- [ ] **Step 7: Commit the authorization boundary**

```powershell
git add skills/context-continuity/scripts skills/command-driven-operations/scripts/command-guard/binding-store.mjs `
  tests/context-continuity/compact-hook.test.mjs tests/command-guard/binding-store.test.mjs `
  tests/validate-package.sh
git commit -m "feat: invalidate credential reuse on compaction"
```

---

### Task 5: Distribute compact hooks to all subagents and installed Nori artifacts

**Files:**
- Create: `tests/context_continuity_install_policy.py`
- Create: `tests/test-context-continuity-install-policy.py`
- Modify: all 12 `subagents/*.md`
- Modify: `tests/validate-content.py`
- Modify: `tests/validate-installed-subagents.py`
- Modify: `tests/test-installed-subagents.py`
- Modify: `tests/test-subagent-frontmatter.py`
- Modify: `tests/validate-package.sh`

**Interfaces:**
- `source_continuity_hook_errors(agentId, text) -> list[str]` requires one canonical PreCompact and one PostCompact block in every source subagent.
- `installed_continuity_hook_errors(agentId, source, installed, installedSkillsDir) -> list[str]` accepts only Nori's resolved installed path and byte-equal hook artifacts.
- Existing executor PreToolUse/PostToolUse command-guard semantics remain unchanged.

- [ ] **Step 1: Write source-policy RED tests**

Define the canonical block in `tests/context_continuity_install_policy.py`:

```python
CANONICAL_CONTINUITY_HOOKS = '''  PreCompact:
    - hooks:
        - type: command
          command: "{{skills_dir}}/context-continuity/scripts/compact-hook-launcher.sh"
          args:
            - pre
          timeout: 5
  PostCompact:
    - hooks:
        - type: command
          command: "{{skills_dir}}/context-continuity/scripts/compact-hook-launcher.sh"
          args:
            - post
          timeout: 5
'''
```

For analytical roles, insert a new `hooks:` parent followed by this block. For
executors, append the two events under the existing `hooks:` parent. Tests
remove one phase, duplicate one phase, change timeout, change path, add a
matcher, change arg, or insert `async: true`; each must fail with a stable
reason code.

- [ ] **Step 2: Run policy tests and verify RED**

Run:

```powershell
python tests/test-context-continuity-install-policy.py
python tests/test-subagent-frontmatter.py
```

Expected: all 12 roles fail the missing-continuity-hook invariant.

- [ ] **Step 3: Add exact hooks to all 12 subagents**

Preserve the existing eight command-guard hook blocks byte for byte. Add the
canonical compact phases to executors and one hooks parent to each analytical
role. Do not preload `context-continuity`; the skill is installed package-wide
and the hook path resolves through `{{skills_dir}}` without adding its body to
every subagent context.

- [ ] **Step 4: Extend source and installed validators**

In `tests/validate-content.py`, call
`source_continuity_hook_errors(agent_id, text)` for every registered role. In
`tests/validate-installed-subagents.py`, call:

```python
errors.extend(installed_continuity_hook_errors(
    agent_id, source, installed, installed_skills_dir
))
```

Add these artifacts to the installed byte-comparison set:

```python
CONTINUITY_ARTIFACTS = (
    Path("context-continuity/scripts/compact-hook-launcher.sh"),
    Path("context-continuity/scripts/compact-hook.mjs"),
    Path("context-continuity/scripts/context-statusline.mjs"),
    Path("context-continuity/scripts/settings.mjs"),
    Path("context-continuity/scripts/configure-context-continuity.mjs"),
)
```

- [ ] **Step 5: Prove installed Nori preservation**

Extend `tests/test-installed-subagents.py` with fixtures that resolve
`{{skills_dir}}`, preserve an unrelated operator hook in `settings.json`, add a
preference after initial install, switch the skillset again, and assert both
preferences remain. Mutate one installed compact hook and one installed script
byte; each must fail.

- [ ] **Step 6: Run GREEN and commit**

```powershell
python tests/test-context-continuity-install-policy.py
python tests/test-subagent-frontmatter.py
python tests/test-installed-subagents.py
python tests/validate-content.py
git add subagents tests/context_continuity_install_policy.py `
  tests/test-context-continuity-install-policy.py tests/validate-content.py `
  tests/validate-installed-subagents.py tests/test-installed-subagents.py `
  tests/test-subagent-frontmatter.py tests/validate-package.sh
git commit -m "feat: distribute non-blocking compact hooks"
```

---

### Task 6: Measure skills, subagents, MCPs, and tool search without retaining content

**Files:**
- Create: `skills/context-continuity/scripts/context-inventory.mjs`
- Create: `tests/context-continuity/inventory.test.mjs`
- Create: `tests/fixtures/context-continuity/tool-search-available.jsonl`
- Create: `tests/fixtures/context-continuity/tool-search-unavailable.jsonl`
- Modify: `skills/context-continuity/SKILL.md`
- Modify: `tests/validate-package.sh`

**Interfaces:**
- `collectStaticInventory(root: string) -> Inventory` returns root, per-skill, per-subagent, MCP-manifest, and preload byte/count data.
- `normalizeRuntimeEvidence(events: Iterable<object>) -> RuntimeEvidence` returns percentages, counts, booleans, observed identifiers, and reason codes only.
- CLI `context-inventory.mjs --root PATH [--runtime-jsonl PATH]` emits one JSON document and refuses output paths.
- Forbidden keys recursively include `content`, `prompt`, `response`, `summary`, `transcript`, `tool_input`, `tool_result`, `command`, `header`, `credential`, `secret`, and `token`.

- [ ] **Step 1: Write RED static inventory tests**

```javascript
test('inventory measures every registered skill and subagent', async () => {
  const report = await collectStaticInventory(ROOT);
  assert.equal(report.skills.count, 25);
  assert.equal(report.subagents.count, 12);
  assert.equal(report.skills.items.every(({ id, bodyBytes, descriptionBytes }) => id && bodyBytes > 0 && descriptionBytes > 0), true);
  assert.equal(report.subagents.items.every(({ id, definitionBytes, preloadBytes }) => id && definitionBytes > 0 && preloadBytes > 0), true);
});

test('retained schema cannot carry content', () => {
  const report = normalizeRuntimeEvidence(syntheticEventsContainingSecrets);
  assert.deepEqual(findForbiddenKeys(report), []);
  assert.doesNotMatch(JSON.stringify(report), /SYNTH_SECRET|synthetic prompt|tool output/u);
});
```

Add deterministic available/unavailable tool-search fixtures and assert distinct
reason codes `TOOL_SEARCH_AVAILABLE`, `TOOL_SEARCH_UNAVAILABLE_GATEWAY`, and
`TOOL_SEARCH_NOT_OBSERVED`. Add MCP count fixtures with no server, one connected
server, and descriptions unavailable.

- [ ] **Step 2: Run tests and verify RED**

Run `node --test tests/context-continuity/inventory.test.mjs`.

Expected: FAIL because the inventory module does not exist.

- [ ] **Step 3: Implement content-free static measurement**

Use `Buffer.byteLength`, manifest registrations, parsed subagent `skills:`, and
file metadata. Output item IDs and numbers only:

```javascript
{
  schemaVersion: 1,
  rootInstructions: { bytes, lines },
  skills: { count, totalBodyBytes, totalDescriptionBytes, items },
  subagents: { count, totalDefinitionBytes, items },
  mcp: { packageServerCount },
}
```

Do not estimate tokens or infer an absolute window.

- [ ] **Step 4: Implement runtime normalization**

Accept only fields needed to derive:

```javascript
{
  context: { beforePercent, afterPercent, deltaPercent, compactionCount },
  tasks: { toolFamily, createdCount, completedCount, survivedCompaction },
  tools: { visibleCountBefore, visibleCountAfter, searchAvailable, reasonCode },
  mcp: { connectedCount, visibleToolCount },
  runtime: { claudeCode, nori, modelLabel, providerLabel, platform },
}
```

All strings pass `boundedIdentifier` and cannot contain whitespace, path
separators, `=`, `:`, or more than 128 characters. Untrusted event fields are
counted or converted to booleans, never copied.

- [ ] **Step 5: Run GREEN, scan output, and commit**

```powershell
node --test tests/context-continuity/inventory.test.mjs
node skills/context-continuity/scripts/context-inventory.mjs --root .
git add skills/context-continuity tests/context-continuity `
  tests/fixtures/context-continuity tests/validate-package.sh
git commit -m "feat: measure context capability costs"
```

Expected: 25 skills, 12 subagents, zero package MCPs, no token estimate, and no
forbidden retained key or synthetic content.

---

### Task 7: Build isolated live Claude Code and DeepSeek validation

**Files:**
- Create: `tests/live-context-continuity-smoke.sh`
- Create: `tests/test-live-context-continuity-safety.py`
- Modify: `tests/validation-notes.md`
- Modify: `tests/validate-package.sh`
- Modify: `.gitignore` only if the harness creates a repository-local artifact directory

**Interfaces:**
- CLI `bash tests/live-context-continuity-smoke.sh --self-test|--run-live [--keep-artifacts]`.
- Exit `0`: requested deterministic or live invariants passed.
- Exit `1`: safety or behavioral invariant failed.
- Exit `2`: prerequisite/capability unavailable; never reported as pass.
- Live mode requires `P0_04A_LIVE_NORMAL_CREDENTIALS_ACK=I_ACCEPT_PROVIDER_CREDENTIAL_EGRESS_RISK`.
- Retained result is `context-continuity-evidence.json` using Task 6's schema; temporary JSONL/TUI captures are deleted unless explicitly kept and never enter the repository.

- [ ] **Step 1: Write the safety contract before the harness**

Create Python static tests requiring:

```python
REQUIRED = (
    "set -euo pipefail", "umask 077", "mktemp -d", "CLAUDE_CONFIG_DIR",
    "P0_04A_LIVE_NORMAL_CREDENTIALS_ACK", "Bubblewrap", "--self-test",
    "--run-live", "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=5",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW", "context-continuity-evidence.json",
)
FORBIDDEN = (
    "cp $REAL_HOME/.claude/settings.json", "cat $SOURCE_CLAUDE_SETTINGS",
    "set -x", "env >", "printenv", "--dangerously-skip-permissions",
)
```

Require exact cleanup of transcript/TUI files, loopback-only mock gateway,
allowlisted settings import through the existing NUL-delimited FIFO pattern,
non-root Bubblewrap, bounded `timeout`, and no production target string.

- [ ] **Step 2: Run safety tests and verify RED**

Run `python tests/test-live-context-continuity-safety.py`.

Expected: FAIL because the harness does not exist.

- [ ] **Step 3: Implement parser self-test mode**

`--self-test` generates synthetic JSONL under `mktemp -d` and proves:

1. Task family detection for both `TaskCreate`/`TaskUpdate` and `TodoWrite`.
2. PreCompact then PostCompact increments one compaction without copying
   `custom_instructions` or `compact_summary`.
3. Task identifiers observed before and after compaction yield
   `survivedCompaction: true` without retaining task text.
4. Available and unavailable tool-search branches produce their exact reason
   codes.
5. Correct and divergent window metadata are distinguishable.
6. Forbidden-content scan fails on one deliberately unsafe retained fixture.

End with exact line `live context continuity parser self-test passed`.

- [ ] **Step 4: Implement generated-home Nori setup**

Reuse the isolation model from `tests/live-command-guard-smoke.sh`:

```bash
WORK="$(mktemp -d)"
REAL_HOME="$HOME"
export HOME="$WORK/home"
export CLAUDE_CONFIG_DIR="$HOME/.claude"
mkdir -p "$CLAUDE_CONFIG_DIR"
```

Import only the existing approved Claude transport allowlist without printing
values. Install the current worktree through discovered Nori into the generated
home, run `validate-installed-subagents.py`, then run:

```bash
node "$HOME/.claude/skills/context-continuity/scripts/configure-context-continuity.mjs" \
  --apply --scope project --root "$WORK/project" \
  --claude-config-dir "$CLAUDE_CONFIG_DIR" --status-line
```

Assert production settings contain `72`, both compact hooks, the owned status
line, and no absolute-window override. Add unrelated settings and hooks before
apply and after Nori switch; assert both survive apply, switch, and owned-only
removal.

- [ ] **Step 5: Implement real manual and automatic compaction probes**

Inside Bubblewrap, use a pseudo-terminal (`script`) for interactive commands
and stream JSON for non-interactive probes. Every capture stays in `$WORK`.

Run these scenarios with synthetic task labels and no operational target:

1. `/context` in main and each of the 12 subagent roles; retain percentages and
   counts only.
2. Create two native tasks, complete one, invoke `/compact Preserve task
   identifiers and immediate next action`, then read the native task list and
   assert both identifiers remain.
3. Repeat manual `/compact` with no custom focus and assert the hooks run and
   authorization bindings are empty.
4. Start a fresh process with
   `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=5`, generate bounded repetitive synthetic
   output until one automatic PreCompact/PostCompact pair occurs, and assert
   the task list survives. Use a maximum provider-token and 10-minute wall-clock
   budget.
5. Establish a synthetic literal-credential approval against the existing
   loopback fixture, compact, and prove the next matching call returns native
   `ask`, not `allow`. Never retain the credential literal.
6. Exercise `/resume` and `/rewind` on the generated session and record which
   task/context/authorization facts remain; exercise `/clear` only in a separate
   disposable session.
7. Load one skill at a time, invoke one subagent at a time, then connect a
   disposable no-secret MCP fixture. Record before/after percentages and tool
   counts only.
8. Detect actual tool search on the configured DeepSeek route. If unavailable,
   record `TOOL_SEARCH_UNAVAILABLE_GATEWAY`; do not force a `tool_reference`
   request or label the opposite fixture as live.

- [ ] **Step 6: Test correct and misreported windows**

On the real DeepSeek route, assert the scenario completes without
`CLAUDE_CODE_AUTO_COMPACT_WINDOW`. Then start a disposable loopback mock gateway
that reports a deliberately divergent window. Only after the parser records
`WINDOW_REPORTING_DIVERGENCE`, set a process-scoped absolute override for the
mock scenario, rerun, and record `ABSOLUTE_OVERRIDE_EVIDENCE_GATED`.

The mock records only method, path, status, and numeric window fields; it never
records headers or bodies.

- [ ] **Step 7: Normalize and delete content-bearing captures**

Run Task 6 normalization, write only the allowlisted evidence JSON, scan it for
forbidden keys and synthetic prompt/secret markers, then delete JSONL, PTY,
session-copy, and mock request files. `--keep-artifacts` may retain them only
inside the generated temporary directory and must print the directory plus a
warning that it contains model content; it never copies them into the repo.

- [ ] **Step 8: Run deterministic GREEN and document live prerequisites**

```powershell
python tests/test-live-context-continuity-safety.py
& 'C:\Program Files\Git\bin\bash.exe' -lc 'export PATH=/usr/bin:/mingw64/bin:$PATH; bash -n tests/live-context-continuity-smoke.sh; bash tests/live-context-continuity-smoke.sh --self-test'
```

Update `tests/validation-notes.md` with the exact acknowledgment, exit meanings,
isolation, numeric-retention schema, automatic-test threshold exception, real
DeepSeek requirement, and absolute-window diagnostic rule.

- [ ] **Step 9: Commit the live harness**

```powershell
git add tests/live-context-continuity-smoke.sh `
  tests/test-live-context-continuity-safety.py tests/validation-notes.md `
  tests/validate-package.sh .gitignore
git commit -m "test: add live context compaction validation"
```

---

### Task 8: Update architecture, release metadata, and user documentation

**Files:**
- Modify: `docs/architecture/ADR-005-context-continuity-and-preventive-compaction.md`
- Modify: `tests/test-architecture-docs.py`
- Modify: `README.md`
- Modify: `docs.md`
- Modify: `CHANGELOG.md`
- Modify: `nori.json`
- Modify: `.nori-version`
- Modify: `tests/validation-notes.md`

**Interfaces:**
- Produces package version `0.12.0` consistently in root metadata and docs.
- ADR-005 changes from design obligation language to exact implemented
  enforcement points and current validation evidence.
- User docs expose check/apply/status-line/rollback commands and explain that
  settings are local and operator-owned.

- [ ] **Step 1: Write release-document regressions first**

Extend `tests/test-architecture-docs.py` so ADR-005 must contain:

```python
REQUIRED_ADR_005 = (
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE",
    "72",
    "PreCompact",
    "PostCompact",
    "credential reuse",
    "numeric-only",
    "DeepSeek",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW",
    "Validation evidence",
)
```

Extend schema/content fixtures so version disagreement, missing continuity
commands, or claims that an absolute override is default fail.

- [ ] **Step 2: Run documentation tests and verify RED**

```powershell
python tests/test-architecture-docs.py
python tests/test-schema-validation.py
python tests/validate-content.py
```

Expected: FAIL on version `0.11.1` and missing implemented user guidance.

- [ ] **Step 3: Update release metadata to 0.12.0**

Set root `nori.json` and `.nori-version` to `0.12.0`. Update the manifest
description to summarize continuity, preventive percentage compaction,
non-blocking hooks, and content-free evidence without embedding runtime
versions.

- [ ] **Step 4: Update README, docs, changelog, and ADR**

Document:

- local `--check`, `--apply`, `--status-line`, and `--remove-owned` commands;
- 72 default and preserved 70-75 operator range;
- no normal absolute-window override;
- native task list and Compact Instructions;
- non-blocking, content-free hooks and fresh authorization after compaction;
- status-line opt-in conflict behavior;
- skills/subagents/MCP/tool-search numeric measurements;
- deterministic, installed, and live DeepSeek validation boundaries;
- P0-04B exclusion.

Add ADR-005 `Implemented architecture`, `Enforcement points`, `Validation
evidence`, `Consequences and limitations`, and `Forward compatibility`
sections using actual test counts and observed live identifiers only after the
real run. If the live run has not happened, write `Live evidence pending` and
do not claim acceptance evidence.

- [ ] **Step 5: Run documentation GREEN and commit**

```powershell
python tests/test-architecture-docs.py
python tests/test-schema-validation.py
python tests/validate-content.py
python tests/validate-schema.py
git diff --check
git add docs/architecture/ADR-005-context-continuity-and-preventive-compaction.md `
  README.md docs.md CHANGELOG.md nori.json .nori-version `
  tests/test-architecture-docs.py tests/validation-notes.md
git commit -m "docs: release context continuity controls"
```

---

### Task 9: Execute real validation, independent review, and PR gates

**Files:**
- Modify only after a RED regression demonstrates a defect: files owned by Tasks 1-8.
- Update after merge only, external and unversioned: `C:\projects\senior-infra-ops-analyst\TODO-AI-FIRST.md`.

**Interfaces:**
- Consumes all prior task outputs.
- Produces fresh static, installed, live DeepSeek, independent-review, CI, and Security evidence.
- Produces a pushed branch and PR; merge requires explicit operator instruction.

- [ ] **Step 1: Run the complete package gate**

```powershell
& 'C:\Program Files\Git\bin\bash.exe' -lc 'export PATH=/usr/bin:/mingw64/bin:$PATH; cd "$PWD"; bash tests/validate-package.sh'
```

Expected: command-guard tests and mutations, continuity suites, Python suites,
shell self-tests, schema, content, installed-artifact fixtures, and workflow
validation all pass.

- [ ] **Step 2: Run a fresh isolated Nori installation**

In generated `HOME` and `CLAUDE_CONFIG_DIR`, install the worktree through the
currently discovered Nori, verify 12 subagents, 25 project skills, 20 slash
commands, all compact hooks, byte-equal scripts, unrelated settings
preservation, repeat switch, and owned-only rollback. Record observed versions
as evidence, not requirements.

- [ ] **Step 3: Run the authorized real DeepSeek validation**

With the existing operator-approved normal-provider exception and temporary
acknowledgment variable:

```bash
P0_04A_LIVE_NORMAL_CREDENTIALS_ACK=I_ACCEPT_PROVIDER_CREDENTIAL_EGRESS_RISK \
  bash tests/live-context-continuity-smoke.sh --run-live
```

Expected: supported scenarios pass, unsupported tool-search capability is
reported with its exact reason code, production threshold remains 72, real
route uses no absolute override, and retained evidence passes the forbidden-
content scan.

- [ ] **Step 4: Apply TDD to every live defect**

For each failure, reduce the observation to a deterministic content-free
fixture, run it RED, implement the smallest correction, run it GREEN, rerun the
affected live scenario, then rerun the complete package gate. Do not weaken a
safety or privacy invariant to accept provider behavior.

- [ ] **Step 5: Request independent review**

Review `332088f..HEAD` against the approved design and this plan. Require explicit
findings for:

- settings precedence, conflict, rollback, symlink, and crash consistency;
- hook non-blocking semantics, shell fallback, and prohibited retention;
- authorization invalidation and concurrency;
- native task continuity and status-line null states;
- context measurement honesty and tool-search capability branching;
- Nori operator-preference preservation;
- live provider isolation and evidence claims;
- version, README, changelog, ADR, and P0-04B scope.

Fix every Critical or Important finding with a RED regression first. Repeat
review until no Critical or Important finding remains.

- [ ] **Step 6: Re-run final local verification**

```powershell
& 'C:\Program Files\Git\bin\bash.exe' -lc 'export PATH=/usr/bin:/mingw64/bin:$PATH; cd "$PWD"; bash tests/validate-package.sh'
git diff --check
git status --short --branch
git log --oneline 332088f..HEAD
```

Expected: complete gate exits `0`, no whitespace errors, clean worktree, and
only P0-04A commits after the main baseline.

- [ ] **Step 7: Push and create the PR without merging**

Push `agent/p0-04a-context-continuity`, create a ready-for-review PR containing
the design decision, test evidence, live DeepSeek capability results, privacy
invariants, rollback, and residual risks. Do not include a memory citation or
provider credential detail in the PR body.

- [ ] **Step 8: Wait for CI and Security**

Require all ordinary CI and security checks to pass on the reviewed head SHA.
If a check fails, inspect logs, add a deterministic RED regression, fix the
cause, rerun local gates, push, repeat independent review for affected scope,
and wait for the new head checks.

- [ ] **Step 9: Merge only on explicit operator instruction**

Before merge, verify the PR head SHA equals the independently reviewed and
passing SHA. Use the repository's established merge method only after the
operator explicitly requests merge.

- [ ] **Step 10: Close the definitive external TODO only after merge**

After verifying the merge commit is present in `main`, mark P0-04A complete in
`C:\projects\senior-infra-ops-analyst\TODO-AI-FIRST.md` and record package
version, branch, PR, merge SHA, deterministic counts, installed Nori result,
live DeepSeek observations, tool-search/window capability results, independent
review conclusion, CI/Security status, and ADR-005 path. Do not mark P0-04B.
