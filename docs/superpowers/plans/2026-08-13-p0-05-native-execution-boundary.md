# P0-05 Native Execution Boundary Implementation Plan

<!-- cspell:words autouse configured_unproven precondition reparse -->

Last updated: 2026-08-21.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the direct-main-session Bash enforcement gap and publish a tested decision boundary between protected shell, executor delegation, typed operational tools, and refusal.

**Architecture:** Extend the existing `command-driven-operations` skill rather
than introduce another command classifier. A strict, operator-owned settings
configurator installs the existing Pre/Post Bash hooks into project-local
Claude Code settings, while a canonical policy document and tests define when
the main session must delegate or require a typed tool. Source, installed Nori,
and opt-in live Claude Code probes distinguish configured settings from
observed enforcement. A harmless session-scoped denial probe establishes live
coverage without authorizing any subsequent command.

**Tech Stack:** Node.js ECMAScript modules and test runner, Python 3.12-compatible standard library tests, Bash, Markdown, JSON, Claude Code native hooks, Nori installed-artifact validation, Debian WSL package gate.

## Global Constraints

- Reuse the ADR-004 command guard; do not create a second parser, classifier, risk taxonomy, or JSON envelope around Bash.
- Direct main-session operational Bash is protected only in the `ACTIVE` state; every other state delegates to a proven executor or performs no execution.
- Exact settings establish only `CONFIGURED_UNPROVEN`; `ACTIVE` requires the current session's exact `printf P005_GUARD_PROBE` call to receive the expected structured command-guard denial.
- Session proof is ephemeral, authorizes no later command, and is invalidated by session resume, clear, compaction, permission-mode, runtime, settings, hook, path, or policy changes.
- Keep settings activation explicit, project-local, reversible, and limited to exact package-owned values.
- Preserve every unrelated operator, project, Nori, P0-04A, and managed setting.
- Require both `PreToolUse` and `PostToolUse` Bash hooks; a single phase is invalid.
- Treat `bypassPermissions` only as a native permission mode, never as an operational risk level or safety guarantee.
- Treat MCP annotations as untrusted hints; authorization and invariant validation remain server-side requirements.
- Do not implement browser automation, an MCP gateway, a model proxy, a provider client, or a parallel runtime.
- Do not pin Claude Code, Nori, Node.js, a provider, a model, or an MCP revision; detect capabilities and record observed versions.
- Never use production targets in tests.
- Never persist prompts, transcripts, raw commands, summaries, credential values, secret-derived state, or synthetic secrets as runtime evidence.
- The external `C:\projects\senior-infra-ops-analyst\TODO-AI-FIRST.md` remains outside Git and cannot be marked complete before merge to `main`.
- Implement with TDD, retain the 82/82 mutation gate, and require independent review plus green CI/Security on the exact final head.

---

### Task 1: Canonical routing contract

**Files:**
- Create: `references/native-execution-boundary.md`
- Create: `tests/test-native-execution-boundary.py`
- Modify: `AGENTS.md`
- Modify: `skills/command-driven-operations/SKILL.md`
- Modify: `tests/validate-package.sh`

**Interfaces:**
- Produces: five lifecycle phases `DIAGNOSE`, `PROPOSE`, `EXECUTE`, `VALIDATE`, and `ROLLBACK`.
- Produces: four execution routes `PROTECTED_BASH`, `PROTECTED_EXECUTOR`, `TYPED_TOOL`, and `NO_EXECUTION`.
- Produces: five coverage states `ACTIVE`, `CONFIGURED_UNPROVEN`, `ABSENT`, `CONFLICT`, and `UNSUPPORTED`.
- Produces: one exact session proof command, `printf P005_GUARD_PROBE`, whose expected structured denial proves coverage but grants no operational authorization.
- Consumes: the canonical risk levels and modifiers from `references/risk-levels.md`.

- [ ] **Step 1: Write failing policy mutation tests**

Create a temporary-copy test harness that mutates one policy requirement at a
time. The test names and stable failure fragments must include:

