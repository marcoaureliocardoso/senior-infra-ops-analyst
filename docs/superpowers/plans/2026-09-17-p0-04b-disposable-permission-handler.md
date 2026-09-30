# P0-04B Disposable Permission Handler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a test-only permission MCP that deterministically allows one exact synthetic browser mutation, denies a second different mutation, and proves the deny caused no additional effect without changing production approval behavior.

**Architecture:** A Node.js verifier reuses the production Bash and browser workflow parsers. A minimal Python stdio MCP server applies one phase-bound decision and writes only content-free one-use evidence. The POSIX/WSL harness creates separate strict MCP configurations for measurement, allow, and deny sessions, then reduces the two ordered workflow streams and fixture state into the existing bounded aggregate.

**Tech Stack:** Node.js 24 ESM and `node:test`, Python 3.12+ standard library and `unittest`, Bash, Claude Code CLI, stdio MCP JSON-RPC, Playwright detected at runtime.

**Spec:** `docs/superpowers/specs/2026-09-17-p0-04b-disposable-permission-handler-design.md`

## Global Constraints

- The handler, verifier, configs, signals, and claims exist only in `tests/` or a disposable runtime and never enter Nori staging, archives, installed skills, or production settings.
- Production mutable browser work continues to use the native interactive Claude Code permission prompt for every `ask`.
- The automated evidence label is exactly `synthetic-deterministic`; it never claims observed human approval.
- The allow and deny phases use distinct sessions, operations, claims, signals, desired states, and invocation fingerprints.
- Only the first structurally exact allow-phase request is allowed; only the first structurally exact deny-phase request receives the planned denial; all mismatches and extra calls deny generically.
- No raw command, workflow record, prompt, stream, permission request, browser content, credential, or fixture state survives final aggregation.
- The authenticated budget is exactly six top-level provider requests and at most 40 model turns, with no automatic retry.
- Native Windows remains inconclusive; private files require POSIX `O_NOFOLLOW`, owner-only mode, atomic creation, and bounded size.
- Use Debian WSL with Node.js `v24.17.0` for focused and complete package gates.

---

### Task 1: Closed Structural Permission Verifier

**Files:**
- Create: `tests/browser-permission-verifier.mjs`
- Create: `tests/browser-permission-verifier.test.mjs`
- Modify: `tests/validate-package.sh:31-37`

**Interfaces:**
- Consumes: `lexBash(command)`, `buildComposition(lexed)`, `parseRunnerArgs(argv, now)`, and the production workflow fingerprint returned by `parseRunnerArgs`.
- Produces: `verifyPermissionRequest(request, expected, now) -> Readonly<{verified:boolean, reasonCode:string, phase:string|null, decision:string|null, invocationFingerprint:string|null, operationId:string|null, expectedEffect:string|null, executionSteps:number, validationSteps:number}>` and the same record as one JSON line from the CLI.

- [ ] **Step 1: Write the failing verifier tests**

Create table-driven tests with literal expectations. Build valid workflow command inputs locally with canonical base64url JSON records, but hand-assert the structural result:

