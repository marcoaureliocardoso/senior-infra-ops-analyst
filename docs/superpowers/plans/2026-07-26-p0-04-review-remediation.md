# P0-04 Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every blocking finding in the independent review of PR #25
while retaining the eight executor subagents as guarded operational executors.

**Architecture:** Native Claude Code hooks remain the enforcement boundary. A
fail-closed Bash launcher invokes dependency-free Node.js modules that fully
parse the outer command, apply executable-specific schemas, authorize literal
credential reuse only from successful native approval evidence, and record
only non-secret structural audit data. One executable fixture ledger drives
source and installed validation, while the opt-in live smoke retains normal
provider credentials under the explicitly accepted residual-risk exception.

**Tech Stack:** Claude Code Markdown/YAML hooks, Nori-installed artifacts,
Bash, Node.js standard library and `node:test`, Python 3 standard library,
PowerShell differential probes, Bubblewrap live isolation, GitHub Actions.

## Global Constraints

- Do not pin Claude Code, Nori, Node.js, or a model identifier or version.
- Keep `model: inherit`, the eight executor roles, and the four analytical
  roles unchanged.
- Use native `PreToolUse` and `PostToolUse`; do not add a daemon, model proxy,
  credential vault, or separately managed runtime.
- A missing launcher dependency, missing installed artifact, timeout, crash,
  output pollution, malformed response, or required-audit failure must exit
  `2` before the proposed tool call can execute.
- Parse and consume the complete outer command before interpreting a nested
  PowerShell payload or any future wrapper.
- Unknown syntax, executable, option, assignment, stage, sink, or data-flow
  edge must not produce `allow`.
- Keep `DESTRUCTIVE` and `EXTERNAL_SIDE_EFFECT` at `ask` in every permission
  mode.
- A first model-visible literal credential use returns `ask` even in
  `bypassPermissions`; only matching successful `PostToolUse` evidence can
  activate session reuse.
- Never store, hash, compare, fingerprint, log, or serialize a credential
  value or a raw credential-bearing command.
- Keep the live smoke opt-in. It may import normal provider credentials only
  under the approved acknowledgement and residual-risk controls.
- Add each reproduced review bypass as a failing executable fixture before
  changing production behavior.
- Keep the branch unmerged; update PR #25 only after all local and installed
  gates pass and a new independent review is recorded.

---

## File map

### Hook lifecycle

- Create
  `skills/command-driven-operations/scripts/command-guard-launcher.sh`: resolve
  and run the validator with an internal deadline and blocking exit behavior.
- Create
  `skills/command-driven-operations/scripts/record-command-approval.mjs`:
  process matching `PostToolUse` events without evaluating tool output.
- Create
  `skills/command-driven-operations/scripts/command-guard/binding-store.mjs`:
  bounded non-secret pending and active session state.
- Modify `subagents/*.md`: replace direct Node invocation on the eight
  executors and add the matching `PostToolUse` hook.
- Modify `tests/command_guard_install_policy.py`: canonical hook lifecycle and
  security-critical installed-file inventory.

### Parsing and policy

- Modify `command-guard/contract.mjs`: strict execution input with bounded
  observational top-level compatibility and tool-use identity.
- Modify `command-guard/bash-lexer.mjs` and `command-guard/powershell-lexer.mjs`:
  complete wrapper consumption and assignment tokens.
- Modify `command-guard/composition.mjs`: retain every stage, edge, operator,
  redirect, source, and sink.
- Create `command-guard/argv-schema.mjs`: shared exact option-arity and
  positional parsing with an explicit assignment allowlist.
- Create `command-guard/http-policy.mjs`: curl and PowerShell web-client
  effective method, body, upload, redirect, authentication, and sink parsing.
- Create `command-guard/sql-policy.mjs`: narrow single-statement relational
  read parser.
- Create `command-guard/git-policy.mjs`: Git push refspec and GitHub external
  side-effect parsing.
- Modify `command-guard/catalogue.mjs`: delegate to the focused schemas and
  replace generic read-family classification.
- Modify `command-guard/policy.mjs`: aggregate all stage findings and apply
  explicit destructive and external-effect precedence.

### Credentials and audit

- Modify `command-guard/credential-flow.mjs`: exact decryptor pipe topology,
  current binding derivation, and provider-control-plane denial.
- Modify `command-guard/redaction.mjs`: parser-aware credential positions and
  no raw-command fingerprint.
- Modify `command-guard/audit.mjs`: non-secret structural action identity and
  bounded per-stage findings.
- Modify `command-guard/response.mjs`: bounded per-stage operator explanation.

### Executable evidence

- Create `tests/command-guard/review-regression-fixtures.mjs`: stable review
  finding fixtures with expected decisions and reason codes.