```python
REQUIRED_CASES = {
    "diagnosis_requires_complete_bounded_read": "bounded read route is missing",
    "proposal_cannot_claim_execution": "proposal/execution separation is missing",
    "main_bash_requires_active_coverage": "ACTIVE main-session gate is missing",
    "settings_are_configured_unproven": "settings-only state is missing",
    "session_probe_is_exact_and_harmless": "session probe contract is missing",
    "session_probe_does_not_authorize_work": "probe authorization boundary is missing",
    "missing_hook_result_stops_or_delegates": "missing-hook disposition is missing",
    "unproven_main_delegates_or_stops": "unproven fallback is missing",
    "destructive_always_asks": "destructive exact-decision rule is missing",
    "deny_cannot_be_upgraded_by_prose": "deny reformulation rule is missing",
    "typed_transaction_required": "transactional typed-tool rule is missing",
    "typed_multitarget_required": "multi-target typed-tool rule is missing",
    "typed_idempotency_required": "idempotency typed-tool rule is missing",
    "missing_typed_tool_does_not_weaken_shell": "missing-capability rule is missing",
    "mcp_annotations_are_hints": "untrusted annotation rule is missing",
    "browser_and_gateway_remain_out_of_scope": "scope boundary is missing",
}
```

Assert that root instructions, the skill body, and the reference use the same
route and coverage-state names. Assert that the reference contains one and
only one routing matrix and that each row has an operation, route, and minimum
condition.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
python3 tests/test-native-execution-boundary.py
```

Expected: failures for the absent reference and missing direct-main-session
routing language. Record the exact failure count in validation notes.

- [ ] **Step 3: Add the canonical reference and concise instructions**

Write `references/native-execution-boundary.md` with these exact normative
sections:

```markdown
## Lifecycle phases
## Coverage states
## Routing matrix
## Protected Bash invariants
## Typed-tool invariants
## Delegation and refusal
## Browser and MCP boundaries
```

Add only concise routing instructions to `AGENTS.md` and the command skill:

```markdown
Direct main-session operational Bash requires ACTIVE command-guard coverage.
Exact settings alone are CONFIGURED_UNPROVEN. In the current session, only an
expected structured guard denial for `printf P005_GUARD_PROBE` establishes
ephemeral ACTIVE coverage; the probe authorizes no subsequent command.
Otherwise delegate to a matching installed executor with proven Pre/Post Bash
hooks. If neither route is proven, do not execute: return the observed
limitation, plan, proposed operation, required approval, and validation steps.
```

Explicitly distinguish an unexecuted proposal from observed evidence. Add the
new reference to the required-reference lists without duplicating the full
matrix in multiple prompt-bearing files.

- [ ] **Step 4: Run focused policy validation and verify GREEN**

Run:

```bash
python3 tests/test-native-execution-boundary.py
python3 tests/validate-content.py
```

Expected: both commands exit zero.

- [ ] **Step 5: Register the focused suite in the package gate**

Add this exact command to `tests/validate-package.sh` beside the other Python
contract suites:

```bash
python3 tests/test-native-execution-boundary.py
```

Run the package script's shell syntax check and confirm the command occurs once.

- [ ] **Step 6: Commit the routing contract**

```bash
git add AGENTS.md references/native-execution-boundary.md skills/command-driven-operations/SKILL.md tests/test-native-execution-boundary.py tests/validate-package.sh
git commit -m "docs: define native execution boundary"
```

### Task 2: Native main-session event contract and pure settings ownership

**Files:**
- Modify: `skills/command-driven-operations/scripts/command-guard/contract.mjs`
- Modify: `tests/command-guard/contract.test.mjs`
- Create: `skills/command-driven-operations/scripts/main-session-settings.mjs`
- Create: `tests/command-guard/main-session-settings.test.mjs`
- Modify: `tests/run-command-guard-tests.mjs`

**Interfaces:**
- Extends: `parseHookEvent(raw)` recognizes the documented ordinary
  main-session shape only when both optional agent identity fields are absent;
  executor identities remain constrained to the existing eight roles.
- Produces: `parseStrictSettings(text: string) -> object`.
- Produces: `desiredMainSessionHooks({ skillRoot, nodeBin, platform }) -> DesiredHooks`.
- Produces: `inspectMainSessionGuard({ scopes, desired, ownership, capabilities }) -> Inspection`.
- Produces: `applyOwnedMainSessionHooks({ current, desired, ownership }) -> ApplyResult`.
- Produces: `removeOwnedMainSessionHooks({ current, ownership }) -> RemoveResult`.
- Consumes: existing launcher, `validate-ops-command.mjs`, and `record-command-approval.mjs` paths from the command skill.

- [ ] **Step 1: Add failing ordinary-main-session event tests**

Require a current native `PreToolUse` Bash payload with both `agent_type` and
`agent_id` absent to normalize to a distinct ordinary-main-session scope.
Reject a payload with only one agent identity field, a synthetic
`main-session` agent type, or an unknown executor. Preserve exact acceptance of
all eight existing executor identities and prove that permission mode does not
change identity classification.

- [ ] **Step 2: Run the event contract suite and verify RED**

```bash
node --test tests/command-guard/contract.test.mjs
```

Expected: the ordinary main-session witness fails because `agent_type` is
currently required.

- [ ] **Step 3: Implement the minimal native event extension**

Represent the ordinary main session with a canonical internal scope only when
both optional agent identity fields are absent. Do not add that scope to
`EXECUTOR_AGENTS`. Preserve rejection of partial, synthetic, malformed, and
unknown identities. The same command parser, catalogue, classifier, response,
audit minimization, and risk matrix apply to both scopes.

- [ ] **Step 4: Add failing strict-settings and desired-hook tests**

Cover valid object roots, invalid JSON, duplicate keys at every depth, scalar
roots, oversized input, Windows and POSIX command quoting, installed paths with
spaces, and exact lifecycle completeness. The required shape is:

```javascript
assert.deepEqual(desired.hooks.map(({ event, matcher }) => [event, matcher]), [
  ['PreToolUse', 'Bash'],
  ['PostToolUse', 'Bash'],
]);
assert.equal(desired.hooks[0].command.includes('validate-ops-command.mjs'), true);
assert.equal(desired.hooks[1].command.includes('record-command-approval.mjs'), true);
```

Reject a desired configuration that has only Pre or only Post.

- [ ] **Step 5: Run the settings suite and verify RED**

Run:

```bash
node --test tests/command-guard/main-session-settings.test.mjs
```

Expected: module-not-found failure for `main-session-settings.mjs`.

- [ ] **Step 6: Implement strict parsing and desired hooks**

Reuse the P0-04A duplicate-key scanner behavior without importing an installed
sibling skill. Keep the module pure and bounded. Build the hook entries using
the installed `command-driven-operations` root and the same launcher contract
already used by executor frontmatter.

The returned inspection object contains only:

```javascript
{
  state: 'ACTIVE' | 'CONFIGURED_UNPROVEN' | 'ABSENT' | 'CONFLICT' | 'UNSUPPORTED',
  reasonCode: 'EXACT_LIVE_PROOF' | 'EXACT_SETTINGS_ONLY' | 'MISSING_HOOKS' |
    'OWNERSHIP_DRIFT' | 'MANAGED_POLICY_BLOCK' | 'CAPABILITY_UNAVAILABLE',
  preHookExact: boolean,
  postHookExact: boolean,
  liveProof: boolean,
}
```

Do not return settings content, hook commands, paths outside the installed skill
root, environment values, or operator hook data.

- [ ] **Step 7: Add failing merge/removal/inspection tests**

Test preservation and exact ownership with these cases:
- empty settings;
- unrelated `permissions`, `env`, `statusLine`, MCP, and hook entries;
- P0-04A compact hooks before and after owned Bash hooks;
- idempotent apply;
- exact owned-only removal;
- operator modification after apply;
- stale ownership;
- missing Pre or Post;
- managed-hook restriction;
- configured-but-unproven state;
- ephemeral live proof matching the exact effective hook identity and current
  session probe result;
- changed runtime/path/settings invalidating live proof.

- [ ] **Step 8: Implement merge, removal, and inspection**

Append only exact entries absent from the target event/matcher. Store ownership
as a schema-versioned list of exact package-owned entries plus a non-secret
configuration identity derived from canonical non-secret structure. Never hash
or fingerprint settings content that might contain secrets. Removal compares
the complete owned entry and reports drift instead of deleting a changed value.

- [ ] **Step 9: Run focused and existing command-guard tests**

Run:

```bash
node --test tests/command-guard/main-session-settings.test.mjs
node tests/run-command-guard-tests.mjs
```

Expected: new tests green; existing 267 tests and 82/82 mutations remain green.

- [ ] **Step 10: Commit the native event and pure settings layer**

```bash
git add skills/command-driven-operations/scripts/command-guard/contract.mjs skills/command-driven-operations/scripts/main-session-settings.mjs tests/command-guard/contract.test.mjs tests/command-guard/main-session-settings.test.mjs tests/run-command-guard-tests.mjs
git commit -m "feat: model main session guard settings"
```

### Task 3: Safe configurator and recovery

**Files:**
- Create: `skills/command-driven-operations/scripts/configure-native-execution-boundary.mjs`
- Create: `tests/command-guard/main-session-settings-cli.test.mjs`
- Create: `tests/test-native-execution-boundary-safety.py`
- Modify: `tests/run-command-guard-tests.mjs`
- Modify: `tests/validate-package.sh`

**Interfaces:**
- Produces CLI modes: `--help`, `--check`, `--apply`, and `--remove-owned`.
- Produces exit codes: `0` exact success, `2` absent/unproven, `3` conflict/unsupported, `64` invalid invocation.
- Produces one bounded JSON status record on stdout for `--check`, `--apply`, and `--remove-owned`.
- Consumes pure interfaces from Task 2.

- [ ] **Step 1: Write failing CLI behavior tests**

Exercise a disposable project and config directory. Assert:

```javascript
assert.equal(run(['--help']).status, 0);
assert.equal(run(['--check']).json.state, 'ABSENT');
assert.equal(run(['--apply']).json.state, 'CONFIGURED_UNPROVEN');
assert.equal(run(['--apply']).json.changed, false); // second apply
assert.equal(run(['--remove-owned']).json.state, 'ABSENT');
```

Also assert `--help` performs no discovery or write, unknown/combined modes exit
64, stdout contains no settings values, and stderr contains no raw hook command.

- [ ] **Step 2: Add adversarial filesystem tests and verify RED**

Cover:
- linked/reparse settings, ownership, lock, transaction, and parent paths;
- non-regular files;
- owner-only creation mode;
- changed target between inspection and replacement;
- two concurrent apply processes;
- lock contention and stale lock handling;
- crash before ownership, between ownership and settings, and after settings;
- exact recovery after each crash point;
- malformed or oversized settings/ownership/transaction records;
- destination replacement during recovery;
- preservation of an operator write arriving before commit;
- no whole-file backup restoration.

Run:

```bash
node --test tests/command-guard/main-session-settings-cli.test.mjs
python3 tests/test-native-execution-boundary-safety.py
```

Expected: failures because the CLI and safety contract do not exist.

- [ ] **Step 3: Implement bounded atomic CLI operations**

Mirror the proven P0-04A transaction discipline:
- resolve project and Claude scopes without following linked final targets;
- validate every relevant ancestor and final target as regular and unlinked;
- acquire one bounded lock;
- re-read and compare the target before commit;
- create owner-only temporary files in the same directory;
- fsync content and directory where supported;
- replace atomically;
- retain a bounded content-free transaction phase for crash recovery;
- remove only exact owned entries.

The ownership and transaction records may contain schema version, lifecycle
event, matcher, reason code, and non-secret structural identity. They may not
contain command strings, full paths outside the installed skill, settings
values, prompts, transcripts, or credentials.

- [ ] **Step 4: Implement static safety validation**

Make `tests/test-native-execution-boundary-safety.py` inspect the CLI and later
live harness for forbidden persistence and dangerous filesystem operations.
Required assertions include no transcript access, no credential environment
enumeration, no recursive deletion, no unbounded user-home target, no shell
interpolation of settings content, and no raw command in evidence schemas.

- [ ] **Step 5: Run focused tests and existing install-policy tests**

Run:

```bash
node --test tests/command-guard/main-session-settings-cli.test.mjs
python3 tests/test-native-execution-boundary-safety.py
python3 tests/test-command-guard-install-policy.py
node tests/run-command-guard-tests.mjs
```

Expected: all green, including 82/82 mutations.

- [ ] **Step 6: Register suites and commit**

Add the CLI suite to `tests/run-command-guard-tests.mjs` and the Python safety
suite once to `tests/validate-package.sh`, then commit:

```bash
git add skills/command-driven-operations/scripts/configure-native-execution-boundary.mjs tests/command-guard/main-session-settings-cli.test.mjs tests/test-native-execution-boundary-safety.py tests/run-command-guard-tests.mjs tests/validate-package.sh
git commit -m "feat: add opt-in main session guard activation"
```

### Task 4: Installed Nori boundary

**Files:**
- Modify: `tests/command_guard_install_policy.py`
- Modify: `tests/test-command-guard-install-policy.py`
- Modify: `tests/validate-installed-subagents.py`
- Modify: `tests/live-nori-package-smoke.sh`
- Modify: `README.md`
- Modify: `docs.md`

**Interfaces:**
- Consumes: a Nori-installed `command-driven-operations` skill and 12 installed subagents.
- Produces: content-free installed inspection with exact `preHook`, `postHook`, `configurator`, and `operatorSettingsPreserved` booleans.

- [ ] **Step 1: Add failing installed-artifact assertions**

Require the installed skill to contain the configurator, pure settings module,
launcher, validator, approval recorder, and boundary reference. Require all
eight executor artifacts to retain exact Pre/Post Bash hook commands pointing
at the installed skill path. Require all four analytical roles to remain
without Bash.

Add negative fixtures for a source checkout path embedded in an installed
command, missing Post hook, extra unguarded executor, and linked script target.

- [ ] **Step 2: Run focused installed tests and verify RED**

Run:

```bash
python3 tests/test-command-guard-install-policy.py
python3 tests/test-installed-subagents.py
```

Expected: failures for the absent configurator and boundary-reference checks.

- [ ] **Step 3: Extend the disposable Nori smoke**

In a generated home, install the current worktree through the detected Nori
CLI or its existing test double. Apply main-session hooks to a disposable
project containing unrelated operator settings and a sentinel hook. Assert:
- installed-path commands are used;
- source paths are absent;
- unrelated settings and sentinel hooks remain exact;
- second apply is unchanged;
- owned removal restores the original semantic settings;
- no active operator profile is linked or changed;
- no upload, login, token lookup, or network mutation occurs.

- [ ] **Step 4: Document activation without claiming automatic installation**

Add concise operator commands to README and `docs.md` using the installed script:

```bash
node "<installed-command-driven-operations>/scripts/configure-native-execution-boundary.mjs" --check
node "<installed-command-driven-operations>/scripts/configure-native-execution-boundary.mjs" --apply
node "<installed-command-driven-operations>/scripts/configure-native-execution-boundary.mjs" --remove-owned
```

State that Nori installation alone does not activate project-local main-session
hooks and that `CONFIGURED_UNPROVEN` is not runtime proof.

- [ ] **Step 5: Run installed validation and commit**

```bash
python3 tests/test-command-guard-install-policy.py
python3 tests/test-installed-subagents.py
bash tests/live-nori-package-smoke.sh --self-test
git add README.md docs.md tests/command_guard_install_policy.py tests/test-command-guard-install-policy.py tests/validate-installed-subagents.py tests/live-nori-package-smoke.sh
git commit -m "test: validate installed execution boundary"
```

### Task 5: Real main-session and fallback evidence

**Files:**
- Create: `tests/live-native-execution-boundary-smoke.sh`
- Create: `tests/native-execution-boundary-pty.py`
- Create: `tests/test-native-execution-boundary-pty.py`
- Modify: `tests/test-native-execution-boundary-safety.py`
- Modify: `tests/validation-notes.md`
- Modify: `README.md`

**Interfaces:**
- Produces stages: `self-test`, `main-default`, `main-bypass`, and `executor-fallback`.
- Produces one bounded evidence document containing booleans, reason codes, observed runtime labels, and counts only.
- Consumes an operator-configured Claude Code provider without reading or copying credential values.

- [ ] **Step 1: Write PTY parser tests before the driver**

Use synthetic captures to require exact ordered evidence:

```python
EXPECTED = [
    "main-default:PreToolUse:deny",
    "main-bypass:PreToolUse:deny",
    "executor-fallback:PreToolUse:deny",
]
```

Reject missing, repeated, orphaned, reordered, echoed-only, stale-session, and
malformed evidence. Include large-output and timeout bounds. Ensure prompt text
cannot satisfy an observation marker.

- [ ] **Step 2: Run PTY tests and verify RED**

```bash
python3 tests/test-native-execution-boundary-pty.py
```

Expected: import or file-not-found failure for the absent driver.

- [ ] **Step 3: Implement the bounded PTY driver**

The driver must:
- send one exact synthetic request per stage;
- identify evidence only from content-free hook audit events tied to the
  current session and stage nonce;
- never copy the prompt, terminal capture, transcript, or command into the
  evidence file;
- wait within an explicit timeout;
- cancel safely and classify timeout as inconclusive;
- require exact sequence equality, not suffix matching;
- emit no credential or environment value.

- [ ] **Step 4: Implement the opt-in live harness**

The harness must use a disposable project, home, settings file, audit directory,
and synthetic target. It applies the exact main hooks, invokes the detected
Claude Code in normal and `bypassPermissions` modes, and requests an unknown
harmless fixture call, exactly `printf P005_GUARD_PROBE`, that the guard
deterministically denies before execution.
It then removes main hooks and proves the executor fallback produces the same
guard family and denial reason.

Gate provider access behind explicit opt-in and acknowledgement. Import only
the minimum existing Claude/provider configuration required to start the
session. Mount or expose no production target. Remove generated homes and
captures on every exit. Record observed Claude Code, Nori, provider/model label,
platform, permission mode, and complete booleans only.

- [ ] **Step 5: Add static and self-test gates**

The self-test uses a fake Claude executable and fake Nori install with no API
call. The safety test must reject any harness change that reads transcript
paths, enumerates secret variables, preserves PTY content, permits arbitrary
commands, lacks cleanup, or accepts a non-disposable target.

Run:

```bash
python3 tests/test-native-execution-boundary-pty.py
python3 tests/test-native-execution-boundary-safety.py
bash tests/live-native-execution-boundary-smoke.sh --self-test
```

- [ ] **Step 6: Run the real opt-in probe**

After the operator explicitly authorizes provider use, run the bounded live
harness in Debian WSL. Expected acceptance requires all three exact observations
and cleanup success. If capability is absent or the cycle times out, record
`INCONCLUSIVE` and do not claim `ACTIVE` or complete P0-05.

- [ ] **Step 7: Commit the live contract and honest evidence**

```bash
git add README.md tests/live-native-execution-boundary-smoke.sh tests/native-execution-boundary-pty.py tests/test-native-execution-boundary-pty.py tests/test-native-execution-boundary-safety.py tests/validation-notes.md
git commit -m "test: prove live native execution routing"
```

### Task 6: Architecture, version, and content integration

**Files:**
- Create: `docs/architecture/ADR-008-native-execution-boundary.md`
- Modify: `docs/architecture/README.md`
- Modify: `CHANGELOG.md`
- Modify: `nori.json`
- Modify: `.nori-version`
- Modify: `skills/command-driven-operations/nori.json`
- Modify: `skills/command-driven-operations/SKILL.md`
- Modify: `README.md`
- Modify: `docs.md`
- Modify: `tests/test-architecture-docs.py`
- Modify: `tests/test-release-history.py`
- Modify: `tests/validate-content.py`

**Interfaces:**
- Produces: accepted ADR-008 linked exactly once from the architecture index.
- Produces: version `0.13.0` as an unpublished repository state.
- Produces: `command-driven-operations` component version `1.1.0` and skill
  document revision `0.6.0` dated `2026-08-13`.
- Consumes: implemented behavior and real validation evidence from Tasks 1-5.

- [ ] **Step 1: Add failing architecture and release-history tests**

Require ADR-008 to contain the decision, routing matrix reference, operator
ownership, runtime-proof limitation, rejected alternatives, validation evidence,
and residual risks. Require the index to link it exactly once.

Require exactly one changelog heading:

```markdown
## [0.13.0] - Unpublished
```

Require `nori.json`, `.nori-version`, README metadata, and `docs.md` to agree on
`0.13.0`. Keep `0.12.0` as the published release entry with its existing body
unchanged. Require `skills/command-driven-operations/nori.json` to report
`1.1.0`, the skill frontmatter to report `version: 0.6.0` and
`last_updated: 2026-08-13`, and `skills.json` to retain the canonical `"*"`
entry rather than duplicating a component version there.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
python3 tests/test-architecture-docs.py
python3 tests/test-release-history.py
python3 tests/validate-content.py
```

