# P0-04A Status-Line Threshold Warning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a stateless status-line suggestion for manual `/compact` only when native `context_window.used_percentage` is strictly greater than the effective 70–75 percent auto-compaction threshold, without changing native automatic compaction.

**Architecture:** Extend the existing dependency-free status-line renderer with one pure threshold parser and one exported suggestion constant. The renderer keeps its current first line, conditionally appends the exact approved second line, and receives the child-process environment explicitly so deterministic tests do not mutate global state. Installation, hooks, automatic-compaction configuration, and absolute-window diagnostics remain unchanged.

**Tech Stack:** Node.js ES modules, built-in `node:test`, built-in streams and child processes, Markdown architecture/release documentation, existing Bash/Python package gates.

## Global Constraints

- Native automatic compaction remains enabled and remains the primary path.
- The warning is visual and advisory; it must never submit `/compact` or change conversation state.
- Display the exact approved suggestion only for valid native `context_window.used_percentage > effective threshold`; equality must not warn.
- Accept `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` only as an ASCII integer from `70` through `75`; every other value falls back to `72`.
- The `remaining_percentage` fallback may render the first line but must never trigger the warning.
- Preserve the 64 KiB input bound, zero exit status, neutral `ctx --` fallback, and absence of files, network calls, notifications, transcript content, and deduplication state.
- Keep status-line installation opt-in and preserve inherited operator or Nori status lines.
- Do not pin Claude Code, Nori, DeepSeek, provider, runtime, model, or context-window versions.
- Keep package version `0.11.0`; this is an extension of the still-unreleased P0-04A change in PR #32.

---

### Task 1: Pure Threshold and Rendering Contract

**Files:**
- Modify: `tests/context-continuity/statusline.test.mjs`
- Modify: `skills/context-continuity/scripts/context-statusline.mjs`

**Interfaces:**
- Consumes: status JSON shaped as `{ context_window?: { used_percentage?: number, remaining_percentage?: number } }` and an environment-shaped object with optional `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`.
- Produces: `DEFAULT_THRESHOLD: 72`, `COMPACT_SUGGESTION: string`, `effectiveThreshold(environment: object): number`, and `renderStatusLine(value: unknown, environment?: object): string`.

- [ ] **Step 1: Add failing unit tests for exact threshold parsing**

Add these imports and cases to `tests/context-continuity/statusline.test.mjs`:

```js
import {
  COMPACT_SUGGESTION,
  DEFAULT_THRESHOLD,
  effectiveThreshold,
  main,
  renderStatusLine,
} from '../../skills/context-continuity/scripts/context-statusline.mjs';

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
```

- [ ] **Step 2: Run the focused test and verify the threshold API is absent**

Run:

```bash
node --test tests/context-continuity/statusline.test.mjs
```

Expected: FAIL because `COMPACT_SUGGESTION`, `DEFAULT_THRESHOLD`, or `effectiveThreshold` is not exported.

- [ ] **Step 3: Implement the minimal exact threshold parser**

Add before `renderStatusLine` in `skills/context-continuity/scripts/context-statusline.mjs`:

```js
export const DEFAULT_THRESHOLD = 72;
export const COMPACT_SUGGESTION = 'Suggested: /compact Preserve objective, decisions, evidence locations, operational state, blockers, authorizations requiring revalidation, and immediate next action.';

export function effectiveThreshold(environment = {}) {
  const configured = environment?.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE;
  return typeof configured === 'string' && /^(?:70|71|72|73|74|75)$/.test(configured)
    ? Number(configured)
    : DEFAULT_THRESHOLD;
}
```

- [ ] **Step 4: Add failing unit tests for strict unrounded comparison**

Add these tests:

```js
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
```

- [ ] **Step 5: Run the focused test and verify the renderer still returns one line**

Run:

```bash
node --test tests/context-continuity/statusline.test.mjs
```

Expected: FAIL because `renderStatusLine` does not yet use the environment or append the suggestion.

- [ ] **Step 6: Implement the minimal conditional second line**

Replace the renderer with:

```js
export function renderStatusLine(value, environment = {}) {
  const context = value && typeof value === 'object' && !Array.isArray(value)
    ? value.context_window
    : null;
  const used = context?.used_percentage;
  const remaining = context?.remaining_percentage;
  const percent = Number.isFinite(used)
    ? used
    : Number.isFinite(remaining)
      ? 100 - remaining
      : null;
  const firstLine = percent !== null && percent >= 0 && percent <= 100
    ? `ctx ${Math.round(percent)}%`
    : 'ctx --';
  const shouldSuggest = Number.isFinite(used)
    && used >= 0
    && used <= 100
    && used > effectiveThreshold(environment);
  return shouldSuggest ? `${firstLine}\n${COMPACT_SUGGESTION}` : firstLine;
}
```

