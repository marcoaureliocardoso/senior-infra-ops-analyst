# P0-04B correlated context-display evidence design

Date: 2026-10-19
Status: Written specification approved by the operator; implementation plan awaiting review. Not implemented.
Baseline: a7f53075d553865af2c3ee1a32727cc8e5e9c286.

## Intent and approval boundary

Make the disposable offline resumed-context test distinguish a numeric sample,
a newly correlated command display and current input ownership. Equal numbers
must not automatically mean stale output, and different text must not by itself
mean a fresh measurement. Keep the original isolation, authorization, input and
disposal controls.

The operator approved investigation, revision of the evidence design and then
this written specification. This permits the implementation plan, not behavior
changes, a native/provider run or delivery. Written-spec approval precedes the implementation plan; plan
approval and execution-method selection precede implementation. A native run
still needs its own bounded exact-final-commit authorization.

## Observed problem

The one authorized a7f5307 offline attempt ended after 10.379 seconds with
OFFLINE_CONTROLS_INCONCLUSIVE. Initial context and the synthetic SDK sample
passed; resumed numeric inspection preceded FRESH_CONTEXT_SIGNATURE_UNCHANGED.
The skill-turn case did not run. Disposal was proved. The grant is consumed.

Synthetic investigation reproduced both a same-value repaint and completion
removal without numeric repaint with that retained rejection profile. It did
not identify which event happened inside the native attempt.

The current signature is a tuple of complete display rows matching three label
families, not a canonical numeric sample. Heading/order changes can satisfy
inequality without changing numbers. A genuine same-value display can fail it.
The raw sticky contextFresh flag includes a matching completion description,
while the owned-command signature correctly projects that menu out. The numeric
reader and the final command guard consequently have different freshness tests.

Exactly the same bytes and final terminal state can produce different sticky
freshness flags when an intermediate clear is exposed by PTY chunk boundaries.
The adapter already awaits parsing; a missing write callback wait is not the
demonstrated issue. Parser erase counters can be chunk-independent, but cached
replay can produce the same counters. No terminal-only observer can prove an
application's hidden recomputation when its observable output is identical.

The signature defense was intentionally added in a077076 to reject restored
stale grids. ADR-010 and the current resumed-history design retain it. This
proposal changes that evidence contract only for the explicit profile below;
it must not be implemented as an unexplained deletion of a guard.

## Alternatives and recommendation

| Approach | Guarantee | Tradeoff |
|---|---|---|
| Keep signature inequality | Existing conservative rule | Legitimate equal-value output may remain inconclusive; text change is still not recomputation proof |
| Correlated current-command display, recommended | A new display transition under the exact owned invocation, with a current numeric sample and independent nonce proof | Requires a recognized display profile and trusts native display semantics; does not prove internal recomputation |
| Native computation receipt only | Application-level invocation/result correlation, if an official detected capability provides it | No generic completed-built-in-/context receipt has been established; unsupported capability remains inconclusive |

Do not invent a hook, assume a prompt hook certifies a built-in command, or
equate SDK usage accounting with the complete /context display. A future native
receipt profile needs separately documented semantics and runtime evidence.

## Evidence meaning and trust model

The recommended profile certifies CORRELATED_DISPLAY, not NATIVE_RECOMPUTED.
It trusts the installed native application to implement its documented local
command and report its current display honestly. It does not defend against a
malicious native binary or distinguish a native internal cache from a newly
computed identical value. Operator approval of this specification explicitly
accepts that narrower property for this offline UI-control test.

This distinction is substantive. If acceptance requires proven internal metric
recomputation, this profile is insufficient and must remain inconclusive until a
supported native receipt exists. It cannot silently lower that requirement.

Terminal text, shape, counters and serialized diagnostics remain observations,
not authorization. Authority still comes from the bounded operator grant and
private invocation capabilities. The closed synthetic case/SDK ledger, actual
stdout descriptor evidence, installed-native identity and current controller
ownership remain prerequisites, not facts inferred from displayed text.

