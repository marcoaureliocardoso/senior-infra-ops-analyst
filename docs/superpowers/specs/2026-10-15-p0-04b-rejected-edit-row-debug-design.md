# P0-04B rejected edit-row development diagnostic

Status: architectural direction and written specification operator-approved.
The implementation plan awaits operator review and execution-method selection.
Not implemented. No native execution is authorized by specification approval.
Source baseline: `19173557b54778fb944b8b764223b58738ee8688`.

## Intent and evidence

Identify the exact other row responsible for an early normalized edit rejection,
so that command suggestions can be distinguished from other command-shaped text.
This is a development-only diagnostic, not a new acceptance rule. Normal use
continues to retain no terminal content. Success means either one properly bound,
bounded, sanitized row after verified disposal, or an honest content-free omission.

The single authorized offline attempt on the baseline observed Claude Code
2.1.300 and stopped in the first text-turn/before dialogue after 5.6175526 seconds,
exit 2. Its frozen result was INPUT_PROBE_REVOKED, EDIT_PENDING,
NORMALIZED_ELIGIBILITY, eight command bytes and zero Enter bytes, with
UNSUPPORTED_ROW / OTHER_CAPTURED_ROW / UNRECOGNIZED_SHAPE. No gateway message,
SDK turn, after dialogue or skill-turn executed. Both leaders were reaped and
case/outer disposable roots were absent. That grant is consumed.

The aggregate and read-only investigation remain outside Git in the test-owned
`.review-runtime/p004b-terminal-state` directory:

- `p004b-offline-1917355-structural-result.json`;
- `normalized-eligibility-investigation-1917355.md`;
- `investigate-normalized-1917355.py`.

Sixteen pure fixtures passed. Selected command suggestions above/below input and
another command-prefixed row with extra text match the complete native aggregate.
Static inspection of the installed artifact confirms that its suggestion selector
and the input prompt share the pointer glyph. Autocomplete remains the leading
hypothesis, not the proven identity of the deleted native row. Runtime labels and
static offsets are evidence, never product pins or parser fingerprints.

This supplements the implemented
[normalized subreason observer](2026-10-15-p0-04b-normalized-eligibility-diagnostics-design.md).
The current `--debug-context` capture requires numeric context and a later
INPUT_PROBE_INELIGIBLE rejection. It deliberately omits this early failure.
Do not broaden that flag or pretend it already covers this boundary.

## Decision and alternatives

Select a separate opt-in rejected-row diagnostic. Capture no new frame file and
no other row. A sealed first-failure observation carries the exact rejected row
temporarily in memory, separately from the existing content-free journal.

More structural enums were not selected: distinct native conditions can produce
the same closed result. A complete frame was not selected: it collects unrelated
content and creates additional artifact/retention work. Ignoring suggestions or
using READY in place of strict eligibility was not selected: either would alter
input authority without proving the native cause.

## Activation and exact capture boundary

Reserve `--debug-context-edit` for the offline launcher only. It is explicit,
off by default and mutually exclusive with `--debug-context`. Reject it for
isolation-audit mode and all live/provider-backed routes. No environment fallback,
operator settings change, default activation, new dependency or installed-package
inclusion is permitted. The old flag retains its present semantics.

A capture is eligible only when all of the following are proven together:

1. The explicit development option belongs to this invocation and the existing
   offline namespace proves network isolation, hidden operator state and dropped
   capabilities. Synthetic-only authentication and disposable history remain in
   effect; no operator credential/configuration mount is added.
2. The existing owned context command reached its first actual rejecting ordered
   assessment. Its original error is INPUT_PROBE_REVOKED and its paired frozen
   base is EDIT_PENDING / NORMALIZED_ELIGIBILITY / 8 command bytes / 0 Enter bytes.
3. Its actual detail is exactly UNSUPPORTED_ROW / OTHER_CAPTURED_ROW /
   UNRECOGNIZED_SHAPE. Other phases, reasons, row relations and causes are omitted,
   not opportunistically captured.
4. A private observation binds the same exception, command/journal, controller,
   terminal, run, transition and immutable rejecting snapshot. The row comes from
   the same ordered evaluator's first rejected index, not a later scan or guess.