- [ ] **Step 7: Run the focused suite and verify pure rendering is green**

Run:

```bash
node --test tests/context-continuity/statusline.test.mjs
```

Expected: PASS for legacy percentage/neutral behavior and all new threshold cases.

- [ ] **Step 8: Commit the pure renderer contract**

```bash
git add tests/context-continuity/statusline.test.mjs skills/context-continuity/scripts/context-statusline.mjs
git commit -m "feat(context): suggest compact above threshold"
```

### Task 2: Executable Environment and Non-Blocking Boundaries

**Files:**
- Modify: `tests/context-continuity/statusline.test.mjs`
- Modify: `skills/context-continuity/scripts/context-statusline.mjs`

**Interfaces:**
- Consumes: the pure interfaces from Task 1 and `main({ input, output, environment })`, where `input` is an async iterable, `output.write(string)` emits the result, and `environment` defaults to `process.env`.
- Produces: an executable that emits exactly one or two newline-terminated display lines, emits no stderr, creates no artifact, and returns exit code zero for valid, malformed, or oversized input.

- [ ] **Step 1: Add a failing injected-environment test for `main`**

Add `Readable` and `Writable` imports from `node:stream`, then add:

```js
test('status line main uses its child environment for the effective threshold', async () => {
  let output = '';
  const code = await main({
    input: Readable.from([JSON.stringify({ context_window: { used_percentage: 71 } })]),
    output: new Writable({
      write(chunk, _encoding, callback) {
        output += chunk.toString();
        callback();
      },
    }),
    environment: { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '70' },
  });
  assert.equal(code, 0);
  assert.equal(output, `ctx 71%\n${COMPACT_SUGGESTION}\n`);
});
```

- [ ] **Step 2: Run the focused test and verify the injected threshold is ignored**

Run:

```bash
node --test tests/context-continuity/statusline.test.mjs
```

Expected: FAIL because `main` does not accept or pass `environment`.

- [ ] **Step 3: Thread the child environment through `main`**

Change the signature and renderer call to:

```js
export async function main({
  input = process.stdin,
  output = process.stdout,
  environment = process.env,
} = {}) {
  let rendered = 'ctx --';
  try {
    rendered = renderStatusLine(JSON.parse(await readBounded(input)), environment);
  } catch {
    rendered = 'ctx --';
  }
  output.write(`${rendered}\n`);
  return 0;
}
```

- [ ] **Step 4: Strengthen the real entrypoint artifact test**

Extend the existing `spawnSync` options with a deterministic environment and assert exact two-line output:

```js
const result = spawnSync(process.execPath, [entrypoint], {
  input: JSON.stringify({
    context_window: { used_percentage: 71 },
    model: { display_name: 'SYNTH_SECRET_ignored' },
  }),
  encoding: 'utf8',
  cwd: directory,
  env: {
    ...process.env,
    CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '70',
  },
});
assert.equal(result.status, 0, result.stderr);
assert.equal(result.stdout, `ctx 71%\n${COMPACT_SUGGESTION}\n`);
assert.equal(result.stderr, '');
assert.deepEqual(await readdir(directory), []);
```

- [ ] **Step 5: Retain malformed and oversized neutral behavior with a hostile environment**

Pass `environment: { CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '70' }` to each existing malformed/oversized `main` invocation and retain the exact assertion `ctx --\n`. This proves invalid JSON cannot create the advisory line.

- [ ] **Step 6: Run the focused suite and verify executable boundaries**

Run:

```bash
node --test tests/context-continuity/statusline.test.mjs
```

Expected: PASS, no stderr, and the temporary directory remains empty.

- [ ] **Step 7: Commit the executable wiring**

```bash
git add tests/context-continuity/statusline.test.mjs skills/context-continuity/scripts/context-statusline.mjs
git commit -m "test(context): verify status warning boundaries"
```

