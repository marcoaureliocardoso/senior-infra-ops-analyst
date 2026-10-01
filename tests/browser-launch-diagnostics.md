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

Python's official [selectors](https://docs.python.org/3/library/selectors.html),
[subprocess](https://docs.python.org/3/library/subprocess.html), and
[tempfile](https://docs.python.org/3/library/tempfile.html) documentation informs
pipe multiplexing, new-session supervision, and private-root creation. POSIX
pipes are intentional; native Windows pipe supervision is not claimed.

## Provider-free validation

```bash
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
