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

This is a diagnostic-only filter, not an aggregate parser. A future authorized
launcher must validate a final aggregate separately with the existing strict
P0-04B parser; unknown JSON must not be forwarded by this reducer. A repeated
run still requires fresh operator authorization bound to its final commit.

## Provider-free validation

```bash
python3 tests/test-browser-launch-diagnostics.py
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