### Task 3: Architecture and Operator Documentation

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture/ADR-005-context-continuity-and-preventive-compaction.md`
- Modify: `docs/validation/p0-04a-context-continuity-validation-notes.md`
- Test: `tests/test-architecture-docs.py`
- Test: `tests/validate-content.py`

**Interfaces:**
- Consumes: the exact renderer behavior from Tasks 1 and 2.
- Produces: versioned operator guidance that distinguishes the native automatic path from the advisory manual fallback and preserves the honest BLOCKED status of the real ordered automatic `PreCompact(auto) -> PostCompact(auto)` acceptance gate.

- [ ] **Step 1: Document the operator-visible behavior in README**

Near the existing status-line setup text, add:

```markdown
When this package owns the opt-in status line, it keeps the normal `ctx N%`
line. If native `context_window.used_percentage` is strictly greater than the
effective `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` threshold, it adds a second line
suggesting the continuity-preserving `/compact` command. This is an advisory
fallback only: native automatic compaction stays enabled, and the package
never submits the command. An inherited operator or Nori status line remains
untouched and therefore does not receive this package-owned warning.
```

- [ ] **Step 2: Record the decision and invariants in ADR-005**

Add a decision subsection that states all of the following exact facts:

```markdown
The package-owned status line reads the same child environment configured for
native auto-compaction. Only ASCII integer thresholds from 70 through 75 are
accepted; missing or invalid values fall back to 72. It compares the unrounded
native `used_percentage`, warns only when usage is strictly greater, and does
not infer the warning from `remaining_percentage`. The conditional second line
is a deliberate exception to the compact one-line presentation. It is
stateless, performs no command submission, and does not disable or replace the
native automatic path.
```

- [ ] **Step 3: Update release and validation notes without overstating acceptance**

Add to the existing `0.11.0` CHANGELOG entry that the opt-in status line now
shows the exact operator suggestion above the effective threshold while native
auto-compaction remains enabled. In the validation notes, record deterministic
coverage of equality, fractional comparison, thresholds 70–75, invalid-value
fallback, remaining-only input, executable output, malformed input, and no
artifacts. Keep the real automatic compaction result BLOCKED/inconclusive until
the required live ordered pair is observed; do not treat the warning as proof
that auto-compaction fired or failed.

- [ ] **Step 4: Run documentation policy tests**

Run:

```bash
python tests/test-architecture-docs.py
python tests/validate-content.py
```

Expected: both commands exit zero and retain the indexed ADR, unpinned runtime policy, and approved terminology.

- [ ] **Step 5: Commit the documentation update**

```bash
git add README.md CHANGELOG.md docs/architecture/ADR-005-context-continuity-and-preventive-compaction.md docs/validation/p0-04a-context-continuity-validation-notes.md
git commit -m "docs(context): explain threshold warning"
```

### Task 4: Full Validation, Independent Review, and PR Update

**Files:**
- Verify: all files changed since `origin/agent/p0-04a-context-continuity`
- Update only if evidence requires correction: `docs/validation/p0-04a-context-continuity-validation-notes.md`

**Interfaces:**
- Consumes: committed implementation and documentation from Tasks 1–3.
- Produces: deterministic local evidence, an independent review verdict, a pushed PR #32 head, and green GitHub CI/Security checks; it does not merge the PR or mark the external TODO complete.

- [ ] **Step 1: Run focused and complete deterministic gates**

Run:

```bash
node --test tests/context-continuity/statusline.test.mjs
bash tests/validate-package.sh
git diff --check origin/agent/p0-04a-context-continuity...HEAD
```

Expected: every focused test and package gate passes, mutation score remains complete, and `git diff --check` prints nothing.

- [ ] **Step 2: Inspect the final diff for scope and privacy**

Run:

```bash
git status --short
git diff --stat origin/agent/p0-04a-context-continuity...HEAD
git diff origin/agent/p0-04a-context-continuity...HEAD -- skills/context-continuity/scripts/context-statusline.mjs tests/context-continuity/statusline.test.mjs README.md CHANGELOG.md docs/architecture/ADR-005-context-continuity-and-preventive-compaction.md docs/validation/p0-04a-context-continuity-validation-notes.md
```

Expected: no generated evidence, credentials, transcript data, persisted warning state, automatic `/compact` submission, auto-compaction disablement, unrelated changes, or new version pins.

- [ ] **Step 3: Request independent implementation review**

Provide the approved design, this plan, final diff, and test output to the independent reviewer. Require an explicit verdict and remediation of every Critical or Important finding before push. Minor wording findings may be fixed directly and revalidated.

- [ ] **Step 4: Re-run verification after review corrections**

Run again:

```bash
node --test tests/context-continuity/statusline.test.mjs
bash tests/validate-package.sh
git diff --check origin/agent/p0-04a-context-continuity...HEAD
```

Expected: all commands exit zero after the exact reviewed head is finalized.

- [ ] **Step 5: Push the existing branch and verify PR #32 checks**

```bash
git push origin agent/p0-04a-context-continuity
gh pr checks 32 --watch
```

Expected: the pushed head matches local `HEAD`; every required CI/Security check is green. Leave PR #32 as draft unless the operator separately approves readiness, do not merge it, and leave the definitive unversioned TODO incomplete until the real acceptance gate, CI/Security, review, and merge in `main` are all satisfied.