```js
import assert from 'node:assert/strict';
import path from 'node:path';
import test from 'node:test';
import { verifyPermissionRequest } from './browser-permission-verifier.mjs';

const NOW = 1_800_000_000_000;
const RUNNER = path.resolve('skills/browser-operations/scripts/browser-runner.mjs');
const ORIGIN = 'http://127.0.0.1:43111';
const token = (value) => Buffer.from(JSON.stringify(value), 'utf8').toString('base64url');

function command(sessionId, operationId, phase) {
  const change = phase === 'allow';
  const execution = [
    { step: 'navigate', origin: ORIGIN },
    { step: 'click', origin: ORIGIN, locatorRole: 'link', locatorName: 'Login', effect: 'INTERACTIVE_STATE' },
    { step: 'fill', origin: ORIGIN, locatorRole: 'textbox', locatorName: 'Password', valueRef: 'env:OPS_BROWSER_VALUE_PASSWORD', valueClass: 'credential' },
    { step: 'click', origin: ORIGIN, locatorRole: 'button', locatorName: 'Continue', effect: 'INTERACTIVE_STATE' },
    { step: 'fill', origin: ORIGIN, locatorRole: 'textbox', locatorName: 'Code', valueRef: 'env:OPS_BROWSER_VALUE_TOTP', valueClass: 'credential' },
    { step: 'click', origin: ORIGIN, locatorRole: 'button', locatorName: 'Verify', effect: 'INTERACTIVE_STATE' },
    ...(change ? [
      { step: 'select', origin: ORIGIN, locatorRole: 'combobox', locatorName: 'WAN enabled', valueRef: 'env:OPS_BROWSER_VALUE_DISABLED', valueClass: 'configuration' },
      { step: 'click', origin: ORIGIN, locatorRole: 'button', locatorName: 'Save', effect: 'LOW_RISK_CHANGE' },
    ] : [
      { step: 'click', origin: ORIGIN, locatorRole: 'button', locatorName: 'Rollback', effect: 'LOW_RISK_CHANGE' },
    ]),
  ];
  const validation = [
    ...execution.slice(0, 6),
    { step: 'inspect', origin: ORIGIN, locatorRole: 'status', locatorName: 'Saved state', predicate: 'text-equals', expectedRef: change ? 'env:OPS_BROWSER_VALUE_EXPECTED_FALSE' : 'env:OPS_BROWSER_VALUE_EXPECTED_TRUE', expectRef: 'interface-state' },
  ];
  const args = [
    '--step', 'workflow', '--operation-id', operationId,
    '--session-id', sessionId, '--role', 'network-edge-operator',
    '--objective-ref', 'p004b-run-001', '--target', 'loopback-router',
    '--environment', 'test', '--service-origin', ORIGIN, '--auth-origin', ORIGIN,
    '--identity-ref', 'vault:network-admin', '--credential-transport', 'vault',
    '--permission-mode', 'normal', '--action', 'navigate', '--action', 'fill',
    '--action', 'select', '--action', 'click', '--action', 'inspect',
    '--effect', 'LOW_RISK_CHANGE', '--risk', 'LOW_RISK_CHANGE',
    '--precondition-ref', 'fixture-ready', '--validation-ref', 'interface-state',
    '--compensation-ref', 'fixture-rollback', '--expires-in-seconds', '600',
    ...execution.flatMap((step) => ['--workflow-step', token(step)]),
    ...validation.flatMap((step) => ['--validation-step', token(step)]),
  ];
  return `node ${JSON.stringify(RUNNER)} ${args.map((item) => JSON.stringify(item)).join(' ')}`;
}

test('allow phase accepts only the exact synthetic change workflow', () => {
  const request = { tool_name: 'Bash', input: { command: command('allow-session', 'allow-operation', 'allow') } };
  const result = verifyPermissionRequest(request, {
    phase: 'allow', decision: 'allow', runnerPath: RUNNER,
    operationId: 'allow-operation',
    sessionId: 'allow-session', runNonce: 'p004b-run-001', origin: ORIGIN,
  }, NOW);
  assert.deepEqual({
    verified: result.verified, reasonCode: result.reasonCode, phase: result.phase,
    decision: result.decision, operationId: result.operationId,
    expectedEffect: result.expectedEffect, executionSteps: result.executionSteps,
    validationSteps: result.validationSteps,
  }, {
    verified: true, reasonCode: 'P004B_PERMISSION_EXACT', phase: 'allow',
    decision: 'allow', operationId: 'allow-operation',
    expectedEffect: 'LOW_RISK_CHANGE', executionSteps: 8, validationSteps: 7,
  });
  assert.match(result.invocationFingerprint, /^[0-9a-f]{64}$/u);
});
```

Add separate cases for the exact rollback-shaped deny phase and for wrong tool, unknown input key, multiline command, pipeline, redirect, assignment, nonliteral `node`, changed runner, nonce, session, origin, role, target, environment, identity reference, transport, effect, action, value reference, expected reference, expiry, step order, and phase. Each rejection must equal the same content-free record with `verified:false`, `reasonCode:'P004B_PERMISSION_MISMATCH'`, null identity fields, and zero counts.

- [ ] **Step 2: Run the verifier test and observe RED**

Run:

```powershell
& 'C:\Users\Marco\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' --test tests/browser-permission-verifier.test.mjs
```

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `browser-permission-verifier.mjs`.

- [ ] **Step 3: Implement the minimal closed verifier**

