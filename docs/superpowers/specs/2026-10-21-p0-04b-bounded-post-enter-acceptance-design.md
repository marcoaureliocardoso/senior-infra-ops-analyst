# P0-04B bounded post-Enter acceptance transition

Date: 2026-10-21
Status: approved on 2026-10-21; acceptance transition/fence implemented locally;
complete validation blocked at the preexisting outer-publication lifecycle.
Implementation baseline: `3c159a15c13a321c2166abde10538292fa732918`.
Scope: test-only extension; no production policy change or new native execution grant.

## Intent and existing contract

Extend only the passive waiting transition of the existing audited offline
resumed-context acceptance route. Keep the approved property from the
[correlated-display contract](2026-10-19-p0-04b-correlated-context-display-design.md):
CORRELATED_DISPLAY plus independent current-input proof, not NATIVE_RECOMPUTED.
Do not redesign that property, force numeric change or turn a diagnostic report
into acceptance. The operational objective remains P0-04B browser controls;
terminal chronology is not a new independent delivery objective.

The operator selected this direction after investigation and subsequently
approved this written specification. The [implementation plan](../plans/2026-10-21-p0-04b-bounded-post-enter-acceptance.md)
was approved for native/inline execution. Tasks 1/2 are implemented; Task 3
requires design review before changing the separate outer lifecycle.
All previous native grants are consumed. No native/provider/browser execution,
push, PR, merge, release, staging refresh or definitive TODO completion follows.

## Evidence and its limits

One explicitly authorized observation on the baseline returned
CURRENT_PROFILE_OBSERVED / COMPLETE, exit0, in 11.847 seconds overall. Its closed
summary contained DISAPPEARED, EMPTY, NEW_CELL and BASELINE_EQUIVALENT. Initial
completion and the synthetic SDK sample were validated; native/helper reap and
case/outer-root deletion were proved. The report retained `acceptance: false`.
The source archive identifies the baseline commit and SHA-256
`3dfa051969f9e861d9c49ba2c27c551408462140ce2356466ccb8b3c069606f3`.

Evidence outside Git is `p004b-offline-3c159a1-attempt.json` and
`p004b-offline-3c159a1-structural-result.json` under
`.review-runtime/p004b-terminal-state/`. It contains no retained native raw frame,
prompt, transcript, credential or history. Do not reconstruct discarded content.
No runtime version was retained in this observational schema; do not infer one
from an earlier attempt or from a later installed executable.

Follow-up synthetic checks passed observer28, report17 and driver-observer6.
Controlled comparisons using the existing fixtures established two distinctions:

- The ordinary resumed display route recognizes a direct final profile but
  rejects a consumed post-Enter completion before it can inspect a later profile.
- The observational route can reach the same final summary directly or after
  consuming the exact known transient menu. The retained summaries are identical.

Thus native profile feasibility was observed once, but neither post-Enter menu
persistence nor the cause of the successful timing can be reconstructed. The
11.847-second total is not a menu-wait duration. No extra causal recorder or
another native attempt solely to prove that timing is required by this design.
Native nonce/clear/natural-exit acceptance in the resumed dialogue, skill-turn,
real provider/browser behavior and remote gates remain unproved by this result.

## Decision and alternatives

| Approach | Property | Decision |
| --- | --- | --- |
| Extend the existing acceptance transition | Same correlated display and nonce contract, with a narrowly checked read-only pending phase | Selected |
| Require a native structured command/result receipt | Stronger application-level correlation if documented and detected | No such generic built-in receipt has been established; do not invent it |
| Add more timing observations or increase timeout | More chronology, not additional input authority | Not selected; existing evidence is sufficient to justify designing the bounded transition |

The selected route must be acceptance-owned from its original setup. It does
not convert `--observe-post-enter`, its request/guard, closed summary or result
tombstone into a witness. Observation remains irreversibly read-only after Enter.

This would narrowly supersede the blanket post-Enter completion rejection in
the [menu contract](2026-10-15-p0-04b-correlated-command-menu-design.md), only
while the audited resumed acceptance coordinator awaits its current display.
The original pre-Enter correlation still retires at Enter; separate read-only
facts may justify passive classification, never continued editing or submission.
All HISTORY_COMMIT_V1 criteria, history inventory and later nonce/exit rules stay.
The [observational contract](2026-10-20-p0-04b-post-enter-observation-design.md)
and its prohibition on returning to acceptance are not superseded.
The audited offline resumed transition is implemented locally; non-resumed,
production and observation-only contracts remain unchanged. Full validation
and native acceptance are not established by that implementation.

