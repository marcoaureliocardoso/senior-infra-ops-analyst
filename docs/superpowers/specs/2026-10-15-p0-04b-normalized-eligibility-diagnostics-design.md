# P0-04B normalized eligibility subreason observation

Status: diagnostic direction and written specification operator-approved.
Implementation plan approved for inline execution; local implementation and
181 covering tests complete. Immutable full-gate and independent review pending.
No additional native execution is authorized by implementation approval.
Source baseline: `d86543d946a714557ba3289718d9cc772afcc9a2`.

## Intent and observed evidence

Identify why the actual normalized empty-input assessment rejected an owned
offline context edit, without retaining terminal content or weakening input
ownership. Success means a future rejection distinguishes the assessment's
closed subreason; success does not mean accepting an ambiguous terminal.

This supplements the implemented
[context rejection observer](2026-10-14-p0-04b-context-rejection-diagnostics-design.md).
Its phase, concrete-write accounting, first-failure binding and privacy contract
remain in force. The existing four-field `contextCommandFailure` stays unchanged.

The single authorized offline run on the baseline observed Claude Code 2.1.299
and stopped in the first text-turn before dialogue: `INPUT_PROBE_REVOKED`,
`NORMALIZED_ELIGIBILITY`, `EDIT_PENDING`, eight acknowledged command bytes and
zero Enter bytes. No gateway message, SDK turn or skill-turn ran. Both leaders
were reaped and disposable roots removed. That execution grant is consumed.

Retained structural evidence and source-only investigations are outside Git in
the test-owned `.review-runtime/p004b-terminal-state` directory:

- `p004b-offline-d86543d-structural-result.json` records the native aggregate.
- `normalized-eligibility-investigation-d86543d.md` records static tracing,
  installed-executable inspection and 16 passing pure fixture expectations.

The leading hypothesis is a command-suggestion selector colliding with the input
marker. Source-derived suggestion fixtures reproduce the rejecting check and all
retained structural fields without a numeric context panel. The description can
set `contextFresh`; that fact alone is not numeric context evidence. The native
subreason remains unproven because its raw frame was deleted and must not be
recovered. Installed-version observations are evidence, not runtime requirements.

## Decision and alternatives

Recommended: add an optional sibling `normalizedInputFailure` to the existing
failure record. Freeze its enums from the same assessment that rejects the edit,
inside the same sealed first-failure observation. Keep the original four-field
object and operational reason intact. Cost: a small additive observer/collector
contract with explicit coupling tests.

Expanding `contextCommandFailure` itself was not selected: consumers currently
validate exactly four keys, so extending it needlessly changes their contract.
Reusing existing `inputEligibility` fields by relabeling the error was rejected:
those fields are bound to `INPUT_PROBE_INELIGIBLE`, while this operation must
retain `INPUT_PROBE_REVOKED`. Reclassification would change operational semantics.

No acceptance workaround is selected. Ignoring suggestion-shaped rows, relying
on general READY status, adding recovery keys, changing command bytes or enlarging
deadlines would change the safety protocol without proving the native cause.

## Additive serialized contract

`normalizedInputFailure` is accepted only on an existing `failure` record with
`reasonCode=INPUT_PROBE_REVOKED` and a valid `contextCommandFailure` whose
`check=NORMALIZED_ELIGIBILITY`. It is absent on success, other checks, checkpoints
and cleanup. Its absence never supplies an explanation or changes acceptance.

| Field | Closed contract |
|---|---|
| `reason` | Exactly one existing empty-input rejection code listed below |
| `rowRelation` | Required only for UNSUPPORTED_ROW; one existing relation enum |
| `rowCause` | Required only for UNSUPPORTED_ROW; one existing cause enum |

Allowed reasons: `FORBIDDEN_STATE`, `NO_MARKER`, `UNSUPPORTED_ROW`,
`NONEMPTY_INPUT`, `MULTIPLE_MARKERS`, `CURSOR_ROW_MISMATCH`,
`CURSOR_COLUMN_MISMATCH`, `INSUFFICIENT_SPACE`, `ANCHOR_CHANGED`.
Allowed relations: `CURSOR_ROW`, `OTHER_CAPTURED_ROW`, `CURSOR_OUTSIDE_CAPTURE`.
Allowed causes: `INVISIBLE_FORMAT_CHAR`, `UNSUPPORTED_WHITESPACE`, `MARKER_WIDTH`,
`CONTROL_COMMAND_SHAPE`, `UNRECOGNIZED_SHAPE`.

UNSUPPORTED_ROW has exactly three keys; every other reason has exactly one key.
No nulls, extra keys, arbitrary strings, cells, characters, hashes or coordinates
are accepted in this object. The vocabularies reuse the existing policy constants,
not a runtime-specific list of command descriptions or version fingerprints.

Example of a possible failure record, not a claim about the deleted native frame:

```json
{
  "point": "failure",
  "reasonCode": "INPUT_PROBE_REVOKED",
  "contextCommandFailure": {
    "phase": "EDIT_PENDING",
    "check": "NORMALIZED_ELIGIBILITY",
    "commandBytesWritten": 8,
    "enterBytesWritten": 0
  },
  "normalizedInputFailure": {
    "reason": "UNSUPPORTED_ROW",
    "rowRelation": "OTHER_CAPTURED_ROW",
    "rowCause": "UNRECOGNIZED_SHAPE"
  }
}
```