Implement the exact public function and a CLI that accepts seven fixed arguments (`phase`, `runnerPath`, `operationId`, `sessionId`, `runNonce`, `origin`, `decision`), reads at most 65,536 bytes from stdin, and writes one JSON line. Binding the expected operation ID prevents a structurally valid command for a different operation from inheriting the decision. Core parsing must use the production components:

```js
const lexed = lexBash(command);
const composition = buildComposition(lexed);
if (composition.stages.length !== 1 || composition.operators.length !== 0
    || composition.redirects.length !== 0) return mismatch();
const argv = composition.stages[0].argv;
if (argv[0] !== 'node' || path.resolve(argv[1]) !== path.resolve(expected.runnerPath)) {
  return mismatch();
}
const workflow = parseRunnerArgs(argv.slice(2), now);
```

Compare closed common envelope fields and exact phase-specific step arrays. Return the parser's canonical `invocationFingerprint`; never hash rejected data or copy request values into failures. Freeze every returned record.

- [ ] **Step 4: Run focused verifier tests and mutation review**

Run the Windows Node test, then the same test under Debian WSL. Mentally mutate each phase branch, the single-stage condition, session, origin, value reference, decision, and fingerprint return; confirm at least one named test fails for each mutation.

Expected: all verifier tests pass on both platforms.

- [ ] **Step 5: Add the verifier test to the package gate and commit**

Add this exact line after the browser workflow tests in `tests/validate-package.sh`:

```bash
node --test tests/browser-permission-verifier.test.mjs
```

Commit:

```powershell
git add tests/browser-permission-verifier.mjs tests/browser-permission-verifier.test.mjs tests/validate-package.sh
git commit -m "test: verify exact browser permission workflows"
```

---

### Task 2: Single-Use Disposable Permission MCP

**Files:**
- Create: `tests/browser-permission-mcp.py`
- Create: `tests/test-browser-permission-mcp.py`
- Modify: `tests/validate-package.sh:31-39`

**Interfaces:**
- Consumes: the Task 1 verifier CLI and fixed arguments.
- Produces: one stdio MCP tool `approval_prompt`; an owner-only signal `{schemaVersion,runNonce,phase,decision,callCount,invocationFingerprint,verified,inputUnchanged}`; and an exclusive owner-only claim containing only `claimed\n`.

- [ ] **Step 1: Write failing real-process MCP protocol tests**

Start the actual server with temporary absolute paths. Exercise initialize, initialized notification, tools/list, and tools/call over pipes. Assert the allow response's text decodes twice into the official permission object and preserves the exact Bash input:

```python
permission = json.loads(called["result"]["content"][0]["text"])
self.assertEqual(permission, {
    "behavior": "allow",
    "updatedInput": request_arguments["input"],
})
self.assertEqual(json.loads(signal.read_text(encoding="utf-8")), {
    "schemaVersion": 1,
    "runNonce": "p004b-run-001",
    "phase": "allow",
    "decision": "allow",
    "callCount": 1,
    "invocationFingerprint": expected_fingerprint,
    "verified": True,
    "inputUnchanged": True,
})
```

Use the real Task 1 verifier and a real valid command. Add independent tests for deterministic deny, mismatched request, call-before-list, duplicate call, concurrent claim, oversized input, malformed JSON, symlink claim, symlink signal, non-POSIX behavior, verifier crash, verifier timeout, and secret-canary absence from signal, claim, stderr, and generic mismatch response.

- [ ] **Step 2: Run the MCP tests and observe RED**

Run:

```powershell
python tests/test-browser-permission-mcp.py
```

Expected: FAIL because `tests/browser-permission-mcp.py` does not exist.

- [ ] **Step 3: Implement the minimal stdio server**

Follow the existing `mcp-context-fixture.py` protocol shape. Accept exactly eleven arguments after the script: verifier, Node binary, runner, phase, decision, operation ID, session, nonce, origin, claim, and signal. Reject Windows, relative paths, links, invalid labels, or any phase/decision pair other than `allow/allow` and `deny/deny`.

For `tools/call`, require this exact outer shape:

```python
{
    "name": "approval_prompt",
    "arguments": {"tool_name": "Bash", "input": {"command": "..."}},
}
```

Pass only the `arguments` object to the verifier. Bound the subprocess to five seconds and 4,096 output bytes. Atomically claim with `os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW`, mode `0o600`, before returning either planned decision. Write the signal through a same-directory exclusive temporary file, `fsync`, `os.replace`, and final mode `0o600`.