## Activation and original boundary

Activate only for an audited offline resumed acceptance invocation with its
actual completed initial handshake, validated fixed synthetic SDK sample,
private live resumed-history view and original owned `/context` command.
Support the existing text-turn and skill-turn kinds without assuming that
native success for one establishes the other. Initial dialogues, ordinary
policy callers, default non-resumed drivers, installed/live/provider/browser
routes, content-debug routes and the observational mode retain their contracts.
No new public flag, environment switch, caller-provided exclusion or setting.

Before Enter, the actual controller prepares a private non-serializable pending
binding under the original command, scope/run/state/helper/native/controller/
transition/case, geometry and deadline. Keep exact baseline/provenance references,
old pinned/retired history, original inventory and any privately correlated menu.
The existing position-only diagnostic annotation is not sufficient evidence.

Finalize this binding from the last validated pre-Enter snapshot, including
every consumed writable-wait frame. Require eight actual command-byte
acknowledgements, full exact owned echo and one actual Enter acknowledgement.
Wrong/partial/boolean counts, stale or copied snapshots, foreign bindings and
pre-Enter failures reject; no catch-and-resume fallback is permitted.
Retirement of the pre-Enter editing/menu capability is irreversible. The
acceptance-owned command/view need not be revoked: they remain live solely for
the existing display-witness lifecycle. Never invalidate and then reopen them,
detach the observational guard into acceptance, renew a scope or move a deadline.

## Passive phase and composed assessment

At the Enter acknowledgement, before any later callback or output pump can
dispatch input, all terminal-input paths must be fenced while the display is
pending or only a candidate. This includes raw and
whole-writer callbacks, startup keys, terminal-generated responses, another
Enter, Escape, Tab, nonce, Ctrl+U and `/exit`. Cleanup uses supervision, not keys.

Every consumed snapshot must first pass the original cancellation/deadline,
monotonic ordering, owner/helper/native/scope/run/controller/transition/case,
capture/parser, authentication/modal and supported geometry checks. Old-history
validation remains fatal, including pinned replacement/movement and retired-row
return. Perform one authoritative ordered assessment of all remaining rows;
a known row must never hide a later unknown marker or authentication screen.
PENDING is an internal non-writable flow decision, not a successful empty-input
assessment or a generic row-exclusion permit. Only the owning coordinator may
wait on it. Premature `bind_history` or a foreign caller must fail closed,
without a receipt or recovery; no projected anchor can bypass the passive fence.

The only nonterminal transient forms are:

1. The exact selected off-cursor completion already correlated before Enter,
   at the original position with unchanged supported cells and geometry.
2. The exact owned `/context` echo at its original input anchor, with the
   original prefix/tail, supported width-one cells and exact cursor geometry.

Neither form is empty input, history, command completion or write authority.
A missing pre-Enter menu cannot be learned after Enter. Movement, mutation,
duplication, another command, unowned draft/marker, unsupported cells or other
unrecognized layout rejects. Disappearance of each known transient is monotonic;
once absent, its return rejects. A bare history shape at any original menu or
inventoried history position remains forbidden, even after menu disappearance.

Assessment-only normalization may project out the sole exact owned input echo
when checking other rows, as in the approved ownership discipline. It must not
modify the captured state, fabricate rows, create a candidate from that
normalized anchor or become a general permissive parser. Candidate empty-input
proof always uses the actual supported empty current input, not a projected one.

Track numeric conflicts throughout this phase. Missing/partial observations
are not complete samples. Intraframe contradictory free/buffer values or invalid
totals reject; once a distinct complete sample is seen, returning to baseline or
another distinct sample rejects. Restoration cannot erase contradictory evidence.
Baseline-equivalent numbers alone do not establish a display witness.

## Existing witness and independent input proof

The first candidate must meet every HISTORY_COMMIT_V1 condition simultaneously:
one supported new current-command history row outside the original inventory
and validated old exclusions; actual supported empty current input; no remaining
completion or competing marker; a complete valid numeric sample; and all live
guards without a discarded conflict. The no-menu path uses the same criteria
and does not require observing a transient or waiting a fixed amount of time.