Separate the three facts:

| Fact | What it establishes | What it never establishes |
|---|---|---|
| Numeric sample observed | The consumed snapshot contains valid context numbers | New execution, computation, consent or writable input |
| Correlated display witnessed | The owned current command produced a newly observed committed history/display transition under the recognized profile | Internal recomputation or nonce ownership |
| Input ownership proved | Exact nonce echo, guarded clear and a newer empty input frame in this operation | Provider/browser consent or future-operation authority |

No individual fact substitutes for the others.

## Narrow scope and activation

Apply the new profile only to the audited offline resumed dialogue with a valid
private resumed-history view and completed fixed synthetic SDK witness. Initial
dialogues, default policy callers, production/live/provider routes and browser
operations retain their current contracts. No new public activation flag,
operator setting, environment override, MCP grant or credential transport.

The profile is recognized from the current bound invocation and observed layout,
not a Claude/provider/model/version allowlist. Its installed-native support has
not yet been demonstrated. Presence of xterm or a parser API does not establish
it. Missing, ambiguous or conflicting evidence stays inconclusive; there is no
fallback from failed resumed correlation to signature inequality or cursor-only
eligibility. No claim that this design will pass the next native attempt.

## Concrete display profile: owned new history commit

The first profile is HISTORY_COMMIT_V1. It uses the application's newly displayed
current-command history under the existing owned command, not an erase counter
or an unqualified string match. All conditions are required:

1. The original strict baseline, resumed offer/view, native/helper/controller,
   scope/run/transition and deadline are live and exact. Authentication, modal,
   forbidden UI and geometry checks remain in force.
2. Exactly eight /context bytes have concrete write acknowledgements and the
   current anchor has echoed the exact command. Exactly one actual Enter byte
   is then acknowledged. Pre-Enter writable waits keep updating the concrete
   boundary and validating the same owned command; no observation before that
   acknowledgement can satisfy the post-Enter witness.
3. A later consumed snapshot contains exactly one new supported /context
   history row outside the current input and validated old-history exclusions.
   It must be absent as a current-history candidate throughout the original
   baseline and consumed pre-Enter frames. A pre-existing, pinned, retired,
   relocated or menu-bound row cannot be promoted. No caller-supplied row index.
4. The same snapshot has a supported empty current input anchor, no competing
   unowned marker, no persistent completion and a complete valid numeric sample.
   One ordered composed assessment checks every remaining row. A disappearance
   of the completion or a cleared input alone never constitutes a display commit.
5. Post-Enter complete numeric observations must not contain a conflicting
   transition that is discarded to manufacture this witness. Baseline-equivalent
   samples while awaiting a commit are not evidence. Once a distinct complete
   sample is observed, a return to the baseline or another distinct sample before
   binding is ambiguous and rejects this conservative profile. This preserves
   the existing transient-change-then-restored-old-grid negative control.
6. Before consumption, drain available output and revalidate against the latest
   consumed snapshot. The new row, sample and empty anchor must still match their
   candidate; loss, duplication, movement, conflicting numeric sample, owner
   change or other invalidation revokes, rather than rebinds or retries.

New command history plus a baseline-equivalent numeric sample is acceptable
only under all these conditions and the explicit trusted-native display
assumption above. It is a correlated reading, not proof that the numbers were
recomputed. If native output replays identical bytes while satisfying this full
current-invocation profile, terminal observation cannot distinguish that hidden
case. That is a disclosed limitation, not an anti-replay guarantee for native
content. Private witness reuse across invocations is independently prohibited.

An empty display without new command history, a fullscreen layout that does not
emit such history, or an ambiguous old/new row identity is unsupported for this
profile. Do not add a permissive zero-history branch to make it pass.

## Private capability and sample lifecycle