Expected: failures for missing ADR-008 and missing 0.13.0 unpublished state.

- [ ] **Step 3: Write ADR-008 and integrate documentation**

Write only implemented facts. Distinguish:
- source contract passed;
- installed contract passed;
- live direct main-session behavior observed or inconclusive;
- executor fallback observed or inconclusive;
- P0-04B and P3-16 follow-ups.

Do not turn configuration presence into live proof. Document that direct
main-session autonomy remains unavailable wherever the state is not `ACTIVE`.

- [ ] **Step 4: Update the unpublished version state**

Bump canonical current-version locations to `0.13.0`, the changed first-class
component manifest to `1.1.0`, and its internal skill-document revision to
`0.6.0` with the current date. Add curated changelog bullets for the
execution-routing policy, opt-in settings ownership, installed validation, and
live result. Do not tag, publish a GitHub Release, or upload to Nori.

- [ ] **Step 5: Run focused content gates and commit**

```bash
python3 tests/test-architecture-docs.py
python3 tests/test-release-history.py
python3 tests/validate-content.py
python3 tests/validate-schema.py
git add .nori-version CHANGELOG.md README.md docs.md nori.json skills/command-driven-operations/nori.json skills/command-driven-operations/SKILL.md docs/architecture/ADR-008-native-execution-boundary.md docs/architecture/README.md tests/test-architecture-docs.py tests/test-release-history.py tests/validate-content.py
git commit -m "docs: record native execution boundary architecture"
```