Return the original `input` object only for exact allow. Planned deny returns `{"behavior":"deny","message":"P004B_SYNTHETIC_DENY"}`. Every other denial returns `P004B_PERMISSION_DENIED`.

- [ ] **Step 4: Run server tests on Windows and WSL**

Windows must run protocol-independent validation cases and report the declared POSIX skips. Debian WSL must run every case, including ownership, links, exclusivity, and concurrency.

Expected: all executable cases pass and no test asserts source text.

- [ ] **Step 5: Add the server suite to the package gate and commit**

Add:

```bash
python3 tests/test-browser-permission-mcp.py
```

Commit:

```powershell
git add tests/browser-permission-mcp.py tests/test-browser-permission-mcp.py tests/validate-package.sh
git commit -m "test: add deterministic browser permission MCP"
```

---

### Task 3: Strict Phase-Specific MCP Configuration

**Files:**
- Modify: `tests/browser-mcp-config.py`
- Modify: `tests/test-browser-mcp-config.py`

**Interfaces:**
- Consumes: absolute regular paths for the Task 2 handler, Task 1 verifier, Node binary, installed runner, context fixture, output directory; bounded run nonce, origin, allow session, and deny session.
- Produces: private `empty-mcp.json`, `measurement-mcp.json`, `allow-mcp.json`, and `deny-mcp.json`; fixed permission tool name `mcp__p004b-permission__approval_prompt`; fixed claim and signal paths beneath the output directory.

- [ ] **Step 1: Replace external-config tests with failing disposable-config tests**

Assert behavior by reading generated JSON, modes, and paths. The exact server sets must be:

```python
self.assertEqual(empty["mcpServers"], {})
self.assertEqual(set(measurement["mcpServers"]), {"p004b-context"})
self.assertEqual(set(allow["mcpServers"]), {"p004b-permission"})
self.assertEqual(set(deny["mcpServers"]), {"p004b-permission"})
self.assertEqual(allow_server["command"], sys.executable)
self.assertEqual(allow_server["args"][4:6], ["allow", "allow"])
self.assertEqual(deny_server["args"][4:6], ["deny", "deny"])
self.assertNotEqual(allow_server["args"][6], deny_server["args"][6])
```

Assert all four files are `0600`; handler/verifier/runner/fixture paths are canonical regular non-symlinks; output directory is canonical, private, and absolute; allow and deny sessions differ; claims and signals differ; no environment map, external MCP server, token, or secret field is emitted. Reject links, relative paths, duplicate sessions, invalid origins, unbounded labels, unsafe output directories, and pre-existing output targets.

- [ ] **Step 2: Run config tests and observe RED**

Run under Debian WSL:

```bash
python3 tests/test-browser-mcp-config.py
```

Expected: FAIL because the existing builder still expects an operator MCP source and emits approval-plus-measurement configs.

- [ ] **Step 3: Rewrite the builder to the new closed interface**

Expose:

```python
def build(
    handler: Path, verifier: Path, node: Path, runner: Path,
    fixture: Path, output_dir: Path, fixture_signal: Path,
    nonce: str, origin: str, allow_session: str, deny_session: str,
) -> None:
    ...
```

Use the existing private atomic writer. Create no directories and overwrite no files. Build handler arguments in the exact Task 2 order. Do not copy any operator configuration.

- [ ] **Step 4: Run the config tests and existing safety suite**

Run `tests/test-browser-mcp-config.py` and `tests/test-live-browser-operation-safety.py` under Debian WSL. At this checkpoint the live safety suite may fail only on assertions that still describe the old external handler; record those exact expected failures for Task 5 rather than weakening the builder.

- [ ] **Step 5: Commit the strict config producer**

```powershell
git add tests/browser-mcp-config.py tests/test-browser-mcp-config.py
git commit -m "test: generate phase-bound browser permission configs"
```

---

### Task 4: Ordered Allow/Deny Evidence Reduction

**Files:**
- Modify: `tests/browser-workflow-evidence.mjs`
- Modify: `tests/browser_operations_live.py`
- Modify: `tests/test-live-browser-operation-safety.py`