Preserve one ordered assessment and its original comparison/short-circuit order.
Propagate the evaluator's already available private rejected index without
expanding the public serialized assessment or recomputing eligibility in a catch.
Normalization changes only the owned input row; the eligible rejected row must
be a different, unchanged row in the original snapshot.

## Observation lifecycle and provenance

The first failure seals a one-shot observation before ordinary revocation; only
an eligible first failure may carry a row. A base-only or omitted first failure
can never acquire content from a later failure.
Later catches, cleanup and dialogues cannot enrich, replace or reuse it. With
the option disabled, retain no new row, snapshot or content-bearing attachment.
Keep the existing base-only and paired enum projection contracts unchanged.

The debug consumer validates private object identity and original binding, not
shape-valid dictionaries or arbitrary error attributes. Forged, copied, replaced,
foreign, closed, expired or snapshot-substituted observations yield omission.
Do not poll the terminal, read a new frame, rerun the evaluator, renew a lifetime,
issue a scope, or revive revoked input to obtain a diagnostic.

After preparation, release private content-bearing bindings on success, omission,
exception, cancellation and cleanup. These are trusted-process provenance rules,
not a sandbox against arbitrary same-process Python execution. Releasing Python
references is logical disposal, not guaranteed physical memory zeroization.

## Content minimization, sanitization and output

Use only the existing bounded in-memory snapshot. Scan its original cells with
the existing conservative sensitive-content checks before preparing an excerpt;
do not persist or export the scan input. Authentication/trust UI, credential-like,
canary-like or otherwise detected sensitive material anywhere in the snapshot
omits the entire row. Detector failure also omits; never emit detector input,
exception text, matched fragments or secret-derived identifiers.

Copy at most one row of 120 validated terminal cells, without adjacent/cursor
rows, history, full frames, unrelated prompts, session IDs, content hashes or credential
values. The exported excerpt is exactly `rowRelation: OTHER_CAPTURED_ROW` plus
`text`, formed from that row's cell text using the existing renderer row semantics.
Escape control/format characters for inert textual display; preserve ordinary
Unicode so the actual marker and description remain distinguishable.

The entire excerpt, including keys, escaping and JSON overhead, must fit 4096
UTF-8 bytes using the actual exported JSON encoding. Oversized or invalid rows
are omitted whole, never clipped into a plausible partial explanation. No new
raw-frame file, excerpt file, log stream, archive, telemetry or automatic upload
is created. Existing temporary native capture/history still follow their owned
deletion lifecycle and are not retained by this feature.

The existing namespace report uses a temporary output file. Do not route this
new content-bearing candidate through that file. Only for the new option, use
bounded in-memory IPC to the outer process, draining within the existing deadline
and cancellation lifecycle so a full pipe cannot deadlock the child. Bound the
complete intermediate message to the unchanged 16384-byte report ceiling, with
one extra byte sufficient to detect overflow. It is a private pending candidate,
not a public READY result. Validate private bindings inside the namespace before
serialization. The outer process accepts candidates only from its own launched
child's dedicated pipe, validates the closed candidate shape and case disposal
facts, and never treats serialized identities as proof. Reap that namespace child
and delete the owned outer root before preparing public
output. Missing, malformed, oversized or interrupted IPC cannot export an excerpt.
Do not change the old/default modes' report transport or add a retained sidecar.

Preparation must occur within the original command lifetime; expiry before
preparation omits capture. A candidate prepared in time may await disposal within
the existing outer deadline, without renewing input authority. Outer timeout or
interruption discards the candidate and permits cleanup only.

Emit a separate outer `debugContextEdit` object only when explicitly enabled.
It contains `status`, `untrustedData: true`, `chatCopyMayPersist: true`, and an
`excerpt` only for READY. Closed statuses are NO_CAPTURE, READY, OMITTED_SCOPE,
OMITTED_PROVENANCE, OMITTED_SENSITIVE, OMITTED_ROW_LIMIT, OMITTED_EXCERPT_LIMIT,
OMITTED_CLEANUP, OMITTED_REPORT_LIMIT and OMITTED_OBSERVER. No arbitrary diagnostic
error string is allowed. Default structural records remain content-free.