Introduce one private, non-serializable display witness, bound to the actual
owned command, original scope/run/state/helper/native/controller/transition,
post-Enter boundary, deadline, new history row and current measurement identity.
Only the owning coordinator can issue it after the profile passes. Public
constructors, dictionaries, copied attachments, row strings, terminal control
sequences and diagnostic records cannot mint or restore it.

Lifecycle: PRE_ENTER -> AWAIT_DISPLAY -> CANDIDATE -> CONSUMED, with terminal
REVOKED available throughout. Candidate observations do not authorize input.
The operation consumes the witness once to bind the current context/history
receipt; ordinary nonce eligibility then still has to pass independently.

Use a pure numeric observation that shares the existing parser's validation and
supported display grammar but does not call the sticky freshness observer.
Identity includes the parsed free/buffer values at their supported precision,
derived used percentage and bound display geometry; it does not assume an
absolute context capacity. Canonical numeric equality is not a freshness test.
Raw snapshots remain intact. No screen blanking, synthetic row insertion or
emulator reset is permitted to create evidence.

Preserve the original current-context receipt, old-history retirement and
nonce/clear/exit invariants. Do not let a new profile restore retired old rows.
The witness is not a generic row exclusion or InputOwnershipProof. Continued
use must revalidate its bound history and measurement while allowing only the
existing controlled current-input normalization for nonce and exit writes.

## Integration and observation

One authoritative resumed-context coordinator must perform the evidence checks
used by both bind_history and the resumed composed assessment. Do not fix one
guard while leaving the other dependent on signature inequality. Avoid a second
permissive parser or a diagnostic-only reconstruction of acceptance.

The driver must wait for a valid correlated-display candidate, not merely for a
sticky context percentage. Keep context_numeric as numeric observation only.
For this resumed route, emit passed context_inspected only after display binding
and current numeric validation; a new content-free context_display checkpoint
records that bounded display proof. Existing nonce checkpoints remain separate.
The case aggregator must require this resumed display checkpoint as well as the
existing context/nonce/clear/cleanup/exit proof. A preliminary numeric observation
cannot make the case complete.

Use closed failure checks for missing/ambiguous display evidence and unstable
samples in the existing four-field command diagnostic. Retain legacy labels
for old records. New JSON observation labels never become capabilities.
Optional diagnostic loss cannot change an existing decision; loss of required
authoritative evidence cannot be treated as optional or silently bypassed.

No parser-observer production change is required by HISTORY_COMMIT_V1. Any later
parser profile is a separate design, not an implicit fallback. A PTY read/frame
count, timeout, silence, onWriteParsed notification or erase event alone is never
command completion. The existing engine continues to await parsing callbacks.

## Fragmentation, privacy and operational bounds

Numeric parsing and profile evaluation must not depend on seeing a temporary
clear between PTY chunks. Equal final values are allowed only under the
independent current-command witness. Frame progression is a monotonic ordering
check, not the authority to create the witness.

Existing irreversible old-history/auth/geometry/lifetime guards remain active
for every consumed snapshot. If fragmentation exposes a loss that those guards
already revoke, the operation stays inconclusive; do not coalesce past it to
restore authority. This design does not promise compatibility with every
renderer or make every fragmentation pattern successful. It requires no unsafe
acceptance under any pattern and chunk-insensitive numeric interpretation.

Keep 25 seconds per context dialogue, 165 seconds overall, at most two cases,
the existing SDK limits, stop-first-inconclusive, original cancellation/deadline
and identity-checked cleanup. No extra Enter, Escape, Tab, clearing key or retry.

Keep 16 diagnostic records and 3072 bytes per phase, and 16384 bytes for the
complete outer report including final newline/disposal evidence. A small display
checkpoint must fit those limits; no increase is authorized. Persistent output
contains only bounded closed labels/numbers/booleans and existing percentages,
not new raw rows, signatures, prompts, nonces, transcripts, SDK streams or secrets.
Temporary raw evidence/history is disposed before aggregation as before. The
separately authorized debug options and their retention rules are unchanged.

## Required validation