- Create `tests/command-guard/executable-fixtures.test.mjs`: execute every
  declared fixture, record it after assertions, and close the ledger in one
  test process.
- Create `tests/command-guard/fixture-ledger.mjs`: record and validate IDs that
  actually executed.
- Modify `tests/command-guard/coverage-manifest.mjs` and
  `tests/command-guard/coverage.test.mjs`: bind finite inventory entries to
  executed fixture IDs.
- Create `tests/command-guard/launcher.test.mjs`,
  `tests/command-guard/binding-store.test.mjs`, and
  `tests/command-guard/installed-corpus.test.mjs`.
- Modify `tests/run-command-guard-tests.mjs`: run the executable ledger and
  installed corpus.
- Modify `tests/test-command-guard-install-policy.py`: compare every installed
  security-critical artifact with source.
- Modify `tests/live-command-guard-smoke.sh` and
  `tests/test-live-command-guard-safety.py`: accepted normal-credential
  exception, acknowledgement, and compensating controls.

### Documentation and release

- Modify `docs/architecture/ADR-004-native-command-guard.md` and
  `docs/reviews/2026-07-26-pr-25-independent-review.md`: implemented
  architecture and finding disposition.
- Modify `README.md`, `docs.md`, `CHANGELOG.md`, and
  `tests/validation-notes.md`: operator behavior, verification evidence, and
  residual live-smoke risk.
- Verify `nori.json` and `.nori-version`: retain the current unreleased version
  when consistent; change both only if the release policy requires a new
  version after PR #25 has already been published.

## Shared data contracts

The implementation is JavaScript, but these object shapes are fixed across
tasks:

```js
// GuardFixture
{
  id: 'RV02-PS-OUTER-SEQUENCE',
  command: 'pwsh -NoProfile -Command "Get-Service" ; uname -a',
  permissionMode: 'bypassPermissions',
  expectedDecision: 'deny',
  expectedReasonCode: 'DENY_UNCONSUMED_WRAPPER',
  covers: [{ category: 'edgeCases', item: 'WRAPPER_TRAILING_STAGE', kind: 'negative' }],
}

// AssignmentSchema
{ allowedNames: new Set(['AWS_PROFILE']), forbiddenPatterns: [/^LD_/u] }

// Composition
{ shell: 'bash', stages: [], edges: [], redirects: [] }

// FamilyResult
{
  policyId: 'HTTP', risk: 'LOW_RISK_CHANGE', target: '/', environment: 'https://example.invalid',
  modifiers: [], sinks: [], sources: [], credentialConsumer: true,
}

// StageFinding
{ stage: 1, reasonCode: 'DENY_UNKNOWN_COMMAND', risk: 'SAFE_READ_ONLY', modifiers: [] }

// PolicyResult
{
  decision: 'deny', reasonCode: 'DENY_UNKNOWN_COMMAND', risk: 'SAFE_READ_ONLY',
  modifiers: [], findings: [], policyId: null, target: null, environment: null,
}
```

`PowerShellComposition` has the same `Composition` shape with `shell` set to
`powershell`.

---

### Task 1: Replace synthetic coverage labels with an executable fixture ledger

**Files:**
- Create: `tests/command-guard/review-regression-fixtures.mjs`
- Create: `tests/command-guard/executable-fixtures.test.mjs`
- Create: `tests/command-guard/fixture-ledger.mjs`
- Modify: `tests/command-guard/coverage-manifest.mjs`
- Modify: `tests/command-guard/coverage.test.mjs`
- Modify: `tests/command-guard/helpers.mjs`
- Modify: `tests/run-command-guard-tests.mjs`

**Interfaces:**
- Produces: `REVIEW_REGRESSION_FIXTURES: readonly GuardFixture[]`, where each
  fixture has `id`, `command`, `permissionMode`, `expectedDecision`, and
  `expectedReasonCode`.
- Produces: `createFixtureLedger(expectedIds: string[]) -> FixtureLedger`,
  whose `record(id)` and `assertComplete()` methods execute in the same test
  process.
- Guarantees: a declared fixture cannot satisfy coverage unless its assertion
  ran in the current process.

- [ ] **Step 1: Write the failing ledger tests**

Add these assertions to `coverage.test.mjs`:

```js
test('declared fixtures must be executed', () => {
  const ledger = createFixtureLedger(['RV02-PS-OUTER-SEQUENCE']);
  assert.throws(() => ledger.assertComplete(), /fixture-not-executed:RV02-PS-OUTER-SEQUENCE/u);
});

test('executed fixtures must be declared exactly once', () => {
  assert.throws(() => createFixtureLedger(['A', 'A']), /fixture-declared-twice:A/u);
  const ledger = createFixtureLedger([]);
  assert.throws(() => ledger.record('UNDECLARED'), /fixture-not-declared:UNDECLARED/u);
});
```

