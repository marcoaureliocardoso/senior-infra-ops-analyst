# Browser launch diagnostic boundary

`browser_launch_diagnostics.py` is a test-only, credential-free reducer for
external P0-04B launcher diagnostics. It does not execute Claude Code, Nori,
browser actions, authentication, or provider requests, and is not included in
the Nori skillset. Import `reduce_line(bytes)` in an external launcher rather
than writing another permissive stdout/stderr filter. No operator settings
are read or changed by this module.

## Contract

- Only exact repository-owned diagnostic templates are classified. Context
  probes, native status-line evidence, PTY fallback, measurement failures,
  workflow requests, rejected workflow evidence, and harness exit/cleanup
  reports remain distinct.
- Output fields are closed categories, closed reason codes, closed probe,
  measurement, phase and source labels, or exit numbers from 1 through 255.
  A failed numeric context probe may additionally report at most 16 ordered
  stage/outcome pairs as `CONTEXT_PHASES / PTY_PHASES_REPORTED`. The closed
  startup/context/exit vocabulary, unique stages and terminal failure are
  required; arbitrary fields or labels reject the entire sequence.
  Unrecognized lines, labels, controls, invalid UTF-8, arbitrary JSON, and
  oversized lines become `UNKNOWN / DIAGNOSTIC_SUPPRESSED` without content.
- The unsettled-top-level-await warning yields only a warning classification.
  It does not identify the originating process, the failed stage, or cause.
- `cleanupReported`, `stageReported`, `exitReported`, and `capabilityReported`
  describe claims in observed output. They are not independently verified
  facts. A matching line can be forged. Neither a code nor filter exit 0
  establishes guard coverage, permission, provider receipt, acceptance, or
  authorization to repeat an operation.
- The module accepts neither paths nor credentials as arguments, never opens
  files or sockets, and never stores raw input. Line data remains transient in
  memory. Output contains no prompt, page, transcript, stream, canary, session
  identifier, private path, provider/model string, or credential value.

The stdin CLI is intended for offline/synthetic checks. It caps each line at
4,096 payload bytes, total input at 1 MiB, and distinct output at 256 records.
It discards an entire overlong line, not just the leading chunk, and suppresses
duplicate sanitized records. Limits return exit 2 and a closed `FILTER` code.
Exit 0 means filtering finished, not that a harness passed. The caller owns
wall-clock limits, process termination, and independent cleanup validation.
Do not pipe an authenticated run directly into this CLI: limit termination
can close the pipe. Use bounded in-memory line classification under the
launcher's existing process and output budgets instead.

This is a diagnostic-only filter, not an aggregate parser. The test-only
`browser_disposable_launcher.py` imports it while separately validating a final
aggregate with the existing strict P0-04B parser. Unknown JSON is never forwarded
by the reducer. A repeated live run still requires fresh operator authorization
bound to its final commit; the launcher's CLI does not implement a live route.

## Disposable launcher integration

The POSIX/WSL launcher starts exactly one child, drains stdout and stderr
concurrently with `DefaultSelector`, and retains at most 4,096 payload bytes per
line, 1 MiB of total input, and 256 distinct sanitized diagnostic records. Raw
streams stay in bounded transient memory and are never written by the launcher.
Overlong lines are discarded whole. Output/record exhaustion, timeout, signals,
launch failure, and child failure return distinct closed codes without retries.
The preflight deadline is 120 seconds; process-group termination has a bounded
additional grace period. The internal supervisor accepts no deadline above
1,800 seconds and cannot increase the output budgets.

Only one bounded stdout JSON object can supply `aggregateReported`. Duplicate
keys, nonfinite constants, malformed encoding, repeated aggregates, pending
cleanup, and incoherent passing claims are rejected. The existing strict
aggregate validator checks its shape and consistency. Runtime strings are
omitted, and reasons other than the three closed preflight codes are suppressed:
a regex-constrained arbitrary label is not safe output. `STREAM_COMPLETE` means
successful process completion and a structurally valid reported aggregate,
not authenticated acceptance or independent proof of its assertions.