Drain bounded already-available output and revalidate the exact row, numeric
sample and empty anchor against the latest consumed snapshot. Candidate loss,
movement, duplication or conflicting evidence is terminal, not a return to
waiting. Silence, a delay, parser callbacks, frame counts, menu disappearance,
empty input or a numeric grid alone never establish the candidate.

Only the original acceptance coordinator may issue and consume the existing
private display witness to bind the existing context/history receipt. The
pending state then retires permanently, releasing its content-bearing transient
references. No transient exclusion survives into receipt/nonce/exit assessment.
The ordinary current-display/history validators remain active thereafter;
transient return or post-bind mutation rejects rather than reactivating pending.

Logical phases, not a new public event schema:

| Phase | Input permitted | Evidence required to advance |
| --- | --- | --- |
| Original owned edit/submission | Only existing checked `/context` writes and one Enter | Exact original pre-Enter proofs and actual acknowledgements |
| Passive pending / display candidate | None | Full current profile, drained/latest-frame validation and original live guards |
| Bound display receipt | No generic write permit | Existing one-shot witness consumption and strict current-input eligibility |
| Existing nonce/clear/exit protocol | Only its independently guarded next bytes | Fresh checks before each concrete write and after every intervening await |
| Revoked, failed, closed or expired | None; owned cleanup only | Terminal; no restoration |

Do not reopen a generic writer merely because a profile or diagnostic says
success. Nonce construction and each subsequent write must use the existing
command/receipt/view/scope/controller identities and current strict assessment.
Keep 16 non-submitted synthetic nonce characters, exact echo before one Ctrl+U,
a newer empty frame, one consumed exit proof, guarded `/exit` bytes and natural
exit0. Do not add a menu exception for nonce, clear or `/exit`, or alternate keys.

## Integration, reporting and bounds

- `tests/terminal_context_echo.py` owns the private acceptance pending binding,
  composed phase assessment and existing display witness. Shared callers such
  as `observe`, `context_display_percent`, `bind_history` and the resumed
  composer must agree; no one-caller-only fix or reconstruction after rejection.
- `tests/headless_context_driver.py` and its CLI wrapper enforce the central
  phase-aware write fence and existing checked nonce/clear/exit dispatch. No
  broad Boolean writer reopening or switch from an observational invocation.
- Existing pure row/numeric helpers may be reused, including contradiction
  checks. Shared factoring must not change default policy or the observational
  mode. Its controller/guard/summary cannot serve as an acceptance capability.
- `tests/terminal_resume_history.py` retains case/SDK/view identity, old-history
  retirement and one-shot validation; `tests/terminal_input_challenge.py` retains
  independent nonce/clear/exit authority. No serialized record can mint either.
- The existing acceptance aggregator still requires resumed context_display,
  context_inspected, nonce checkpoints, natural exit and native/helper/case/outer
  cleanup. A pending/candidate state cannot emit passed acceptance checkpoints.
  Missing required evidence or an observational-schema envelope remains failure.

Preserve 25 seconds per dialogue, 165 seconds overall including existing cleanup
allowance, current SDK/request ceilings and original case order: at most text-turn
then skill-turn, stopping at the first inconclusive case. No deadline renewal,
busy-loop probe, automatic repeat, installation, runtime/provider/model/window
pin or operator-state/credential access. Native status-line priority and the
separate P0-04B measurement sidecar are outside this change.

Keep 16 records/3072 actual JSON bytes per phase and 16384 bytes for the complete
outer report including disposal/newline. Retain only existing bounded structural
events, closed reasons, booleans and percentages. No new timing trace, menu text,
row, nonce, prompt, transcript, history or content hash may be exported. The
content-debug contracts are not broadened. Optional diagnostics cannot suppress
the base failure, while missing required proof cannot be treated as optional.
Keep cancellation supervision through owned reap/disposal, suppress success
after cancellation/expiry, and make known cleanup failure dominate every result.
Delete owned raw evidence/history/roots before aggregation/publication.

## Required validation and later execution gates

The implementation plan must require author-owned TDD and controlled synthetic
PTY/namespace integration, independent whole-change review and an immutable
complete package gate on corrected source. Cover at least:

- Direct final profile and exact menu/owned-echo transients followed by a valid
  profile, with equal and changed numbers, for both synthetic case kinds.
- No menu before Enter followed by an unowned menu; partial/wrong echo, count,
  stale/copy/foreign binding, owner/helper/case/geometry/deadline/cancellation loss.
- Known menu plus another unknown/authentication row; movement, mutation,
  duplication, disappearance/reappearance, unsupported cells and input drafts.
- Completion-only or input-clear-only output, no new history, menu-cell history
  replacement, pinned/retired/moved/duplicate history and restored conflicts.
- Intraframe contradictions and cross-frame numeric change/restoration;
  candidate loss during drain, writable waits and subsequent nonce/exit use.
- Both raw and whole-writer paths, callback attempts and terminal responses:
  zero bytes while passive/candidate; after binding only exact independently
  guarded protocol bytes. Test a forbidden callback after binding as well.
- Delayed/fragmented output under original limits; process/helper exit and
  protocol/capture loss. Never coalesce past a fatal intermediate observation.
- Actual fixed command + one Enter + 16 nonce characters + one Ctrl+U + `/exit`
  sequence, checkpoints, newer empty frame, natural exit and complete cleanup.
- Forged/replayed/serialized witnesses, diagnostic records, closed summaries
  and the observation result/tombstone cannot create acceptance. A revoked
  capability or a failed candidate is never restored.
- Observational mode unchanged: exactly one text case, no post-Enter byte or
  acceptance event, `acceptance: false` and rejection by the legacy aggregator.
- Initial/default/non-resumed/live/provider/content-debug and installed/staging
  behavior unchanged; report pressure, diagnostic loss and cleanup-failure
  priority. No installed Claude/provider/operator state during synthetic tests.

Synthetic success does not establish native acceptance. After implementation,
review and the complete gate, any native run needs a fresh exact-final-commit
one-shot authorization explicitly permitting the resumed nonce/clear/exit
protocol. It must not reuse the observational grant. A full existing offline
run may include skill-turn only within that grant and only if text-turn passes;
native support for either case or a later `/exit` layout is not promised.

The later acceptance result must prove the existing complete case contract,
not just CURRENT_PROFILE_OBSERVED. Whole-P0-04B provider/browser tests, remote
CI/Security and merge requirements remain separate; do not mark the TODO done.

## Residual risks, rollback and document review

This profile trusts the installed native application's display semantics;
identical cached output cannot prove hidden recomputation. The successful
observation is one run, not a universal renderer or timing guarantee. Another
layout, fragmented invalid intermediate state or `/exit` completion may remain
inconclusive; that must not trigger a broader exception or a second key.
Private in-process capabilities are not a sandbox against arbitrary trusted
process mutation or a promise of physical memory zeroization.

Rollback removes the acceptance-only passive transition and its driver fence
integration together, restoring immediate strict resumed rejection. Preserve
the original menu retirement, display/history/nonce controls and the separate
read-only observational route. No rollback renews a grant or rewrites evidence.
Root/component versions stay unchanged for this test-only scope; packaging and
production policy are not modified. ADR-010/index, CHANGELOG and validation notes
must distinguish this proposal, implementation, synthetic gates and native proof.

Written-spec approval permits drafting the implementation plan, not behavioral
implementation or native execution. The operator must then review the plan and
select its execution method. No new subsystem or general terminal adapter is
authorized by this narrowly scoped extension.

## Related contracts and official references

- [Correlated display](2026-10-19-p0-04b-correlated-context-display-design.md)
- [Correlated menu](2026-10-15-p0-04b-correlated-command-menu-design.md)
- [Read-only post-Enter observation](2026-10-20-p0-04b-post-enter-observation-design.md)
- [ADR-010](../../architecture/ADR-010-browser-automation-boundary.md)
- [Claude Code commands](https://code.claude.com/docs/en/commands)
- [xterm write callback](https://xtermjs.org/docs/api/terminal/classes/terminal/#write)

Official documentation checked on 2026-10-21 describes the command menu/context
display and parsed-buffer callback. It does not define this private acceptance
profile or certify native computation from a callback. No public API, new hook
or native receipt is assumed, and documentation presence is not runtime proof.