### Task 7: Complete verification and independent review

**Files:**
- Modify only when a verified failure requires remediation.

**Interfaces:**
- Consumes: the complete P0-05 branch.
- Produces: exact final-head local evidence and an independent review verdict.

- [ ] **Step 1: Run focused gates from a clean worktree**

```bash
git status --short
node tests/run-command-guard-tests.mjs
python3 tests/test-native-execution-boundary.py
python3 tests/test-native-execution-boundary-safety.py
python3 tests/test-native-execution-boundary-pty.py
python3 tests/test-command-guard-install-policy.py
python3 tests/test-installed-subagents.py
python3 tests/test-architecture-docs.py
python3 tests/test-release-history.py
python3 tests/validate-content.py
python3 tests/validate-schema.py
bash tests/live-native-execution-boundary-smoke.sh --self-test
git diff --check
```

Expected: every command exits zero; command guard reports all pristine tests and
82/82 mutations.

- [ ] **Step 2: Run the complete package gate through Debian WSL**

Use the repository's authorized Debian WSL route with the compatible detected
Node runtime and run:

```bash
bash tests/validate-package.sh
```

Expected: exit zero. Record observed runtimes and exact counts without turning
them into version restrictions.

- [ ] **Step 3: Inspect source and installed diffs**

Confirm:
- no production target, secret, prompt, transcript, PTY capture, or generated
  runtime file is tracked;