- [ ] **Step 2: Run the focused test and verify red**

Run:

```bash
node --test tests/command-guard/coverage.test.mjs
```

Expected: fail because `validateExecutedFixtures` does not exist.

- [ ] **Step 3: Implement the ledger and real fixtures**

Return ledger state scoped to the calling test process:

```js
export function createFixtureLedger(expectedIds) {
  const declared = new Set();
  for (const id of expectedIds) {
    if (declared.has(id)) throw new Error(`fixture-declared-twice:${id}`);
    declared.add(id);
  }
  const executed = new Set();
  return {
    record(id) {
      if (!declared.has(id)) throw new Error(`fixture-not-declared:${id}`);
      if (executed.has(id)) throw new Error(`fixture-executed-twice:${id}`);
      executed.add(id);
    },
    assertComplete() {
      for (const id of declared) if (!executed.has(id)) throw new Error(`fixture-not-executed:${id}`);
      return true;
    },
  };
}
```

Seed `REVIEW_REGRESSION_FIXTURES` with stable IDs for RV-02 through RV-17.
Each fixture must contain the exact reproduced command from the review record;
RV-01 and RV-13 use subprocess and installed-artifact fixture IDs rather than
command strings.

- [ ] **Step 4: Execute every fixture through the real policy assertion**

In `executable-fixtures.test.mjs`, create one ledger, loop over
`REVIEW_REGRESSION_FIXTURES`, call the existing
`analyzeCommand(parseHookEvent(...))`, assert the expected decision and reason
code, record the ID only after both assertions pass, then call
`ledger.assertComplete()` before the test returns.

- [ ] **Step 5: Remove `casesFor` fabricated labels**

Make the coverage manifest map each finite inventory item to explicit fixture
IDs from `GuardFixture.covers`. In the same executable-fixture test process,
`validateCoverageManifest` cross-checks the inventory, fixture IDs, coverage
kinds, and completed ledger before returning success.

- [ ] **Step 6: Run red regressions and commit the evidence layer**

Run:

```bash
node --test tests/command-guard/coverage.test.mjs \
  tests/command-guard/security-regressions.test.mjs
```

Expected: ledger tests pass and the newly executed review fixtures fail on the
known unsafe decisions. Commit only tests and the ledger infrastructure:

```bash
git add tests/command-guard tests/run-command-guard-tests.mjs
git commit -m "test: bind command guard coverage to executed fixtures"
```

---

### Task 2: Make the native hook lifecycle fail closed and prove installed equivalence

**Files:**
- Create: `skills/command-driven-operations/scripts/command-guard-launcher.sh`
- Create: `tests/command-guard/launcher.test.mjs`
- Create: `tests/command-guard/installed-corpus.test.mjs`
- Modify: `subagents/audit-evidence-collector.md`
- Modify: `subagents/cloud-platform-operator.md`
- Modify: `subagents/database-operator.md`
- Modify: `subagents/diagnostic-operator.md`
- Modify: `subagents/kubernetes-operator.md`
- Modify: `subagents/network-edge-operator.md`
- Modify: `subagents/observability-sre.md`
- Modify: `subagents/release-cicd-operator.md`
- Modify: `tests/command_guard_install_policy.py`
- Modify: `tests/test-command-guard-install-policy.py`
- Modify: `tests/test-installed-subagents.py`

**Interfaces:**
- Produces: launcher exit `0` with exactly one validator JSON object, or exit
  `2` with a bounded stderr message.
- Produces: `SECURITY_CRITICAL_ARTIFACTS: tuple[Path, ...]` in the Python
  installation policy.
- Consumes: the existing `validate-ops-command.mjs` stdin/stdout contract.

- [ ] **Step 1: Write launcher failure tests**

Cover missing Node.js, missing validator, validator exit `1`, validator exit
`2`, deadline, invalid JSON, two JSON objects, and stderr pollution. Assert
every failure returns `2` and never emits an `allow` object.

- [ ] **Step 2: Verify launcher tests are red**

Run:

```bash
node --test tests/command-guard/launcher.test.mjs
```

Expected: fail because the launcher does not exist.

- [ ] **Step 3: Implement the launcher**

Use `set -euo pipefail`, require exactly one mode argument equal to `pre`,
resolve `SCRIPT_DIR` from `BASH_SOURCE[0]`, validate the validator path under
that directory, resolve `node` and `timeout` with `command -v`, and run
`timeout --signal=TERM --kill-after=1s 5s "$NODE_BIN" "$VALIDATOR"`. Capture
stdout and stderr in owner-only temporary files, validate one JSON response
with the resolved Node.js binary, print it, and remove the exact temporary
directory in an `EXIT` trap. Every error path calls:

```bash
block_hook() {
  printf '%s\n' 'Command guard blocked execution because its launcher failed.' >&2
  exit 2
}
```

- [ ] **Step 4: Change the eight source hooks test-first**

Update canonical-policy tests to require:

```yaml
command: "{{skills_dir}}/command-driven-operations/scripts/command-guard-launcher.sh"
args:
  - pre
timeout: 7
```

The launcher deadline is five seconds and the native outer timeout is seven
seconds. Analytical agents remain hook-free.

- [ ] **Step 5: Prove installed artifact identity**

Define `SECURITY_CRITICAL_ARTIFACTS` for every shipped launcher, entrypoint,
and `command-guard/*.mjs` module. Compare each installed file byte-for-byte
after isolated Nori installation. The source-side installed-corpus runner then
imports the source fixture corpus and executes it against the installed policy
modules.

- [ ] **Step 6: Run source and installed hook gates**

Run:

```bash
node --test tests/command-guard/launcher.test.mjs \
  tests/command-guard/installed-corpus.test.mjs
python3 tests/test-command-guard-install-policy.py
python3 tests/test-installed-subagents.py
```

Expected: all pass.

- [ ] **Step 7: Commit the fail-closed lifecycle**

```bash
git add skills/command-driven-operations/scripts/command-guard-launcher.sh \
  subagents tests/command_guard_install_policy.py \
  tests/test-command-guard-install-policy.py tests/test-installed-subagents.py \
  tests/command-guard/launcher.test.mjs \
  tests/command-guard/installed-corpus.test.mjs
git commit -m "fix: fail closed across command guard launch paths"
```

---

### Task 3: Consume wrappers completely and restrict environment assignments

**Files:**
- Create: `skills/command-driven-operations/scripts/command-guard/argv-schema.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/policy.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/bash-lexer.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/powershell-lexer.mjs`
- Modify: `tests/command-guard/lexer.test.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`

**Interfaces:**
- Produces: `parseAssignments(argv: string[], schema: AssignmentSchema) ->
  { assignments: ReadonlyMap<string, string>, executableIndex: number }` or a
  stable denial error.
- Produces: `unwrapPowerShell(composition: Composition) ->
  PowerShellComposition` only after complete outer consumption.

- [ ] **Step 1: Add exact red regressions**

Add assertions for outer `;`, `&&`, redirect, newline, duplicate `-Command`,
trailing argument, abbreviated option, and case variants. Add assignment cases
for `PATH`, `LD_PRELOAD`, `DYLD_INSERT_LIBRARIES`, `BASH_ENV`, `ENV`,
`SHELLOPTS`, `GIT_EXTERNAL_DIFF`, `GIT_CONFIG_COUNT`, `PAGER`, `NODE_OPTIONS`,
an unknown variable, and the allowed `AWS_PROFILE` and
`OPS_CREDENTIAL_IDENTITY` schemas.

- [ ] **Step 2: Run the focused red tests**

```bash
node --test tests/command-guard/lexer.test.mjs \
  tests/command-guard/security-regressions.test.mjs
```

Expected: the reviewed PowerShell and control-variable fixtures fail.

- [ ] **Step 3: Replace argument slicing with complete wrapper consumption**

Delete the `lexCommand` behavior that returns only `argv[index + 1]`.
Tokenize the full outer command, require one foreground stage, reject outer
edges and redirects, parse exact wrapper option arity case-insensitively, and
require `-Command` to consume the final payload token.

- [ ] **Step 4: Replace generic assignment skipping**

Delete the generic `^[A-Za-z_][A-Za-z0-9_]*=` executable skip. Command-family
schemas pass their exact allowed assignment names to `parseAssignments`.
Unknown or control variables return `DENY_EXECUTION_CONTROL_ASSIGNMENT`.

- [ ] **Step 5: Verify and commit**

```bash
node --test tests/command-guard/lexer.test.mjs \
  tests/command-guard/security-regressions.test.mjs
git add skills/command-driven-operations/scripts/command-guard \
  tests/command-guard
git commit -m "fix: consume wrappers and environment prefixes completely"
```

---

### Task 4: Preserve compatibility only for observational event metadata

**Files:**
- Modify: `skills/command-driven-operations/scripts/command-guard/contract.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/limits.mjs`
- Modify: `tests/command-guard/contract.test.mjs`

**Interfaces:**
- Produces: normalized `toolUseId` and optional compatibility modifiers.
- Guarantees: unknown `tool_input` keys remain fatal; bounded unknown
  top-level scalar metadata cannot grant autonomous privileges.

- [ ] **Step 1: Write the compatibility matrix**