**Interfaces:**
- Consumes: allow stream, deny stream, allow signal, deny signal, the two expected workflow sessions, run nonce, and structural before/after fixture observations.
- Produces: ordered samples with `permissionPhase`; final aggregate field `permission:{mode:'synthetic-deterministic',allow:'completed',deny:'completed',callCount:2}`; `ACTIVE` only when allow validated and deny proved no effect.

- [ ] **Step 1: Add failing evidence tests with complete real stream envelopes**

Extend the existing stream fixture builders rather than asserting parser internals. Add one valid allow stream and one valid deny stream. The deny stream must contain one Bash tool use, the exact ordered PreToolUse `ask` hook lifecycle, the correlated permission-denied tool result, no PostToolUse or PostToolUseFailure for the runner, no runner JSON result, and one same-session SDK success terminal after the model stops.

Assert the aggregate literal:

```python
self.assertEqual(result["permission"], {
    "mode": "synthetic-deterministic",
    "allow": "completed",
    "deny": "completed",
    "callCount": 2,
})
self.assertEqual(result["capabilityState"], "ACTIVE")
self.assertEqual(result["workflow"]["outcome"], "WORKFLOW_VALIDATED")
```

Add named rejection tests for swapped phases, same session, same operation, same fingerprint, allow signal reporting deny, deny signal reporting allow, unmatched fingerprint, duplicate permission call, deny followed by PostToolUse, deny followed by runner output, later Bash/MCP activity, changed fixture state after deny, missing state observation, malformed signal, signal link, and any raw command/canary in retained output.

- [ ] **Step 2: Run the evidence tests and observe RED**

Run:

```powershell
python tests/test-live-browser-operation-safety.py
```

Expected: FAIL because the aggregate has no `permission` field and treats every workflow sample as requiring `WORKFLOW_VALIDATED`.

- [ ] **Step 3: Extend workflow evidence and parsers minimally**

Add `invocationFingerprint` to `browser-workflow-evidence.mjs` output and its exact Python field set. Add a strict loader for Task 2 signals. Preserve the existing allow evaluator and add:

```python
def evaluate_denied_stream(
    path: Path, canary: str, signal_path: Path,
    expected_nonce: str, expected_session: str,
) -> dict[str, Any]:
    ...
```

The denied sample uses route class `workflow-denied`, outcome `NOT_OBSERVED`, and exactly one workflow session. Extend `ROUTE_CLASSES`, aggregate schema validation, trusted workflow-session correlation, and self-test fixtures. Promote to `ACTIVE` only for exactly one completed allow sample followed by exactly one coherent denied sample whose independent fixture observation is unchanged.

- [ ] **Step 4: Run parser self-test, safety tests, and content validation**

Run Windows portable tests and Debian WSL full cases. Run `bash tests/live-browser-operations-smoke.sh --self-test` and `python tests/validate-content.py`.

Expected: all pass; self-test emits no permission input, command, or workflow token.

- [ ] **Step 5: Commit evidence reduction**

```powershell
git add tests/browser-workflow-evidence.mjs tests/browser_operations_live.py tests/test-live-browser-operation-safety.py
git commit -m "test: require ordered allow and deny browser evidence"
```

---

### Task 5: Wire the Disposable Handler into the Live Harness

**Files:**
- Modify: `tests/live-browser-operations-smoke.sh`
- Modify: `tests/test-live-browser-operation-safety.py`
- Modify: `tests/browser-fixture/server.mjs`
- Modify: `tests/browser-operations/fixture-server.test.mjs`
- Modify: `tests/test-nori-staging.py`
- Modify: `tests/test-nori-archive.py`
- Modify: `tests/validate-package.sh`
- Modify: `docs/superpowers/plans/2026-09-02-p0-04b-one-shot-workflow.md`

**Interfaces:**
- Consumes: Task 1-4 artifacts, detected existing browser runtime, and the fixture's bounded structural state endpoint.
- Produces: two ordered Claude workflow invocations, content-free fixture snapshots, and no external permission configuration requirement.

- [ ] **Step 1: Write failing harness and fixture behavior tests**

Change safety tests to execute preflight/self-test behavior and inspect generated configs through Task 3 tests, not merely grep new source. Retain static assertions only for destructive cleanup boundaries that cannot safely be executed on Windows. Extend the staging and archive tests to build the real artifacts and assert that neither `browser-permission-mcp.py` nor `browser-permission-verifier.mjs` is present anywhere in their file inventories.