An owned private root receives the child's `TMPDIR`. The supervisor terminates
the process group and closes both pipes before removing that exact root with
symlink-resistant cleanup. A replaced root is not followed or reported clean.
`launcherCleanup` is independent of the aggregate's reported `cleanup` field.
Children that escape the process group or an uncatchable launcher termination
are not claimed covered; this is supervision of the trusted repository harness,
not a sandbox for adversarial executables. No production settings are changed.

The public CLI accepts only `--preflight`. Its child environment contains only
explicit HOME/PATH and optional existing browser module/cache paths; credentials,
provider/model variables, settings paths, shell startup hooks, and authorization
flags are not inherited. It reads no operator settings and installs no packages.
The existing preflight opens and closes an empty browser and directly checks a
synthetic fail-closed guard denial; it does not execute Claude/Nori, authenticate,
navigate, prove native hook execution, or perform live acceptance. Its runtime
labels are therefore not verified CLI/provider/model observations.

```bash
# Select the already-installed runtimes; no credentials or live flags.
env -i HOME=/home/operator PATH=/path/to/node/bin:/usr/bin:/bin \
  P004B_BROWSER_NODE_MODULES=/path/to/existing/node_modules \
  P004B_PLAYWRIGHT_BROWSERS_PATH=/path/to/existing/browser-cache \
  python3 tests/browser_disposable_launcher.py --preflight
```

`--run-live` fails closed even if authorization-shaped environment flags exist.
The internal `supervise` function is process plumbing, not an authorization
mechanism. Any future external live caller still needs a fresh operator grant
for the exact final commit, independently protected credential transport, and
the unchanged endpoint, six-invocation/40-turn/120-second/1,800-second limits.
Neither a diagnostic nor a reported aggregate can grant or renew consent.
No deleted historical diagnostic can be reconstructed by this integration.

### Native session persistence compatibility

