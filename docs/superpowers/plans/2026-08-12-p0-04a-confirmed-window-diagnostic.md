# P0-04A Confirmed-Window Diagnostic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add and execute an operator-approved diagnostic that makes the already detected DeepSeek context capacity explicit only for the real automatic-compaction child process.

**Architecture:** The live harness accepts one opt-in numeric argument, derives the runtime capacity from the existing `/context` capture, and blocks unless the two values are identical. Only the automatic child receives the confirmed value; installed and operator settings remain percentage-only.

**Tech Stack:** Bash, Python 3 standard library, Claude Code PTY harness, Node.js package validation.

## Global Constraints

- Keep auto-compaction enabled and the production default at 72 percent.
- Do not pin Claude Code, Nori, DeepSeek, provider, or context-window versions.
- Do not persist transcript, prompt, response, compact summary, credential, secret, or raw debug content.
- Keep both compact hooks non-blocking.
- Preserve operator settings and the existing 100,000-unit and 600-second bounds.
- Use the confirmed absolute value only in the explicitly approved live diagnostic process.

---

### Task 1: Add the fail-closed diagnostic option

**Files:**
- Modify: `tests/live-context-continuity-smoke.sh`
- Modify: `tests/test-live-context-continuity-safety.py`

**Interfaces:**
- Consumes: `--run-live`, the existing manual `/context` PTY capture, and a positive integer supplied through `--confirmed-window-diagnostic`.
- Produces: `CONFIRMED_WINDOW_DIAGNOSTIC`, either empty or the exact native capacity allowed only for the automatic child.

- [ ] **Step 1: Write failing static and behavioral tests**

Add assertions that the option requires a value, rejects self-test mode,
rejects non-numeric and mismatched capacities, and is injected only beside the
real automatic invocation.

- [ ] **Step 2: Run the focused tests and confirm RED**

Run: `python tests/test-live-context-continuity-safety.py`

Expected: failures because the option and equality gate do not exist.

- [ ] **Step 3: Implement the minimal option parser and equality gate**

Parse the option without `eval`, validate `^[1-9][0-9]*$`, derive the runtime
window from the final native `[Nk]` or `[Nm]` label in `manual.pty`, and call
`blocked` unless the values match exactly.

- [ ] **Step 4: Inject the value into only the automatic child**

Build an automatic-only environment array. Append
`CLAUDE_CODE_AUTO_COMPACT_WINDOW=<confirmed>` only when the option was supplied;
leave settings and every earlier provider process unchanged.

- [ ] **Step 5: Run focused tests and confirm GREEN**

Run: `python tests/test-live-context-continuity-safety.py`

Expected: all tests pass.

### Task 2: Verify the complete deterministic package

**Files:**
- Modify only if verification reveals a diagnostic-contract defect.

**Interfaces:**
- Consumes: the completed opt-in harness change.
- Produces: deterministic evidence that normal and diagnostic routes preserve all existing safety gates.

- [ ] **Step 1: Run the shell self-test in Git Bash or WSL**

Run: `bash tests/live-context-continuity-smoke.sh --self-test`

Expected: `live context continuity parser self-test passed`.

- [ ] **Step 2: Run the repository's complete package gate**

Run: the package validation command documented by the repository.

Expected: all validation, security mutation, schema, Python, and Node checks pass.

- [ ] **Step 3: Commit the reproducible diagnostic**

Commit the design, plan, tests, and minimal harness implementation with no live
content artifacts.

### Task 3: Execute and interpret the real DeepSeek diagnostic

**Files:**
- Modify: `tests/validation-notes.md`
- Modify: `docs/architecture/ADR-005-context-continuity-and-preventive-compaction.md`

**Interfaces:**
- Consumes: operator-approved value `1000000`, the temporary DeepSeek credential route, and the isolated Nori/Claude Code harness.
- Produces: one of `complete_pair`, `pre_only`, or `no_pre`, plus numeric-only context/window evidence.

- [ ] **Step 1: Run the isolated live harness**

Run the existing credential-safe WSL launcher with `--run-live
--confirmed-window-diagnostic 1000000`. Do not retain content captures.

- [ ] **Step 2: Classify the exact structural result**

Accept only an observed ordered `PreCompact(auto)` then `PostCompact(auto)` as a
complete pair. Never synthesize a missing phase.

- [ ] **Step 3: Document the evidence honestly**

Record observed versions, numeric capacity/context, whether exact equality was
proven, elapsed bound, and the structural result. Keep the PR draft if the pair
is absent.

- [ ] **Step 4: Re-run focused documentation and safety tests**

Run the architecture documentation tests, live-harness safety tests, and the
full package gate after documentation changes.

- [ ] **Step 5: Request independent review and refresh the PR head**

Review the exact diff and evidence, push only after all local gates pass, then
wait for CI/Security. Do not merge without an explicit operator request.