## Decision boundary, provenance and failure isolation

1. At the existing `_prefix` boundary, evaluate normalized empty-input assessment
   once through the same ordered policy evaluator currently used by
   `empty_input_anchor()`. Compare its anchor with the original anchor exactly as
   today. Do not add a second assessment, IO, clock read, poll or live validation.
2. If its anchor is absent, copy only a valid closed rejection reason and its
   applicable row enums. If it returns a different non-null anchor, the actual
   comparison rejected: use `ANCHOR_CHANGED`, not an invented row explanation.
   Unknown or inconsistent detail is omitted; it cannot modify the comparison.
3. Freeze the valid detail with the existing phase/check/count payload at the
   first rejection before revocation. Use the same exception, journal, controller,
   terminal, run and transition bindings. Store immutable scalar tuples, never
   the assessment object, snapshot, row, input bytes or exception message.
4. Project the base and optional detail from one validated frozen observation.
   Preserve the existing base-only projection contract for current callers.
   Do not recompute a reason from the later diagnostic snapshot or make a revoked
   operation live again. Missing detail cannot be attached by a later catch.
5. The collector validates the two fields' coupling and copies the entire record
   atomically. Malformed serialized detail rejects the record through its existing
   diagnostic mechanism. An internally unavailable/malformed optional detail is
   omitted without discarding an otherwise valid base observation.

Forgery, replacement, mutation and cross-dialogue reuse must not produce trusted
detail. Shape-valid serialized data remains data, not provenance or authority.
First-failure rules apply to both fields together; later exceptions or cleanup
cannot substitute a different assessment. No new observation extends beyond the
owned command's existing observation window or activates default/live routes.

Observer failures remain best-effort: preserve original result, reason, revocation
and capture/FD/helper/native cleanup. Never retry a failing collector. Do not
change `InputProofError` semantics to accommodate the new serialization.

## Components and unchanged limits

The private journal/attachment module freezes and purely projects optional detail;
the context component supplies enums at the actual boundary; the selected driver
transports the paired projection; the structural collector enforces its shape and
coupling. The offline launcher keeps its existing audit, disposal and aggregation.
Use existing mounted modules; add no dependencies, activation flags or CLI options.

Keep 16 records and 3072 exported JSON bytes per phase, and 16384 bytes for the
complete outer report including disposal/audit facts and newline. The additional
field consumes these caps; it does not expand them or add a checkpoint.
Keep 25 seconds per dialogue, 165 seconds total, at most two cases and stopping at
the first inconclusive result. Preserve SDK/request ceilings, network isolation,
hidden operator state, startup consent and capability-drop requirements.

No raw frame, prompt, stream, nonce, credential, history, content hash, native
session identifier or arbitrary exception text may enter the observation.
Temporary debug capture eligibility and protected disposal remain unchanged.
No installed skillset behavior, operator preference, provider transport, runtime
version, component manifest or absolute context-window size is changed or pinned.

## Required verification

Implement only after written-spec and plan approval, with synthetic TDD:

1. Reproduce selected-menu-like rows above and below input with no numeric panel:
   preserve the existing rejection and expose UNSUPPORTED_ROW/OTHER_CAPTURED_ROW/
   UNRECOGNIZED_SHAPE. Removing the selector permits the original valid case;
   general READY or `contextFresh` alone cannot supply edit or numeric proof.
2. Cover every allowed assessment reason, the actual mismatched-anchor comparison,
   simultaneous faults and existing short-circuit order. Invalid assessment detail
   must not alter acceptance or manufacture a supported subreason.
3. Count the ordered assessment invocation and prove there is only one; verify
   identical original reason, input writes, phase/count accounting, lifetime checks
   and acceptance events with and without the observer.
4. Verify exact shape/coupling, unsupported-row key pairing, first-freeze retention,
   immutable copies and omission on unrelated/success paths. Reject forged,
   replaced, foreign or cross-run attachments and malformed serialized records.
5. Inject observer and collector failures; verify original exception/success,
   revocation, closed captures/FDs and reaped leaders, with no retry or extra input.
6. Exercise maximum phase/report envelopes and existing debug/disposal/cancellation
   tests; preserve namespace wiring, Nori staging/archive and installed behavior.
7. Run focused regressions, scoped independent review and a full package gate on
   an immutable implementation candidate. Documentation-only closure is checked
   separately and must identify the tested/reviewed source hashes accurately.

Fixtures must not execute Claude, contact a provider or read operator settings.
Use the passive renderer where relevant, without relying on an installed binary
version or its minified names. A passing suite proves diagnostics, not native
workflow completion or the actual cause of the consumed attempt.

## Documentation, rollback and approval gates

This spec is indexed as proposed, not implemented. After implementation, update
ADR-010 and its index, unreleased CHANGELOG and validation notes with enforced
behavior and actual evidence. Test-only scope does not require a manifest/version
change; reassess if implementation exceeds this boundary.

Rollback removes the additive detail path and its collector coupling as one unit,
leaving the existing four-field observer and strict operational protocol intact.
It does not restore a consumed execution grant or reconstruct deleted evidence.

Written-spec approval permits creation of the implementation plan. Implementation
requires review of that plan and selection of its execution method. A fresh native
attempt requires separate final-commit authorization; no native/provider/browser
run, push, PR, merge, release or definitive TODO completion follows from this spec.