Extend the fixture with a content-free `/api/summary` response containing exactly:

```json
{"routerEnabled":false,"revision":1}
```

for the post-allow state. The fixture test must prove initial `{true,0}`, successful change `{false,1}`, successful rollback `{true,0}`, authentication protection on mutable routes, and no credential/canary fields in the summary.

Add harness tests proving old `P004B_PERMISSION_MCP_CONFIG`, `P004B_PERMISSION_PROMPT_TOOL`, and variable request-count inputs are rejected or ignored; expected authorization is exactly 6/40; measurement commands omit `--permission-prompt-tool`; allow and deny commands each use their own strict config and the fixed internal tool name.

- [ ] **Step 2: Run focused tests and observe RED**

Run fixture tests, MCP config tests, live safety tests, parser self-test, and `bash -n` under Debian WSL.

Expected: failures name the missing summary endpoint and old external-handler harness path.

- [ ] **Step 3: Implement the parent wiring**

Make these ordered harness changes:

1. Hard-code `EXPECTED_TOP_LEVEL_INVOCATIONS=6` and `EXPECTED_MAX_MODEL_TURNS=40`; retain exact authorization environment checks and remove `REQUEST_COUNT`.
2. Copy the handler and verifier into `$PROJECT/.claude`, mode `0500`, after Nori installation; verify the staging tree and installed skill roots do not contain them.
3. Start the browser fixture before MCP config creation, allocate distinct allow and deny UUID sessions, and call Task 3 once.
4. Use `empty-mcp.json` for context probes and ordinary measurement stages, and `measurement-mcp.json` only for context MCP discovery/use. Remove `--permission-prompt-tool` from measurement commands.
5. Run the allow prompt once with `allow-mcp.json`, fixed internal permission tool, exact allow session, synthetic password/TOTP, disabled-state reference, 120-second request cap, Bash-only model tools, and no retry.
6. Reduce the allow stream, fetch `/api/summary`, and require `{routerEnabled:false,revision:1}`.
7. Run the deny prompt once with `deny-mcp.json`, exact deny session, rollback objective, Bash-only model tools, and no retry.
8. Reduce the deny stream, fetch `/api/summary` again, and require the same `{routerEnabled:false,revision:1}`.
9. Delete configs, claims, signals, prompts, streams, transcripts, fixture snapshots, and session stores before building the aggregate.

The denied prompt must say to attempt exactly one rollback workflow and stop after denial. It must not invite an alternative command, browser route, or retry.

- [ ] **Step 4: Update the superseded Task 4 plan text and run focused WSL gates**

Amend only the active-runtime handler paragraphs in the older plan and link the approved 2026-09-17 specification and this plan. Run:

```bash
bash -n tests/live-browser-operations-smoke.sh
node --test tests/browser-permission-verifier.test.mjs
python3 -m unittest tests/test-browser-permission-mcp.py tests/test-browser-mcp-config.py tests/test-live-browser-operation-safety.py
bash tests/live-browser-operations-smoke.sh --self-test
```

Expected: all pass without a provider request.

- [ ] **Step 5: Run the existing real-browser matrix and commit**

Run the 37-scenario opt-in loopback matrix against the existing Playwright `1.62.1` package and cached Chromium. Confirm all 40 matrix records still pass and no handler artifact appears in staging.

Commit:

```powershell
git add tests/live-browser-operations-smoke.sh tests/test-live-browser-operation-safety.py tests/browser-fixture/server.mjs tests/browser-operations/fixture-server.test.mjs tests/test-nori-staging.py tests/test-nori-archive.py tests/validate-package.sh docs/superpowers/plans/2026-09-02-p0-04b-one-shot-workflow.md
git commit -m "test: automate bounded browser permission decisions"
```

---