Assert an unknown bounded top-level string, boolean, and finite number are
accepted and ignored; nested objects, arrays, over-limit strings, duplicate
security keys, unknown `tool_input` fields, and unknown hook/tool names are
rejected. Assert effort level `ultra` is observationally accepted and an
unknown permission mode follows conservative normal-mode policy.

- [ ] **Step 2: Verify red**

```bash
node --test tests/command-guard/contract.test.mjs
```

Expected: bounded top-level metadata and future effort cases fail.

- [ ] **Step 3: Separate security and observational keys**

Keep exact validation for known fields. Permit only bounded scalar unknown
top-level values, record their key names without values in a compatibility
modifier, and preserve strict duplicate-key scanning for all known security
keys and `tool_input`.

- [ ] **Step 4: Verify and commit**

```bash
node --test tests/command-guard/contract.test.mjs
git add skills/command-driven-operations/scripts/command-guard/contract.mjs \
  skills/command-driven-operations/scripts/command-guard/limits.mjs \
  tests/command-guard/contract.test.mjs
git commit -m "fix: tolerate bounded observational hook metadata"
```

---

### Task 5: Parse HTTP effects and sinks by client

**Files:**
- Create: `skills/command-driven-operations/scripts/command-guard/http-policy.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/credential-flow.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/policy.test.mjs`

**Interfaces:**
- Produces: `parseHttpOperation(argv: string[]) -> FamilyResult | null`.
- Result includes `effectiveMethod`, `hasBody`, `hasUpload`, `redirectMode`,
  `localSinks`, `origin`, and `credentialConsumer`.

- [ ] **Step 1: Add curl and PowerShell web-client regressions**

Cover curl `-d`, `--data-*`, `--json`, `-F`, `--form-string`, `-T`, stdin and
file uploads, `-o`, `--output`, `-O`, `-D`, `-c`, `--etag-save`, `--trace`,
`--next`, `-L`, explicit method conflicts, attached short options, and option
values beginning with `-`. Cover PowerShell `-Body`, `-Form`, `-InFile`,
`-Method`, `-OutFile`, redirect controls, case variants, and duplicate options.

- [ ] **Step 2: Verify red decisions**

```bash
node --test tests/command-guard/security-regressions.test.mjs \
  tests/command-guard/policy.test.mjs
```

Expected: implicit POST, upload, and local-sink cases are misclassified.

- [ ] **Step 3: Implement exact HTTP option tables**

Use explicit option descriptors with arity and effects. Infer POST from body or
form, PUT from upload unless an explicit method overrides it, and preserve the
most restrictive effect when options conflict. Any local sink with a literal
credential returns `DENY_SECRET_PERSISTENCE`; unauthenticated sinks are
classified as file writes and require the corresponding operation policy.

- [ ] **Step 4: Verify and commit**

```bash
node --test tests/command-guard/security-regressions.test.mjs \
  tests/command-guard/policy.test.mjs
git add skills/command-driven-operations/scripts/command-guard/http-policy.mjs \
  skills/command-driven-operations/scripts/command-guard/catalogue.mjs \
  skills/command-driven-operations/scripts/command-guard/credential-flow.mjs \
  tests/command-guard
git commit -m "fix: derive HTTP methods uploads and sinks"
```

---

### Task 6: Replace generic reads and SQL blacklists with narrow schemas

**Files:**
- Create: `skills/command-driven-operations/scripts/command-guard/sql-policy.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`
- Modify: `tests/command-guard/policy.test.mjs`

**Interfaces:**
- Produces: `parseRelationalStatement(query: string, dialect: string) ->
  { kind: 'bounded-read', rowLimit: number } | null`.
- Guarantees: every safe read family has an exact option and operand schema.

- [ ] **Step 1: Add sensitive and mutating read regressions**

Assert denial or approval-required classification for `ss -K`, journal vacuum
and rotate options, `ps auxeww`, Kubernetes secret/config output, cloud secret
stores, container environment inspect, privileged sudo reads, unbounded
PowerShell network probes, broad file/process/environment discovery, and each
supported command's unknown options.

- [ ] **Step 2: Add relational parser regressions**

Include bounded literal `SELECT`, `SHOW`, and non-analyzing `EXPLAIN` positive
cases. Include `SELECT pg_terminate_backend(123)`, `SELECT ... INTO`, file
functions, locks, procedural calls, comments hiding tokens, dollar quoting,
multi-statements, `EXPLAIN ANALYZE`, and missing or excessive row bounds as
negative cases.

- [ ] **Step 3: Verify red**

```bash
node --test tests/command-guard/security-regressions.test.mjs \
  tests/command-guard/policy.test.mjs
```

Expected: reviewed generic-read and side-effecting SQL fixtures fail.

- [ ] **Step 4: Implement focused parsers**

Remove `POSIX_READ` and broad cloud prefix inference. Define exact accepted
verbs and flags for each executable. The SQL parser accepts one statement,
balances literals and comments, permits only a narrow read token grammar, and
requires a literal row bound where result size can grow.

