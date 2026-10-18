# P0-04B offline resumed-history view design

Status: specification and plan approved; inline implementation on the isolated branch, final review/package gate pending.
Native/provider/browser acceptance is not established or authorized by this artifact.
Source baseline: `b5e0e555871f7cebaa61acf55c30a104847ca37d`.

## Intent and observed evidence

Keep the existing initial-dialogue -> SDK -> resumed-dialogue offline regression.
Distinguish expected synthetic history from the current editable input without
transferring old input ownership, consent, credential authority or native proofs.
The target is the disposable test harness, not arbitrary production sessions.

The single authorized baseline attempt on 2026-10-17 was inconclusive under
runtime 2.1.301. The initial dialogue inspected 16% context, completed nonce
echo/clear and exited naturally. The text SDK step exited zero with one loopback
message. Resume stopped at `prompt_ready`, before the next owned `/context`.
Both initial and failure snapshots classified the actual rejecting row as
`OTHER_CAPTURED_ROW / UNRECOGNIZED_SHAPE / SDK_TEXT_PROMPT_SHAPE`.
This is exact public-fixture display classification, not a provenance proof.
The skill-turn case did not run. Both leaders were reaped and disposable roots
removed; helper close separately reported TERMINAL_DEADLINE_EXCEEDED.

Structural evidence outside Git: `p004b-offline-b5e0e55-structural-result.json`
and the consumed-grant marker `p004b-offline-b5e0e55-attempt.json`, under the
project's `.review-runtime/p004b-terminal-state/`. No rejected native row was
retained, exported or reconstructed. The runtime version is evidence, not a pin.

Source and eight pure-cell checks establish two different barriers. The current
SDK text fixture blocks passive readiness; a measurement-prefixed fixture can
pass readiness yet still fail strict active assessment. Old `/context` history
can also be the active assessor's first rejection while the SDK prompt is the
readiness evaluator's first rejection. Changing a prefix or timeout is not a fix.

The official CLI contract supports resuming a specific conversation and
structured session/result output. It does not establish the harness's private
terminal ownership. Existing receipts intentionally bind one native process,
scope, transition, terminal, deadline and frame progression.

## Decision and alternatives

Introduce a private case-completion ledger and a fresh resumed-history view.
The ledger attests only completed, fixed synthetic actions performed by the
trusted harness. The view can exclude narrowly identified historical marker
rows from one shared assessment; it never authorizes a write by itself.

A single interactive process would avoid the cross-process boundary, but would
replace the SDK-plus-resume subject of this regression and require a different
synthetic-turn controller. It is not selected. Cursor-only parsing, diagnostic
shape labels as authority, regex-only exemptions, replaying old receipts and
fresh-session substitution do not meet this design's coverage/safety contract.

This specification refines the blanket pre-existing-history rejection only for
the audited offline caller. The default/live policy and callers without the new
private capability remain strict. Existing owned context/menu/nonce/exit proofs
remain required, with the composition rules below.

Keep at most two cases, 25 seconds per context dialogue and SDK process, the
existing SDK `--max-turns 4`, and the loopback gateway's rejection beyond four
messages per case. Keep the original 165-second enclosing run ceiling; all view
binding and stream validation consumes that budget. No child relaunch, extra
Enter, alternate key or automatic case/experiment repetition is introduced.

## Trust, scope and privacy

- The sole issuer is the existing isolated offline case supervisor after its
  namespace audit: loopback only, hidden operator state, dropped capabilities,
  disposable HOME/config/project/history and the original enclosing timeout.
- Use private branded objects and identity registries in the trusted Python
  process. JSON, event files, diagnostics, environment flags, CLI options, saved
  identifiers, provider messages and screen text cannot mint or activate a view.
- Bind each case to its original live supervisor and disposable-root identity,
  case kind, generated native session, fixed invocation descriptors and phase.
  The text and skill cases cannot exchange witnesses or views.
- Bind a new view to the fresh terminal, native process, scope, run owner,
  transition, current deadline and parsed frame sequence of the resumed dialogue.
  No prior OfflineProbeScope, ContextEchoReceipt or InputOwnershipProof transfers.
- A completion fact may outlive the completed process; no permission does.
  The new scope uses its existing dialogue budget, while the original enclosing
  165-second supervisor deadline remains authoritative and cannot be renewed.
- A changed root, session, case, invocation, owner or phase invalidates the
  preparation. A view is offered once to one resumed dialogue and never replayed.