### Task 6: Provider-Free Gates, Live Acceptance, and Delivery Evidence

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/architecture/ADR-010-browser-automation-boundary.md`
- Modify: `docs/superpowers/specs/2026-08-31-p0-04b-browser-automation-design.md`
- Modify: `docs/superpowers/specs/2026-09-17-p0-04b-disposable-permission-handler-design.md`
- Modify: `references/browser-operations.md`
- Modify: `tests/validation-notes.md`
- Modify after merge only: `C:\projects\senior-infra-ops-analyst\TODO-AI-FIRST.md`

**Interfaces:**
- Consumes: all deterministic implementation evidence and one separately authorized authenticated run.
- Produces: truthful release documentation, independent review verdict, CI/Security evidence, PR, and post-merge TODO completion.

- [ ] **Step 1: Update documentation claims before live execution**

Document the implemented test-only boundary, exact 6/40 budget, allow/deny semantics, production native prompt, no staging, no retry, and pending authenticated result. Do not claim `ACTIVE`, completed authentication, mutation, or denial until observed.

- [ ] **Step 2: Run every provider-free gate**

Run Windows portable suites, Debian WSL focused suites, `git diff --check`, `python tests/validate-content.py`, `python tests/test-architecture-docs.py`, staging/archive tests, provider-free preflight with the existing Playwright paths, and the complete Debian WSL package gate:

```bash
env PATH=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin bash tests/validate-package.sh
```

Expected: package validation passes; preflight remains `AVAILABLE_RECOGNIZED`; no authenticated provider request occurs.

- [ ] **Step 3: Request independent security and spec review**

Require review of verifier/parser reuse, first-call confusion, allow/deny ordering, fingerprint correlation, input preservation, generic denial, signal/claim safety, MCP separation, fixture-state independence, cleanup, staging exclusion, evidence truthfulness, and production/native-prompt separation. Resolve every P0/P1/P2 with a fresh RED/GREEN cycle and rerun affected gates.

- [ ] **Step 4: Commit the provider-free implementation state**

```powershell
git add CHANGELOG.md docs/architecture/ADR-010-browser-automation-boundary.md docs/superpowers/specs/2026-08-31-p0-04b-browser-automation-design.md docs/superpowers/specs/2026-09-17-p0-04b-disposable-permission-handler-design.md references/browser-operations.md tests/validation-notes.md
git commit -m "docs: record automated browser permission boundary"
```

- [x] **Step 5: Obtain fresh exact authorization and run once**

Before execution, obtain explicit authorization for exactly:

- provider `https://api.deepseek.com/anthropic`;
- currently configured model, observed structurally at execution time;
- six authenticated top-level Claude Code invocations;
- at most 40 model turns;
- two workflow requests with 120 seconds each and total limit 1,800 seconds;
- only synthetic P0-04B prompts and loopback browser target;
- deterministic allow then deny, no human interaction and no automatic retry;
- raw prompt, stream, permission, session, and fixture evidence deleted before the content-free aggregate.

Run only after that authorization:

```bash
env PATH=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin:/home/marco/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  P004B_LIVE_AUTHORIZED=1 \
  P004B_LIVE_ACK=I_ACKNOWLEDGE_BOUNDED_SYNTHETIC_BROWSER_PROBES \
  P004B_AUTHORIZED_TOP_LEVEL_INVOCATIONS=6 \
  P004B_AUTHORIZED_MAX_MODEL_TURNS=40 \
  P004B_AUTHORIZED_PROVIDER_ENDPOINT=https://api.deepseek.com/anthropic \
  P004B_PER_REQUEST_TIMEOUT_SECONDS=120 \
  P004B_TOTAL_TIMEOUT_SECONDS=1800 \
  P004B_BROWSER_NODE_MODULES=/home/marco/.npm/_npx/e41f203b7505f1fb/node_modules \
  P004B_PLAYWRIGHT_BROWSERS_PATH=/home/marco/.cache/ms-playwright \
  bash tests/live-browser-operations-smoke.sh --run-live
```

Do not repeat an inconclusive or failed result. Record only the bounded aggregate.

The endpoint-bound attempt on commit
`eb8fcdb02c6a82e9321df18563ab6f37dba982db` stopped in the first
provider-backed `skill` measurement with `CLAUDE_PROCESS_FAILED`; it produced
no trusted sample or aggregate, did not reach either browser workflow, cleaned
up the disposable root, and was not repeated. Acceptance remains pending.

A later authorized attempt on commit
`1a40d37849dc870da84c948f3f45451372c3076b` stopped at the same first `skill`
measurement with `CLAUDE_PROCESS_FAILED_EXIT_1_STREAM_EMPTY` and was not
repeated. A loopback diagnostic without real credentials isolated the cause to the
Claude Code `2.1.281` command contract: `stream-json` requires verbose mode.
The corrected harness now supplies `--verbose` on every structured live
invocation. This provider-free diagnosis and correction do not satisfy live
acceptance; another run requires fresh authorization bound to the corrected
commit.