Live measurement stages use native `--resume`, so an acceptance caller must
omit `CLAUDE_CODE_SKIP_PROMPT_HISTORY=1`. The official
[environment-variable reference](https://code.claude.com/docs/en/env-vars)
states that this option also suppresses session transcripts and makes those
sessions unavailable to resume/continue. Prompt history and native transcripts
may exist only inside the already-owned private disposable HOME/config during
the bounded synthetic test; existing cleanup removes them before aggregation.
This is temporary native state, never a retained evidence artifact.

The live harness rejects an enabled or unrecognized explicit value before
resolving the source root, reading settings, creating private state or starting
dependencies. Absent/empty values and exactly `0`, `false`, `no` or `off`
(case-insensitive words) are compatible. Whitespace and other spellings are not
silently normalized or overridden. The fixed message reduces to
`CONTEXT / SESSION_PERSISTENCE_REQUIRED`, without the input value or any path.
This is an explicit caller-environment gate, not a proof of every effective
runtime/managed setting or a grant to launch. Later native/acceptance checks
still fail closed.

Self-test/preflight and the separate non-resuming local dispatch diagnostic
retain their behavior. Production settings and the operator's environment are
not changed. The existing resume sequence, workflow `--no-session-persistence`,
exact authorization bindings, six-invocation/40-turn/120-second/1,800-second
budgets, raw-evidence cleanup and no-repeat rule are preserved. Correcting the
external caller does not enable a public live route or authorize another run.

Python's official [selectors](https://docs.python.org/3/library/selectors.html),
[subprocess](https://docs.python.org/3/library/subprocess.html), and
[tempfile](https://docs.python.org/3/library/tempfile.html) documentation informs
pipe multiplexing, new-session supervision, and private-root creation. POSIX
pipes are intentional; native Windows pipe supervision is not claimed.

## Provider-free validation

Numeric PTY inspection uses collapsed `/context`, not per-item expansion.
The required native header, coherent numeric percentage and successful exit
are still mandatory. Installed-profile comparisons exposed format/viewport
sensitivity in the expanded view at the bounded 40-row geometry; enlarging the
terminal is not the remedy. Both forms are documented in the official
[command reference](https://code.claude.com/docs/en/commands). This choice adds
no fallback retry, cache provisioning, provider/model assumption or acceptance
relaxation; it does not require an absolute context-window size.

### Optional acceptance-only native startup decision

Interactive Claude Code requires a one-time approval for `ANTHROPIC_API_KEY`,
whereas print mode uses it directly; this is documented in the official
[environment-variable reference](https://code.claude.com/docs/en/env-vars).
Changing credential transport to avoid that decision is not this test's remedy.

Only a fresh operator grant covering both the bounded authenticated run and
one native API-key confirmation permits the trusted caller to set:

```bash
P004B_STARTUP_API_KEY_APPROVAL=I_ACKNOWLEDGE_ONE_NATIVE_API_KEY_CONFIRMATION
P004B_AUTHORIZED_COMMIT=<exact-final-40-character-commit>
```

These flags and the resulting claim are bookkeeping, never proof of human
consent. Existing live authorization, exact endpoint and fixed budgets still
apply. The public disposable launcher still rejects `--run-live`. Its internal
supervisor cannot grant authorization or read credentials for the caller.
Self-test/preflight reject the opt-in; absent opt-in retains fail-closed PTY
behavior. A missing, changed, dirty or untracked source checkout rejects the
opt-in before dependencies run. Linux Git handles native checkouts; the installed
Windows Git plus `wslpath` handles Windows-linked WSL worktrees, or blocks if that
bridge is unavailable. Neither route configures Git globally or accesses GitHub.
Git reads disable optional index writes and filesystem-monitor helpers. The WSL
bridge explicitly forwards only Git's system/global configuration-isolation
variables through the official [WSLENV interface](https://learn.microsoft.com/en-us/windows/wsl/interop).
It does not rely on Linux HOME being inherited by a Windows executable.

The shell pins live `CLAUDE_CONFIG_DIR` to the disposable HOME after remembering
the existing source-settings path. Only `main-before`, with a fresh session and
no agent/resume flags, creates an owner-only claim. The dedicated context driver
rechecks the clean commit and exact command, run nonce, native session, endpoint,
canonical executable and private configuration root. It consumes the claim
before launching and creates an exclusive spent marker, so recreating a claim
cannot replay it. The 120-second expiry bounds the selector decision, not an
increase to any workflow deadline. The parent still owns source immutability
during execution; this is not a sandbox against malicious same-user processes.

After the API-key heading is fully drawn, only the closed two-option Yes/No
block (numbered or unnumbered) with exactly one selection is recognized. The
controller selects the recognized Yes option and confirms once. Unknown or
ambiguous content consumes the decision without input; native login, a repeated
selector or any selector after prompt readiness stops the probe. Prompt readiness
also revokes an unused decision. The shared PTY CLI has no enabling option.
The structural `api_key_approval` event is optional startup context evidence,
not browser allow/deny, credential identity, native hook proof or provider receipt.

An unused decision must not restore pre-transition output into readiness checks.
The controller preserves the caller's byte boundary and, if confirmation adds
output, also requires the post-confirmation boundary. Numeric context startup
recognizes a fresh input row, rejecting known theme/trust menus, numbered
selectors, unrecognized unnumbered option rows and context-status text alone.
The current rendered screen must also have left a recognized theme/trust menu;
a partial blank-chevron redraw while its heading remains visible is insufficient.
Readiness is rechecked after the final quiet settling interval.
Unknown prompt formats stop safely; this is not general terminal emulation.

On numeric-probe failure, `--pty-failure-phases` securely reads one bounded
regular no-follow event file (64 KiB, at most 16 records, unique JSON keys).
Only allowlisted stage/outcome pairs leave the reader; numeric fields are
validated but omitted. Malformed, linked, nonregular, oversized, incomplete
or unknown evidence becomes `unavailable`, with no sequence emitted. The
shell removes raw evidence and the complete owned root, verifies absence and
the sticky cleanup result, then emits the closed phase template on stderr
before the existing leaf failure code. Cleanup failure emits no phase report.
The reducer independently revalidates the template; `cleanupReported` remains
an observed claim, not proof or permission. This diagnostic does not enter the
acceptance aggregate, recover deleted history or authorize another attempt.

No credential, approved-key cache or key hash is copied into the claim or final
evidence. Claude may remember its own decision only inside the disposable native
configuration. The native HOME/config/cache and claim/spent directory are
removed before sidecar construction and aggregate computation, alongside the
earlier raw PTY deletion. Structured measurement files remain until computation;
the entire root is removed before final aggregate emission. This adds no production handler,
permission bypass, retry, authenticated invocation or model turn.

```bash
python3 tests/test-browser-startup-approval.py
python3 tests/test-browser-context-driver.py
python3 tests/test-browser-launch-diagnostics.py
python3 tests/test-browser-disposable-launcher.py
bash tests/live-browser-operations-smoke.sh --self-test
bash tests/validate-package.sh
```

Tests cover the real CLI, a real unauthorized harness stop before runtime
initialization, and the real PTY event reducer followed by line classification.
They also exercise context labels, structural failure fingerprints, workflow
sources, reported cleanup/exit, invalid content, deduplication, and input/output
budgets. No live authorization flags or credentials are needed.

The deleted diagnostics from the 2026-10-01 attempt remain unrecoverable. This
change does not reclassify that attempt or the earlier canary exposure, alter
provider endpoint/model policy, relax acceptance, add retries, or change the
six-invocation/40-turn/120-second/1,800-second live authorization limits.

## Explicit test-only headless terminal runtime

P0-04B context probes select `--terminal-engine headless --terminal-node ABS
--terminal-module-root ABS` before the native command separator. The default
shared driver remains legacy; headless is valid only for `dialogue=context`.
No fallback or module search is permitted. The live caller requires
`P004B_TERMINAL_NODE` and `P004B_TERMINAL_MODULE_ROOT`, validates the immutable
source grant first when applicable, then preflights the terminal before private
state, operator settings, native startup or one-use claim consumption.

Provision once with `tests/provision-terminal-runtime.py --target ABS --npm ABS
--node ABS`. The destination must be new and external to the checkout. The
private lock is copied and installed with clean npm configuration and disabled
lifecycle scripts. Existing targets are not overwritten; a failed partial target
remains owned by that attempt. Reuse a verified retained target through explicit
paths rather than reinstalling automatically. CI provisioning is a separate
credential-free step. No runtime dependency enters Nori staging/installation.

The passive Node engine reports bounded active-buffer cells/cursor state over
private pipes. Python validates framing/schema, fresh current input and exact
numeric context; snapshots are not consent. No raw screen or helper error is
public. `terminal_preflight`, `terminal_state` and `terminal_cleanup` are closed
failure stages, never acceptance evidence. Terminal replies are counted and
discarded. Cleanup errors override apparent native success.

The optional offline CLI accepts only `--audit-isolation` or `--run-offline`,
plus explicit `--source`, `--node`, `--module-root` and, for controls, `--claude`.
It requires Bubblewrap user/PID/network isolation with capabilities dropped,
operator paths hidden and loopback-only networking before native startup. No
real settings, credential reader, live mode or automatic retry exists. Temporary
synthetic key/history, screens and streams are removed before its closed report.
The package suite runs only safety tests, never the native control. A missing
Bubblewrap test capability is an explicit skip, not proof of isolation; the
offline control itself blocks. The 2026-10-07 native control was inconclusive;
see `tests/validation-notes.md`. No paid retry is authorized by this setup.

### Managed cancellation of selected test processes

The selected public/dedicated context entrypoints, terminal preflight and offline
launcher install scoped cooperative SIGTERM/SIGHUP cancellation before helper
creation. Signals set a flag; bounded checkpoints run only after process-handle
publication and before claim consumption/input. Existing handlers are restored;
unrestorable handlers or missing Linux ownership interfaces block startup.

A private release pipe gates a per-target supervisor; no target starts before
its owner publishes it. The supervisor's subreaper scope has only that one
target, so later orphan adoptions belong to the same family. Exact pidfds,
bounded metadata and selective reaping avoid a host-wide process kill. Native
argv/environment/stdio and one-use claims remain unchanged. Failed ownership
or cleanup cannot become acceptance. Neither scope masks SIGKILL nor promises
recovery from interpreter/host failure.

The helper `tests/terminal_cancellation.py` and its internal supervisor mode
are test-only, excluded from Nori staging, and never authorization interfaces.
The offline namespace mounts it read-only; no implicit install or live mode
was added. Provider-free fixtures verify both signal families at startup, IPC,
PTY, pre-claim source waits and namespace disposal. Real native SDK/resume
acceptance remains pending; these fixes authorize no repetition.
