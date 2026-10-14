# P0-04B content-free context rejection diagnostics

Status: conversational design approved; written specification awaiting operator
review. No implementation plan or implementation is approved by this document.
Source baseline: `ad7b080a2e85b1591422f1d890671b95c974a3df`.
No native execution, provider request or additional content capture is authorized.

## Intent and evidence

Identify the exact observed rejection of the isolated offline owned `/context`
transition without retaining terminal content or weakening input ownership.
This is a developer test-harness observation contract, not a production feature,
new input route or correction of a confirmed native root cause.

The single authorized offline attempt on the baseline returned
`OFFLINE_CONTROLS_INCONCLUSIVE` with `INPUT_PROBE_REVOKED` in the first text-turn
before dialogue. Prompt readiness passed; neither `context_sent` nor
`context_numeric` completed. Failure coordinates showed cursor advancement from
column 2 to 10 on the same alternate-buffer row. Those coordinates do not prove
the command cells, actual written-byte count or whether Enter was written.
Native/helper leaders were reaped and disposable roots removed. No SDK,
after/resume, skill-turn or real provider ran. The execution grant is consumed.

Retained structural evidence is outside Git under
`p004b-offline-ad7b080-aggregate.json` and `p004b-offline-ad7b080-result.md` in the
test-owned runtime directory. Deleted raw data must not be reconstructed.

Source-only investigation reproduced eight synthetic scenarios using the actual
passive terminal helper. Five different rejection mechanisms and one valid
command echo shared the native structural signature. Repainting non-breaking
prefix padding as an ASCII space reproduced strict prefix rejection; preserving
the padding passed. This establishes a possible mechanism, not a native cause.
The existing debug contract correctly omitted this early rejection because its
numeric-context and unsupported-row provenance prerequisites were absent.

## Decision and alternatives

Add one optional, atomic, immutable, content-free failure observation. It records
the original command phase, the first actually failing check and separately
acknowledged command/Enter byte counts. Attach it at the rejection boundary,
before revocation destroys phase information; transport it through the existing
failure diagnostic record. Never derive it later from cursor coordinates or
re-run classification against a newer snapshot.

Expanding temporary raw-frame capture to pre-submission failures was not selected:
it widens content exposure and still cannot reliably establish process lifetime
or concrete write acknowledgements. Relaxing whitespace or using cursor-only
assessment was rejected: the native cause is unproven and existing ownership
and global ambiguity checks must remain strict.

This specification supplements the
[owned context echo design](2026-10-13-p0-04b-owned-context-echo-design.md).
It changes observation only; its permission, receipt, deadline and cleanup
requirements remain in force.

## Scope and non-goals

- Observe only the existing audited offline owned-command route, from empty
  baseline assessment through context-history binding. Ordinary passive/live
  routes and later nonce/clear/exit operations receive no new command authority.
- Preserve the fixed command, exact prefix/body/geometry checks, ordered global
  assessment, fresh numeric barrier and one-shot submission behavior.
- Preserve original scope, cancellation, native/helper lifetime, startup consent,
  network isolation, hidden operator state and capability-drop requirements.
- Do not add CLI flags, environment activation, dependencies, renderer/version
  fallbacks, automatic retries, extra writes or operational grace periods.
- Do not expand `terminal_context_debug.py` capture eligibility or its content
  export contract. No early raw-frame capture is introduced.
- Do not change installed package behavior, operator settings, provider transport,
  credentials, root/component versions or the definitive TODO completion state.

## Observation contract

The existing `failure` record may carry one `contextCommandFailure` object with
exactly four fields:

| Field | Closed contract |
|---|---|
| `phase` | `BASELINE`, `ELIGIBLE`, `EDIT_PENDING`, `COMMAND_ECHO_MATCHED`, `SUBMIT_PENDING`, `CONTEXT_PENDING`, or `RECEIPT_READY` |
| `check` | One code from the rejection-check vocabulary below |
| `commandBytesWritten` | Exact integer from 0 through 8; acknowledged fixed-command bytes |
| `enterBytesWritten` | Exact integer from 0 through 1; acknowledged submission byte |

Booleans are not integers for validation. Additional keys, arbitrary strings,
unknown phases/checks and out-of-range values are invalid. Bounds describe the
already fixed ASCII command and one submission byte, not a context window.
The observation is absent on success and on unrelated failures.

Use this closed check vocabulary, preserving the actual evaluation order:

- `BASELINE_ELIGIBILITY`: the existing baseline assessment rejected eligibility.
- `SCOPE_BINDING`: actual scope audit or run/terminal/transition binding rejected.
- `DEADLINE`: actual original deadline or monotonic-clock check rejected.
- `CANCELLATION`: the actual cancellation check terminated the operation.
- `NATIVE_LIFETIME`: the actual native-owner poll observed termination.
- `AUTHENTICATION`: the actual controller authentication check rejected.
- `FORBIDDEN_UI`: the actual menu/selection prohibition rejected.
- `FRAME_STATE`: frame progression or snapshot type validation rejected.
- `PHASE_STATE`: the requested action did not match the existing phase.
- `WRITE_COUNT`: supplied progress failed its existing bounds.
- `ANCHOR_GEOMETRY`: buffer, viewport or anchored row equality rejected.
- `CURSOR_PROGRESS`: cursor advancement was outside zero through acknowledged bytes.
- `PREFIX_CELLS`: exact original cells left of the command changed.
- `COMMAND_CELLS`: observed command characters or cell widths rejected.
- `TRAILING_CELLS`: cells after the current owned edit rejected.
- `NORMALIZED_ELIGIBILITY`: the actual normalized empty-input assessment rejected.
- `ECHO_REGRESSION`: observed command progress decreased.
- `INCOMPLETE_ECHO`: submission required a complete echo that was not present.
- `FRESH_CONTEXT`: post-submission numeric/frame/signature requirements rejected.
- `HISTORY_AMBIGUITY`: duplicate or mismatched correlated history rejected.
- `HISTORY_ELIGIBILITY`: the actual history-aware empty-input assessment rejected.
- `IO_WRITE`: a concrete write failed without a valid acknowledgement.

Separating currently combined predicates must preserve short-circuit order,
error reason, mutation order and effective rejection. A check code identifies the
first executed failing predicate, not all plausible explanations. For example,
`PREFIX_CELLS` alone does not claim which character changed. Do not add content,
character values, hashes or retrospectively guessed checks to make it specific.

Some existing scope accessors combine failures, including helper lifetime.
Report `SCOPE_BINDING` when that is the actual rejecting boundary. Do not perform
additional probing merely to select a more specific code. Unsupported exceptions
retain their existing reason and omit the observation rather than using a guessed
catch-all code.

The collector accepts this object only with existing `INPUT_PROBE_*` reasons,
`RUNTIME_REJECTED` or `TERMINAL_DEADLINE_EXCEEDED`, and only at `failure`.
`AUTHENTICATION` and `CANCELLATION` may accompany their existing
`RUNTIME_REJECTED` result; `DEADLINE` may accompany
`TERMINAL_DEADLINE_EXCEEDED`. No checkpoint, cleanup or successful event may
carry it. Projection preserves the originating exception and the controller's
existing reason mapping; it does not convert a failure to another reason.

## Concrete write accounting and phase semantics

The controller owns a private per-transition accounting journal. Its binding is
to the existing controller invocation, terminal, run and transition identities;
it cannot be supplied by JSON, terminal output, environment or public callers.
It is an observation mechanism, not an input or scope capability.

Initialize both counters to zero only for a new audited owned-command transition.
`BASELINE` denotes its initial assessment before a command object exists. Never
reuse a journal for a resumed dialogue or another context phase/case.

Immediately after `os.write` returns a valid count, advance the matching counter
before any subsequent lifetime, scope, echo or submission-state validation can
raise. Count actual accepted bytes, not requested lengths, echo progress,
cursor advancement or completed checkpoints. Partial command writes accumulate.
`BlockingIOError` and a write error without an acknowledgement add no bytes;
an invalid count cannot be represented as confirmed progress and must suppress
the observation rather than manufacture a count.

Freeze the observation at the first supported rejection, with the phase as it
stood before failure revocation. Later cleanup, catches or invalidation must not
overwrite that observation. In particular, `SUBMIT_PENDING` with
`enterBytesWritten=1` is valid when Enter was accepted but the subsequent live
check rejected before transition completion. It is not proof of a completed
context inspection. An acknowledged byte cannot be rolled back to zero.

Keep both counters independent of command state that is updated only after
validation. A post-write prefix failure must report the actual just-written
command bytes even when the command's validated-progress field was not advanced.
No new byte write, native poll, helper call, clock read or authority validation
is performed by projection of the frozen observation.

## Components and propagation

- A focused private test-only observation component owns the closed vocabulary,
  accounting journal, sealed failure attachment and pure projection. Store only
  enums, counts and in-process identity bindings; do not store terminal snapshots,
  cells, payload bytes, paths, process/session identifiers or exception messages.
- `tests/terminal_context_echo.py` labels its actual rejection boundaries and
  freezes the pre-revocation phase with the journal's acknowledged counts.
  It remains free of IO and retains all existing permission checks.
- `tests/headless_context_driver.py` updates accounting at concrete writes and
  labels its actual command-route lifetime/auth/UI/IO failures. Its outer catch
  only projects a previously issued observation; it cannot invent one from final
  state. If an inner boundary supplied one, the outer catch must not replace it.