- The supervisor rechecks its owned root identity before offering the view and
  through the driver's concrete-write liveness boundary. A missing, replaced,
  linked or differently owned root revokes the case; cleanup still checks the
  original identity independently. Pure profile/stream parsing does not perform
  those filesystem checks or substitute supplied JSON for the supervisor.
- Retain only fixture kinds, bounded counters/geometry and private identity
  bindings in the new ledger/view. Session values stay inside existing disposable
  execution state and are not exported. Do not retain transcript, observed prompt,
  hashes, credentials or raw row copies as new continuity artifacts.
- Public synthetic prompt constants in source are fixtures, not captured input.
  Existing transient terminal buffers/raw capture remain under their original
  disposal rules; this design adds no content-debug or excerpt permission.

This is trusted-process identity discipline, not a sandbox against arbitrary
same-process code mutation or a physical-memory-zeroization guarantee. The native
executable and supervisor are trusted to execute the supplied invocation; terminal
content, model output and parsed SDK events remain observations, not instructions.

## Completed-action and SDK witnesses

The case state advances monotonically:

`CREATED -> INITIAL_COMPLETE -> SDK_VALIDATED -> VIEW_OFFERED -> FINISHED`.

Any failure becomes terminal `REVOKED`. There is no reset, alternate route or
second offer in that case.

INITIAL_COMPLETE is a sealed result produced by the actual owned controller,
not by parsing its reduced event file or diagnostic success flags. Issue it only
after the fixed `/context` command's checked edit/submission, fresh numeric
observation, nonce echo/clear, complete owned `/exit`, natural native exit and
successful native/helper cleanup. It records fixed command kinds and completed
byte/Enter counts, never the nonce or original proof objects. An ordinary zero
exit, public dictionary or fabricated `exit: passed` event is insufficient.

The supervisor's SDK launch witness binds that completed case, its exact session
and fixed invocation descriptor to the child actually launched. A pure bounded
stream validator produces facts; it cannot independently issue a capability.
Both the real child result and stream facts are required:

- One matching main-session `system/init` and one matching successful terminal
  result, in order; no contradictory session, duplicate completion, malformed or
  oversized stream, or events continuing tool execution after completion.
- Text control: no tool calls or tool results, including nested calls. Native
  advertised tool names are bounded metadata, not permission. Exit zero alone
  is insufficient; the existing tool-required measurement evaluator cannot be
  treated as a valid zero-tool control validator.
- Skill case: exactly one `Skill` call with the existing exact
  `skill=context-continuity` input and its successful matching result, no other
  or nested tool calls. Reuse the existing semantic checks where applicable.
- No session identity or lifecycle fact is inferred from assistant prose, a
  rendered history line, or the existing `SDK_TEXT_PROMPT_SHAPE` diagnostic.
- Failure stops before launching the resumed dialogue. Raw SDK files remain
  disposable and are removed before aggregation, as today.

Keep the current text fixture. For the offline skill case, use this complete
short source fixture: `P0-04B synthetic. Invoke Skill(context-continuity) once; reply P004B_SKILL_OK. No browser.`
It preserves the requested operation and fits the existing 120-column transport
with ordinary prompt padding. This is an implemented offline fixture change, not
evidence that a particular native renderer will display it without wrapping.
Tool-call validation, not the natural-language request alone, proves the skill
step. Live/provider-backed fixture prompts remain unchanged.

## Binding the resumed view

After validated SDK completion, offer one pending view to the exact controlled
resume invocation in the same disposable project/session. Validate that offer
before native launch. Bind its rendered view only after observing a fresh,
supported resumed frame with no pending authentication, startup menu or modal.

Expected history is limited to the completed initial `/context`, completed
initial `/exit` and that case's fixed SDK prompt. Each kind has at most one
visible instance. An expected row may be absent at initial binding, but cannot
later appear as a newly adopted history row. No new template is learned from
the screen. An ordinary empty screen still uses the same audited offer; it is
not an escape to the passive controller.

For each present historical row require the complete exact source token/prompt,
one prompt marker, supported one-cell rendering, supported prefix/tail padding
and a captured non-cursor location. The initial supported profile is a complete
single physical row in the existing 120-column cell transport, with ASCII-space
indentation and ASCII-space/NBSP prompt padding. Tabs, wide cells, format/control
characters, truncation, ellipses, wrapped/continuation rows and multiple markers
are not accepted by this profile. Unknown native layouts remain inconclusive.
No English UI description, native version or absolute context capacity is pinned.