- every final deliverable is English;
- only P0-05 behavior and required release metadata changed;
- P0-04A settings ownership remains compatible;
- no browser implementation or MCP server was added;
- worktree contains no unexpected untracked artifact.

- [ ] **Step 4: Request independent read-only review**

Review the exact final commit for:
- main-session bypasses;
- incomplete Pre/Post coverage;
- `bypassPermissions` misinterpretation;
- settings overwrite, link/reparse, time-of-check/time-of-use, recovery, or
  ownership flaws;
- false-positive live evidence;
- MCP annotation trust;
- scope creep into P0-04B or P3-16;
- documentation claims exceeding evidence.

Do not proceed with unresolved Critical or Important findings. Apply each
accepted remediation with focused RED/GREEN evidence, rerun the complete gate,
and request a fresh review of the new exact head.

- [ ] **Step 5: Commit any review-approved remediation**

Stage only reviewed files, commit with a scoped message, and verify:

```bash
git status --short
git diff --check HEAD^ HEAD
```

### Task 8: Publish for CI and close only after merge

**Files:**
- Update after merge only: `C:\projects\senior-infra-ops-analyst\TODO-AI-FIRST.md`.

**Interfaces:**
- Consumes: clean, reviewed, locally passing final head.
- Produces: pushed branch, reviewed PR, green CI/Security, merge commit, and external TODO evidence.