- `tests/terminal_input_challenge.py` retains the existing `InputProofError`
  constructor and nonce authority. Private attachment is additive; reason codes,
  normal string representation and existing eligibility fields remain unchanged.
- `tests/terminal_structural_diagnostics.py` validates the exact closed object
  only at `failure` with a compatible existing reason. It copies the projected
  object atomically and rejects malformed records using its existing mechanism.
- The offline launcher transports existing diagnostics unchanged in purpose.
  If a new private module is required, its mount must be read-only in the same
  audited namespace; it does not enable native launch or access operator files.

Projection must verify private registration, exact exception/transition binding
and supported phase/check/count types without requiring the now-revoked operation
to become live again. Forged, replaced, mutated or cross-transition attachments
produce no trusted observation. The collector still independently validates the
serialized closed shape; a shape-valid dictionary cannot establish provenance.

Diagnostic failures do not change the operational outcome, retry behavior or
acceptance events. Invalid observation is omitted/rejected, never a permissive
fallback. Existing operational revocation, exception propagation and cleanup
must complete even if diagnostic attachment or collection fails.

## Limits and privacy

Keep at most 16 records and 3 KiB per phase, and a complete outer report of at
most 16 KiB including audit/disposal facts and final newline. Add the object to
the existing failure record, not extra structural checkpoints. Overflow retains
existing rejection/truncation behavior and cannot become acceptance success.

Keep 25 seconds per context dialogue, 165 seconds total, at most two cases,
stop-at-first-inconclusive and all existing SDK/request ceilings. Observation
consumes the original budget; it does not renew a deadline.

Never retain or export command/prompt content, raw cells/streams, nonce values,
credentials, tokens, hashes of content, native history, arbitrary exception text
or session identifiers. Existing opt-in temporary-frame/recut allowances remain
separate and unchanged. Raw/history/root disposal precedes final aggregation;
disposal failure cannot permit export or success. Cleanup is not a secure-erasure
claim, and an approved chat copy may persist.

## Required verification and acceptance

Implement with synthetic TDD; tests must not launch Claude or contact a provider.
Use the actual passive renderer and selected driver where relevant.

1. Distinguish valid echo from prefix-padding repaint, trailing text, extra
   control row, forbidden menu and native-owner loss. Reproduce the two renderer
   spacing cases without exporting cells; a valid case has no rejection object.
2. Cover each supported check code at its real boundary, preserving the existing
   reason and ordered rejection. Test simultaneous faults to prove first-failure
   attribution, and combined scope failures without invented specificity.
3. Cover partial writes, writable waits, BlockingIOError, write failure and
   invalid counts. Prove counts update before a post-write check can fail and
   that acknowledged Enter survives rejection before `context_sent` completes.
4. Prove phase freezing before revocation, first-observation retention, independent
   command/Enter counters and isolation between dialogues/transitions.
5. Reject forgery, mutation, foreign exception/controller bindings, bad enums,
   booleans-as-integers, unknown fields and range violations. Projection must not
   invoke live checks, execute IO, recover authority or change operational events.
6. Verify byte/record/report limits, all-or-nothing serialization, malformed and
   unavailable observations, cleanup/cancellation and content-free output.
   Existing raw-debug eligibility and disposal tests must remain unchanged.
7. Preserve strict no-receipt/default/live behavior, namespace mounts, package
   content/discovery, Nori staging/archive and existing acceptance event schemas.
8. Complete scoped independent code review and the full package gate on the same
   immutable implementation candidate before proposing a new native experiment.

Passing synthetic diagnostics is not native/browser acceptance. The previous
attempt's cause remains unknown; this change makes a future observed failure
more distinguishable but does not promise that Claude completes the workflow.

## Documentation, rollback and next gates

After implementation, record the enforced observation contract in indexed
ADR-010, CHANGELOG and validation notes with actual review/test evidence. Do not
label this proposed contract as implemented in the architecture history now.
No runtime/dependency/window pin or version bump is needed for this spec-only
change. Reassess packaging impact if implementation exceeds the stated scope.

Rollback removes the additive observer and its controller/collector/mount
integration as a unit, leaving strict baseline command/receipt/nonce behavior.
It does not restore a consumed native execution grant.

Approval of the conversational design permits writing this specification.
Written-spec approval permits creating the implementation plan; implementation
requires review of that plan and selection of its execution method. A future
native run requires a fresh exact-final-commit grant with the existing isolation,
input sequence, content policy, limits and no-repeat restriction. Provider/browser
acceptance, CI/Security, push/PR and main merge remain separate gates. No definitive
TODO completion follows from this specification or synthetic verification.