Store only the fixture kind and bounded row/marker/padding geometry needed to
reconstruct that public profile. Do not copy the observed row into the ledger.
Duplicated kinds, unknown marker rows, current-row history, suggestions, drafts,
ambiguous input or unsupported geometry reject binding. Ordinary non-marker
screen data remains subject to existing auth/menu/numeric checks; the view does
not certify assistant prose as harmless or make it a new instruction source.

The remaining current input must pass the existing supported empty-anchor and
raw freshness rules at the actual cursor. A valid view only explains the
otherwise competing historical rows; operator authorization and new checked
command execution remain independent prerequisites.

## Lifecycle and composed assessment

The view has monotonic `PENDING -> BOUND -> POST_SUBMIT -> FINISHED` states,
with terminal `REVOKED` available from every live state.

While BOUND, including every consumed frame before the new `/context` Enter,
all pinned history profiles and geometry must remain exact. Disappearance,
movement, replacement, duplication, a new previously absent history kind,
viewport/buffer change or owner/lifetime loss revokes the view irreversibly.
Do not restore it when the expected screen later returns.

POST_SUBMIT begins only after the actual one-byte Enter acknowledgement of the
new fully echoed owned `/context` command. Each old pinned history row may then
remain exact or disappear once and become permanently retired. No movement or
re-binding is permitted. A retired or initially absent old history kind cannot
reappear under this view. Retirement grants no input; fresh numeric observation
and all post-command input/receipt gates still have to succeed.

A newly controlled command/history row must be justified by its own current
command proof, not by resemblance to a retired template. Ambiguous old/new row
identity or overlap between independently claimed exclusions rejects the
transition. Do not promote a baseline row into a fresh ContextEchoReceipt.
This conservative rule may expose another native layout incompatibility.

One capability-aware evaluator composes validated resumed-history exclusions
with the existing pre-Enter menu correlation or post-command ContextEchoReceipt.
It runs the underlying ordered assessment once over the same consumed snapshot
and returns the actual remaining rejection. Callers cannot submit arbitrary row
indices. Keep raw snapshots intact; never blank rows or alter the terminal model.

Use this composed path at resumed readiness and baseline construction, every
partial command write/writable wait, command echo/Enter, fresh-context/history
binding, nonce construction and normalization, pretype/echo/clear checks, final
proof consumption and every partial `/exit` write. Initial-dialogue/default/live
paths without a view keep their prior behavior.

The new view cannot extend the completion-menu exception beyond its existing
pre-Enter phase, authorize an `/exit` menu, create a nonce proof, or turn an
unchanged numeric grid into fresh evidence. Raw policy transition/freshness
barriers remain authoritative. Context-signature projection keeps only its
existing proven menu behavior; history recognition is not new numeric evidence.

Auth/menu/modal transitions, cancellation, deadline expiry, protocol failure,
process/helper loss, owner substitution or a failed composed assessment revoke
the view and every dependent current command/nonce proof. After revocation no
additional input, fallback key, state repair, alternate parser or native retry
is allowed. Cleanup remains independent and best-effort under the existing rules.

## Components and observation

- A focused test-only resumed-history component owns the branded case witnesses,
  one-shot view offer, public fixture profiles and view lifecycle. Its validator
  separates pure bounded event/cell classification from trusted supervisor
  liveness checks. The classifiers have no file, network or logging effects.
- The offline supervisor owns actual SDK process/stream IO and identity-checked
  disposal. It alone joins the owned initial-completion fact, SDK witness and
  exact resumed invocation. Merely calling a pure validator cannot activate input.
- The selected driver emits the sealed initial completion only after cleanup,
  validates a pending view before launch and binds/rechecks the fresh resumed
  view before concrete writes. Proof events remain reduced and unchanged.
- Input policy, owned context echo and nonce/exit components share one composed
  evaluation; no parallel permissive parser or caller-controlled exclusion list.
- Raw diagnostic readiness remains a raw observation. If a view is applied,
  retain an optional closed `resumeViewDecision` of `VALID` or `REJECTED` rather
  than rewriting raw UNSUPPORTED_MARKER as READY. No field is emitted without
  this route. Add a per-case boolean `validSDKSample` for the stream witness.
  The view diagnostic cannot grant input or success. Only the internal sealed
  SDK witness controls continuation and case success; its serialized boolean is
  a reduced result, not a capability that deserialized data can recreate.