The operator then authorized one run on corrected commit
`575fd621b464ab431c20664590c9812f16f0a3bc`. It passed the four trusted
measurement invocations and reached the synthetic `allow` workflow. That fifth
top-level invocation exceeded its deadline and the harness emitted
`CLAUDE_TIMEOUT`; the `deny` invocation was not launched, no aggregate was
produced, cleanup was verified, and no retry occurred. The result is
inconclusive and does not satisfy live acceptance.

Provider-free follow-up identified a diagnostic gap: timeout classification
discarded the already implemented structural stream state. The reducer now
retains only one closed timeout fingerprint (`EMPTY`, `SYSTEM`, `ASSISTANT`,
`RESULT`, `RESULT_ERROR`, `INVALID`, or `OTHER`) and still deletes every raw
artifact before blocking. This cannot recover the deleted stream from the
earlier attempt or justify another authenticated run.

The operator authorized one further exact run on commit
`13324e9c74532b0653755b914c6bda6d490afd4c`. The four trusted measurement
invocations completed and the fifth top-level invocation entered the synthetic
`allow` workflow, then exited nonzero. The harness emitted only
`CLAUDE_EVIDENCE_REJECTED`. Because raw evidence was deleted, retained evidence
cannot distinguish rejection of diagnostic input from a parser failure,
non-allowlisted reducer output, or immediate cleanup failure. No narrower
failure or timeout classification is supported. The `deny` invocation was not
launched, no aggregate was produced, the run was not repeated, and cleanup
removed the disposable root and external wrapper. Live acceptance remains
pending and any further provider-backed attempt requires a new exact
authorization.

An approved provider-free follow-up replaced future generic rejection with four
closed provenance codes: rejected diagnostic input, reducer execution failure,
non-allowlisted reducer output, and immediate cleanup failure. The existing raw
evidence deletion, 64 KiB bound, no-retry rule, authorization boundary, and live
acceptance criteria remain unchanged. This does not retroactively classify the
deleted evidence from the earlier attempt. The RED focused run failed on the
old generic result and missing provenance self-tests; the GREEN run passed all
84 tests, and the direct harness self-test exercised all four paths without a
provider request. The complete provider-free Debian WSL package gate then ended
with `package validation passed`.

On 2026-09-30, the exact authorized attempt on commit
`5b540c12bfd58c6bcb48445f3aa31a3c1a3489b5` used the existing WSL Claude Code
`2.1.284`. All four reduced measurement sample filenames were observed. The
harness subsequently exited with status 2 without a retained failure category
or final aggregate. The failure location and either workflow's invocation or
outcome remain unproven. Cleanup removed `/tmp/p0-04b-browser.Cpmw3x`, the
external wrapper was deleted, and no retry occurred. Acceptance remains pending;
another authenticated attempt requires fresh authorization.

- [x] **Step 6: Record observed evidence and rerun final gates**

If the run passes, update validation notes and release documents with the exact content-free aggregate, observed runtime labels, decision order, cleanup, and limitations. If it is blocked or inconclusive, record that outcome without claiming acceptance. Rerun content, architecture, focused, and complete package gates after documentation changes.

- [ ] **Step 7: Final review, commit, push, and PR**

Request a final independent review. Commit factual live evidence, push `p0-04b-browser-automation`, create or update the PR, and wait for CI and Security. Do not merge without explicit operator instruction.

Suggested evidence commit:

```powershell
git add CHANGELOG.md docs/architecture/ADR-010-browser-automation-boundary.md docs/superpowers/specs/2026-08-31-p0-04b-browser-automation-design.md docs/superpowers/specs/2026-09-17-p0-04b-disposable-permission-handler-design.md references/browser-operations.md tests/validation-notes.md
git commit -m "test: record live browser allow and deny evidence"
```

- [ ] **Step 8: Post-merge verification and definitive TODO**

Only after merge to `main`, synchronize the real repository, run the complete package gate on merged `main`, and then update the nonversioned definitive TODO to mark P0-04B complete with merge, CI/Security, live evidence, and post-merge validation references.