- [ ] **Step 5: Verify and commit**

```bash
node --test tests/command-guard/security-regressions.test.mjs \
  tests/command-guard/policy.test.mjs
git add skills/command-driven-operations/scripts/command-guard \
  tests/command-guard
git commit -m "fix: narrow operational reads and SQL authorization"
```

---

### Task 7: Classify destructive Git and external side effects exactly

**Files:**
- Create: `skills/command-driven-operations/scripts/command-guard/git-policy.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/policy.mjs`
- Modify: `tests/command-guard/security-regressions.test.mjs`

**Interfaces:**
- Produces: `parseGitOperation(argv: string[]) -> FamilyResult | null`.
- Adds modifier: `EXTERNAL_SIDE_EFFECT`.

- [ ] **Step 1: Add Git and GitHub red regressions**

Cover `git push --mirror`, `--prune`, `--force`, `--force-with-lease`, deletion
reference specifications such as `:main`, forced `+main`, wildcard mappings,
`--delete`, and conflicting flags. Cover `gh pr comment`, issue create/edit,
release create/delete, deployment mutation, and generic mutating `gh api`
requests.

- [ ] **Step 2: Verify red in normal and bypass modes**

```bash
node --test tests/command-guard/security-regressions.test.mjs
```

Expected: destructive pushes or external writes receive an autonomous allow or
the wrong risk/reason.

- [ ] **Step 3: Implement explicit Git schemas and precedence**

Parse option arity and every push reference specification. Set destructive
variants to `DESTRUCTIVE`. Set externally persisted GitHub operations to
`EXTERNAL_SIDE_EFFECT`. In `policy.mjs`, return `ask` for either condition in
every permission mode.

- [ ] **Step 4: Verify and commit**

```bash
node --test tests/command-guard/security-regressions.test.mjs \
  tests/command-guard/policy.test.mjs
git add skills/command-driven-operations/scripts/command-guard/git-policy.mjs \
  skills/command-driven-operations/scripts/command-guard/catalogue.mjs \
  skills/command-driven-operations/scripts/command-guard/policy.mjs \
  tests/command-guard
git commit -m "fix: require approval for destructive and external Git effects"
```

---

### Task 8: Enforce exact credential flow, parser-aware redaction, and complete stage reporting

**Files:**
- Modify: `skills/command-driven-operations/scripts/command-guard/credential-flow.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/redaction.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/composition.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/policy.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/audit.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/response.mjs`
- Modify: `tests/command-guard/credential-flow.test.mjs`
- Modify: `tests/command-guard/contract.test.mjs`
- Modify: `tests/command-guard/policy.test.mjs`

**Interfaces:**
- Produces: `structuralActionIdentity(result: PolicyResult) -> string` from
  canonical non-secret fields only.
- Produces: `findings: readonly StageFinding[]` on every policy result.

- [ ] **Step 1: Add direct-pipe topology regressions**

For both `gpg -d` and `age -d`, cover the one valid immediate `|` consumer and
reject `;`, newline, `&&`, `||`, `|&`, redirects, display filters, persistence,
background, third stages, and consumers not configured for direct stdin.

- [ ] **Step 2: Add redaction and action-identity regressions**

Cover Redis `-aVALUE`, Redis `-a VALUE`, MySQL `-pVALUE`, `X-API-Key`,
`PRIVATE-TOKEN`, query token/password/key parameters, URI user information,
cookies, PowerShell headers, and repeated or overlapping values. Assert two
different synthetic values yield the same structural action identity and that
neither value appears in response, stderr, audit, coverage output, or retained
artifacts.

- [ ] **Step 3: Add aggregate stage regressions**

Build two equal-risk stages and assert both stage numbers and reason codes are
present in `findings`, response, and audit. Assert the bounded maximum and the
one-over composition fail closed.

- [ ] **Step 4: Verify red**

```bash
node --test tests/command-guard/credential-flow.test.mjs \
  tests/command-guard/contract.test.mjs \
  tests/command-guard/policy.test.mjs
```

- [ ] **Step 5: Implement topology and structural identity**

Require `composition.edges.length === 1`, exact operator `|`, adjacent stages,
one decryptor, one direct consumer, and no redirects. Remove
`normalizeAndFingerprint` from audit identity. Canonicalize only family, verb,
target, environment, scope, operator kinds, sink kinds, risk, modifiers, and
reason codes.

- [ ] **Step 6: Implement parser-aware redaction and findings**

Credential schemas return sensitive argument spans during parsing. Merge and
redact spans before all serialization. Accumulate all findings, sort by stage
and reason code, cap at the declared bound, and aggregate decision by the most
restrictive modifier and risk.