Use author-owned TDD and one independent read-only review, followed by an
immutable complete package gate on corrected source. The later plan must cover:

- Equal-value legitimate display with the full owned new-history commit, and
  changed-value legitimate display under that same profile.
- Completion-only/input clear with old grid, stale/static grid without a new
  history commit, pre-Enter-only numbers without a post-Enter display commit,
  and unsupported zero-history UI. Equal cached-looking numbers plus a full
  current display witness have the explicitly narrower meaning defined above;
  a test must not label that same observation as proven native recomputation.
- Cosmetic heading changes, reordered numeric rows, cursor noise or arbitrary
  output without a current witness; none creates one.
- Transient changed sample followed by baseline restoration, conflicting
  complete samples, incomplete/ambiguous numeric values and post-bind mutation.
- Old, pinned, retired, duplicated, moved, overlapping or forged history rows;
  changed command, wrong phase, missing/partial echo or invalid write counts.
- Forged, copied, serialized, replayed, expired or foreign-scope witness, and
  owner/helper/native/controller/session loss or substitution.
- Candidate loss during drain/writable wait, cancellation/deadline/auth/menu
  transition, revocation without restoration, and no input after rejection.
- Unchanged nonce protocol: 16 non-submitted characters, exact echo before one
  Ctrl+U, a newer empty frame and one consumed exit proof.
- Equivalent chunkings of recognized displays, including identical-byte
  clear/repaint batches, plus conservative rejection of invalid intermediate
  owned-history states. No raw parser event is accepted as a computation receipt.
- Primary guard/composer/driver/nonce/exit agreement, required aggregation
  checkpoint, optional-observer failure, closed schema and complete report bounds.
- Unchanged initial/default/live/provider behavior and no native/operator-state
  access during synthetic tests. A cached native replay is explicitly outside
  the recomputation claim; no test may falsely claim to distinguish identical
  observations by labeling one fixture "fresh" and another "stale".

Synthetic success does not establish native support. After implementation,
review and the complete package gate, request a separate one-shot exact-commit
offline authorization to observe the actual profile. Unsupported native layout
still stops inconclusively. Provider/browser/remote CI/Security and merge gates
remain separate; no definitive TODO completion follows from this specification.

## Documentation, compatibility and rollback

Root/component versions remain unchanged for the proposed test-only scope.
Implementation must update ADR-010, its index, CHANGELOG and validation notes
with actual behavior/evidence. This specification would narrowly supersede the
different-signature requirement for the recognized resumed profile and the
earlier blanket prohibition on equal-grid evidence, not for other callers.
Pending proposal links must not describe it as implemented or accepted.

Revert the private witness/coordinator, resumed driver and aggregator integration
together to restore the current conservative signature contract. Preserve the
legacy observer's readable labels and all old evidence/consumed-grant markers.
Rollback cannot renew execution authority or change a prior inconclusive result.

## References and evidence

- [ADR-010](../../architecture/ADR-010-browser-automation-boundary.md)
- [Owned context echo](2026-10-13-p0-04b-owned-context-echo-design.md)
- [Correlated completion menu](2026-10-15-p0-04b-correlated-command-menu-design.md)
- [Resumed-history view](2026-10-17-p0-04b-resumed-history-view-design.md)
- [Claude Code commands](https://code.claude.com/docs/en/commands)
- [Claude Code hooks](https://code.claude.com/docs/en/hooks)
- [xterm terminal API](https://xtermjs.org/docs/api/terminal/classes/terminal/)
- [xterm parser hooks](https://xtermjs.org/docs/guides/hooks/)

Construction evidence remains outside Git under
`.review-runtime/p004b-terminal-state/`: p004b-offline-a7f5307-outcome.md,
p004b-same-value-freshness-findings.md and the three synthetic structural result
files named there. Those records establish the investigation, not implementation
or a supported native receipt. Current third-party documentation is not proof of
an installed runtime capability; it must be checked again when relevant.