- Resume failures use a finite closed category for scope, SDK witness, layout,
  replay or revocation; no raw exception/session/content enters a reason code.
  Observer loss must not change the original decision or cleanup.
- The namespace mounts only the additional reviewed test module read-only if
  needed, following the existing individual-file allowlist. No broader host
  directory, config, credential, dependency or provider mount is introduced.

The implementation plan defines private signatures and collector failure-code
wiring under these contracts. Keep diagnostics at 16 records/3072 bytes per
phase and the complete outer report at 16 KiB. A bounded report that cannot
represent required acceptance evidence is inconclusive, not an implicit pass.

## Verification and acceptance

Use synthetic TDD, then controlled PTY integration and one independent scoped
review. Required coverage includes:

- Missing/fabricated/replayed completion, SDK witness or offer; foreign case,
  root, session, invocation, terminal, native owner, scope, transition and frame.
- SDK text success with zero calls; wrong session, exit-zero failure result,
  missing/duplicate init/result, malformed/oversized stream, unexpected/nested
  calls, late calls and invalid skill result. No after-process launch on failure.
- Exact text/short-skill history, optional completed control rows, history-free
  resume and differing valid history positions; valid shapes without a witness
  still fail under the existing default contracts.
- Unknown/current-row history, duplicates, suggestions, drafts, auth/menu/modal,
  unsupported padding/width/format, wrapping and truncation. Failure sends no key.
- BOUND disappearance/movement/replacement; permitted post-Enter retirement;
  forbidden reappearance, initially absent kind appearing, overlap with new
  command history, changed geometry and restoration after revocation.
- Actual echo/Enter counts, correlated menu plus resumed history plus fresh
  command receipt, actual other-row rejection, unchanged old numeric grid,
  nonce echo/one guarded Ctrl+U/new empty frame, and partial `/exit` failure.
- Collector/debug on/off or loss must preserve decisions and cleanup. No new
  text, hashes, identifiers or prompt excerpts in output; limits remain enforced.
- Existing signal/cancellation, isolation, disposal, strict default/live,
  installed/staging and native input/receipt regression suites remain green.

Run the complete package gate on the final immutable source, fixing reviewer
findings before the matching final gate. Record actual reviewed/gated hashes,
skips, rulings and evidence. A fake UI pass is not a native compatibility result.
No new dependency, package/component version or installed behavior is required.

A future native attempt needs a fresh exact-final-commit authorization for the
fixed synthetic prompts and existing `/context`/nonce/Ctrl+U/exit protocol,
synthetic-key confirmation, disposable history, structural-only diagnostics,
25 seconds per dialogue, 165 seconds total, at most two cases, first-inconclusive
stop and no repetition. This document authorizes none of those actions.

## Residual risks, documentation and rollback

Only the text-turn resume rejection was observed natively. The short skill
fixture, history retirement, later redraws, post-resume fresh numeric grid and
exit remain unobserved. A safely unsupported layout may still stop the next
experiment. Do not broaden recognition, keys, budgets or retention to conceal it.
Consumed grants and deleted evidence cannot be recovered by rollback.

Record the local implementation in indexed ADR-010, CHANGELOG and validation
notes, separating enforced synthetic behavior from pending review/package/native
acceptance. Revert the view/witness integration and
offline short-skill fixture together to restore the baseline strict resume
rejection, preserving owned command/menu/nonce/debug/disposal protections.

Production/provider/browser acceptance, remote CI/Security, push/PR, main merge,
release and definitive unversioned TODO completion remain independent gates.
The operator approved this written specification and then selected native/inline
execution of the [implementation plan](../plans/2026-10-17-p0-04b-resumed-history-view.md)
on 2026-10-18. That development approval does not authorize a native experiment
or any external delivery action. Final review/package verification remains
pending at this candidate; real-Claude acceptance needs a fresh final-commit grant.

## References

- [Official programmatic session continuation](https://code.claude.com/docs/en/headless#continue-conversations)
- [Official CLI reference](https://code.claude.com/docs/en/cli-reference)
- [Pinned input proof](2026-10-09-p0-04b-pinned-input-proof-design.md)
- [Owned context echo](2026-10-13-p0-04b-owned-context-echo-design.md)
- [Correlated command menu](2026-10-15-p0-04b-correlated-command-menu-design.md)
- [ADR-010](../../architecture/ADR-010-browser-automation-boundary.md)
- [Validation notes](../../../tests/validation-notes.md)