- [ ] **Step 7: Verify and commit**

```bash
node --test tests/command-guard/credential-flow.test.mjs \
  tests/command-guard/contract.test.mjs \
  tests/command-guard/policy.test.mjs
git add skills/command-driven-operations/scripts/command-guard \
  tests/command-guard
git commit -m "fix: bind credential flows and remove secret-derived identity"
```

---

### Task 9: Activate literal reuse only after successful native approval

**Files:**
- Create: `skills/command-driven-operations/scripts/command-guard/binding-store.mjs`
- Create: `skills/command-driven-operations/scripts/record-command-approval.mjs`
- Create: `tests/command-guard/binding-store.test.mjs`
- Modify: `skills/command-driven-operations/scripts/validate-ops-command.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/contract.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/credential-flow.mjs`
- Modify: `skills/command-driven-operations/scripts/command-guard/policy.mjs`
- Modify: the eight executor files under `subagents/`
- Modify: `tests/command_guard_install_policy.py`

**Interfaces:**
- Produces: `writePendingBinding(binding, env): void`.
- Produces: `activatePendingBinding(postEvent, env): boolean`.
- Produces: `findActiveBinding(currentBinding, env): boolean`.
- Binding fields: `sessionId`, `toolUseId`, `domain`, `identity`, `transport`,
  `family`, `targetClass`, `expiresAt`, and `state`; no command or secret field.

- [ ] **Step 1: Write state-machine red tests**

Cover first literal in bypass returning `ask`; successful matching
`PostToolUse` activation; subsequent same session/domain/identity/transport
following operation policy; different session, mode, domain, identity,
transport, expired state, corrupt state, missing post event, failed tool event,
replayed tool-use ID, and opaque identity returning to `ask` or `deny` as the
policy requires.

- [ ] **Step 2: Write storage safety tests**

Assert owner-only directory and file modes on POSIX, atomic replacement, fixed
entry count, fixed byte bound, expiration cleanup, and no forbidden field names
or synthetic values in state. Force open, parse, rename, and permission errors
and assert they fail closed.

- [ ] **Step 3: Verify red**

```bash
node --test tests/command-guard/binding-store.test.mjs \
  tests/command-guard/credential-flow.test.mjs
```

- [ ] **Step 4: Implement pending and active state**

Use a project-local guard state root selected by the launcher, a per-session
bounded file name, mode `0700` directory, mode `0600` file, temporary-file plus
atomic rename, maximum entry count, and short expiration. Reject symlinks,
unexpected ownership where available, unexpected fields, and over-limit state.

- [ ] **Step 5: Add the successful `PostToolUse` hook**

The eight executors receive a `PostToolUse` matcher for `Bash` that invokes
`record-command-approval.mjs` through the same fail-closed launcher family.
The post entrypoint validates `session_id`, `tool_use_id`, `tool_name`,
`hook_event_name`, and matching pending state. It ignores tool output and exits
nonzero without activation on mismatch or failure.

- [ ] **Step 6: Enforce first-use and reuse decisions**

`PreToolUse` writes pending state before returning first-use `ask`. A matching
active binding can remove only the literal-first-use modifier in
`bypassPermissions`; all other current-command parsing, destructive,
external-effect, sink, and target rules still apply.

- [ ] **Step 7: Verify and commit**

```bash
node --test tests/command-guard/binding-store.test.mjs \
  tests/command-guard/credential-flow.test.mjs \
  tests/command-guard/entrypoint.test.mjs
python3 tests/test-command-guard-install-policy.py
git add skills/command-driven-operations/scripts subagents \
  tests/command-guard tests/command_guard_install_policy.py \
  tests/test-command-guard-install-policy.py
git commit -m "fix: bind literal reuse to successful native approval"
```

---

### Task 10: Preserve normal live credentials under explicit residual-risk controls

**Files:**
- Modify: `tests/live-command-guard-smoke.sh`
- Modify: `tests/test-live-command-guard-safety.py`
- Modify: `skills/command-driven-operations/scripts/command-guard/credential-flow.mjs`
- Modify: `tests/command-guard/credential-flow.test.mjs`

**Interfaces:**
- Adds required live acknowledgement:
  `P0_04_LIVE_NORMAL_CREDENTIALS_ACK=I_ACCEPT_PROVIDER_CREDENTIAL_EGRESS_RISK`.
- Adds reason: `DENY_PROVIDER_CONTROL_CREDENTIAL_ACCESS`.

- [ ] **Step 1: Write static and policy red tests**

Assert `--run-live` refuses missing or wrong acknowledgement, prints the
residual-risk warning before Claude starts, retains normal provider credential
import, never prints or hashes values, and keeps live mode opt-in. Assert Bash
commands referencing `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_API_KEY`, supported
provider control variables, `/proc/*/environ`, `ps e`, `env`, `printenv`, and
shell environment enumeration deny in every permission mode.