Export READY only after native/helper leaders are reaped and case plus outer
disposable roots, raw capture and history are confirmed absent. If disposal is
failed, partial or unproven, export only omission and preserve the original
failure/cleanup result. The sanitized row is untrusted evidence, never permission
or an instruction. A chat/export copy may persist and cannot be promised erased.
Sanitization reduces exposure but is not an absolute secrecy guarantee.

## Unchanged authority, budgets and failure behavior

Do not change Enter/Ctrl+U/exit bytes or their ownership proofs, original reason,
events, revocation, startup consent, acceptance conditions, deadlines, SDK/request
ceilings or first-inconclusive stopping. The diagnostic never enables a retry or
another case after an inconclusive result. Keep at most two synthetic cases,
25 seconds per context dialogue and 165 seconds total.

Keep 16 records and 3072 bytes per structural phase and 16384 bytes for the complete
outer JSON report including audit/disposal facts, optional debug and newline.
The optional excerpt consumes that cap; omit it whole if it does not fit. Never
drop structural failure/cleanup evidence to make room for content. A report that
cannot fit without content remains blocked through the existing outer boundary.

Preparation, provenance, sanitization, serialization and collector failures are
best-effort omissions. They cannot replace the original operational exception,
interrupt revocation/FD/process/root cleanup, or cause a collector retry. Cleanup
of observation-only resources remains allowed after expiry but grants no input
authority. No Nori manifest, staging scope, version pin or production route changes.

## Required verification and documentation

After written-spec and implementation-plan approval, use synthetic TDD to cover:

1. Exact eligible first-failure row above and below input; ordinary description
   without the selector remains uncaptured. Count one ordered assessment and
   prove the same actual rejected index supplies the row.
2. Every mismatched phase/check/byte count/reason/relation/cause; disabled and old
   flags; audit/live mode rejection; partial or absent provenance. All omit.
3. Copied/replaced bindings, wrong exception/run/snapshot/transition, repeated
   consumption, expiry and cross-dialogue reuse. No late enrichment or forgery.
4. Unicode, control/format escaping, wide/continuation cells, malformed snapshots,
   sensitive/canary-like synthetic fixtures and detector exceptions. No protected
   test value may escape into the report or test-command output.
5. The exact 120-cell and 4096-byte boundaries, actual encoding overhead, maximal
   phase/report envelopes and whole-excerpt omission rather than truncation.
6. Preparation/collector/serialization failures, cancellation and disposal faults;
   actual capture/PTY closure, leader reaping and absent owned roots. No row export
   before all required disposal facts or after unproven disposal.
   Exercise bounded IPC overflow, partial messages, backpressure and interruption;
   verify no content-bearing file write and no deadline extension or child leak.
7. Identical operational results, original errors/events, command/Enter/nonce/clear
   bytes and cleanup with and without the diagnostic. Neither shape-valid debug
   output nor READY supplies acceptance or renewed authority.
8. Unchanged package mounts and staging/archive exclusion, existing debug behavior,
   content-free normal output and no new raw-file write.

Run focused regressions, scoped independent review and a full package gate on an
immutable implementation candidate. Update ADR-010/index, unreleased CHANGELOG,
validation notes and spec/plan statuses with enforced behavior and observed
results only. Test-only scope requires no manifest/version bump unless the actual
implementation exceeds this boundary. No native test is part of synthetic TDD.

## Approval and rollback

Direction approval permits writing this spec. Approval of this written spec
permits writing the implementation plan; implementation requires that plan's
approval and execution-method choice. A native attempt requires fresh authorization
bound to the final commit, explicitly permitting the optional row export and its
potential persistent chat copy. No previous execution/debug grant is reused.

Remove the new flag, private observation and outer optional output as one unit
to roll back. Keep the content-free observer, old debug contract and strict input
protocol intact. Rollback cannot undo an exported chat copy or restore a consumed
grant. No push, PR, merge, release or definitive TODO completion follows from this
spec or from future diagnostic success.