- [ ] **Step 1: Rebase safely on current `origin/main`**

Fetch without modifying operator Git configuration. If main advanced, rebase
the isolated branch, resolve only P0-05 overlaps, rerun focused and complete
gates, and obtain a fresh independent verdict for the rebased exact head.

- [ ] **Step 2: Push and open a draft PR after operator authorization**

Push `p0-05-native-execution-boundary` and open a draft PR containing:
- scope and explicit exclusions;
- routing decision;
- settings ownership behavior;
- source, installed, and live evidence;
- observed versions;
- residual risks and rollback;
- exact final head SHA.

- [ ] **Step 3: Require exact-head CI and Security**

Wait for every required workflow. Confirm each check belongs to the recorded PR
head. Do not mark ready while any required check is missing, pending, skipped
unexpectedly, failed, or bound to another commit.

- [ ] **Step 4: Mark ready only after all P0-05 acceptance gates**

The PR may leave draft only when deterministic, installed, and real acceptance
tests pass, the independent review approves the exact head, and CI/Security are
green on that head. An inconclusive live main-session result keeps P0-05 open
unless the operator explicitly approves a revised acceptance design in a new
versioned decision.

- [ ] **Step 5: Merge only on a separate explicit operator request**

Reconfirm the reviewed head SHA immediately before merge and use head-bound
merge protection. Do not force-push tags, create a GitHub Release, upload the
skillset, or merge automatically.