- [ ] **Step 2: Verify red**

```bash
python3 tests/test-live-command-guard-safety.py
node --test tests/command-guard/credential-flow.test.mjs
```

- [ ] **Step 3: Implement the accepted exception controls**

Require the exact acknowledgement before environment loading. Keep the
existing normal credential variable import. Print a fixed warning that
provider egress remains open and the controls do not eliminate compromised
process risk. Retain generated home, minimal environment, read-only runtime
mounts, isolated writable paths, and loopback or disposable targets.

- [ ] **Step 4: Add provider-control access denials**

Detect provider variable names before generic credential classification and
deny them. Deny general environment-discovery command forms in the catalogue.
Scan retained smoke output for synthetic markers and provider variable names,
without interpolating or reading provider values.

- [ ] **Step 5: Run static and self-test gates and commit**

```bash
python3 tests/test-live-command-guard-safety.py
bash tests/live-command-guard-smoke.sh --self-test
node --test tests/command-guard/credential-flow.test.mjs
git add tests/live-command-guard-smoke.sh \
  tests/test-live-command-guard-safety.py \
  skills/command-driven-operations/scripts/command-guard/credential-flow.mjs \
  tests/command-guard/credential-flow.test.mjs
git commit -m "test: constrain accepted live credential exposure"
```

---

### Task 11: Close documentation, package, installed, and live verification

**Files:**
- Modify: `docs/architecture/ADR-004-native-command-guard.md`
- Modify: `docs/reviews/2026-07-26-pr-25-independent-review.md`
- Modify: `README.md`
- Modify: `docs.md`
- Modify: `CHANGELOG.md`
- Modify: `tests/validation-notes.md`
- Modify if required by release policy: `nori.json`
- Modify if required by release policy: `.nori-version`
- Modify: `tests/command-guard/helpers.mjs`

**Interfaces:**
- Produces: finding-by-finding closure evidence for RV-01 through RV-17.
- Produces: one reproducible source, installed, and live verification record.

- [ ] **Step 1: Remove the whitespace blocker**

Delete the trailing blank line reported for
`tests/command-guard/helpers.mjs`, then run `git diff --check` against the PR
base and current index.

- [ ] **Step 2: Run the complete deterministic gate**

```bash
bash tests/validate-package.sh
git diff --check origin/main...HEAD
```

Expected: all Node.js, Python, shell syntax, PowerShell syntax, schema,
coverage, mutation, content, and installed-artifact tests pass; no whitespace
errors remain.

- [ ] **Step 3: Run spell and Markdown gates**

```bash
npx --yes cspell@8.17.5 --config .cspell.json \
  README.md docs.md CHANGELOG.md docs/**/*.md
npx --yes markdownlint-cli2@0.17.2 \
  README.md docs.md CHANGELOG.md docs/**/*.md
```

Expected: zero findings.

- [ ] **Step 4: Run the explicitly acknowledged installed live smoke**

```bash
P0_04_LIVE_NORMAL_CREDENTIALS_ACK=I_ACCEPT_PROVIDER_CREDENTIAL_EGRESS_RISK \
  bash tests/live-command-guard-smoke.sh --run-live
```

Expected: Nori installation succeeds; source and installed artifacts match;
representative allow, ask, deny, launcher failure, literal first-use, approved
reuse, session boundary, and provider-control denial probes pass; output states
the accepted normal-credential residual risk.

- [ ] **Step 5: Update architecture and review disposition**

Revise ADR-004 to replace direct Node invocation and stateless literal reuse
with the implemented launcher and approval-binding lifecycle. In the review
record, keep original findings intact and add a closure table with commit and
test evidence for every RV ID. Do not change the verdict to ready until the
new independent review is complete.

- [ ] **Step 6: Reconcile version metadata**

Read the current version from `nori.json`, `.nori-version`, README, and
CHANGELOG. If PR #25 remains an unreleased draft at version `0.11.0`, retain
`0.11.0` and amend its changelog entry. If that version has been published,
advance exactly one patch version and update every version-bearing file in the
same commit.

- [ ] **Step 7: Commit verified documentation**

```bash
git add docs README.md docs.md CHANGELOG.md tests/validation-notes.md \
  tests/command-guard/helpers.mjs nori.json .nori-version
git commit -m "docs: record verified P0-04 command guard architecture"
```

- [ ] **Step 8: Request independent review and update PR #25**

Request a fresh review of the full diff against `origin/main`, explicitly map
RV-01 through RV-17, fix any blocking finding test-first, rerun Steps 2 through
4, push the branch, update the draft PR description with the verdict and test
evidence, and wait for GitHub checks. Do not merge.