- [ ] **Step 6: Synchronize and update the external TODO**

After confirming the merge commit is present in local and remote `main`, update
P0-05 to `CONCLUÍDO` with version, branch, PR, merge SHA, deterministic counts,
installed evidence, live evidence, independent verdict, and CI/Security state.
Keep browser and MCP gateway work pending under P0-04B and P3-16.

- [ ] **Step 7: Refresh generated staging only after requested**

If the operator requests it, rebuild the external Nori staging directory from
the merged canonical repository using the safe staging tool. Validate inventory
and hashes; do not upload or change the active profile without separate
authorization.

**Testing Details** The plan adds black-box policy mutations, pure settings and CLI behavior tests, adversarial filesystem safety cases, installed Nori validation, exact PTY anti-echo tests, a no-provider self-test, and an opt-in real Claude Code main/fallback probe. Existing command-guard tests and all 82 semantic mutations remain mandatory.

**Implementation Details** Reuse ADR-004's Pre/Post Bash guard; install only
exact project-local owned hooks; preserve operator settings and P0-04A
ownership; distinguish configuration from observed enforcement; delegate when
direct coverage is not `ACTIVE`; require typed tools for invariants shell
cannot prove; treat MCP annotations as hints; keep browser and gateway
implementation out of scope; publish 0.13.0 as unpublished; close the external
TODO only after merge.

**Question** No implementation blocker remains. Provider-backed live validation and all GitHub writes require their normal explicit operator authorizations when those steps are reached.

---
