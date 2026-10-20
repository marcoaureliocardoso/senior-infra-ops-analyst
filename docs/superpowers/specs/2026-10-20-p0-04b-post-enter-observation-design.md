# P0-04B passive post-Enter observation

Status: written specification operator-approved on 2026-10-20. The
[implementation plan](../plans/2026-10-20-p0-04b-post-enter-observation.md) awaits
operator review and execution-method selection. Not implemented. No code change
or new native execution is authorized by this document alone. Source baseline:
`d3e98160e4921443ad02e564e89b4d8002601de2`.

## Intent and evidence

Determine whether the isolated native resumed text-turn UI can reach the
existing HISTORY_COMMIT_V1 display shape after one independently owned /context
submission, without changing acceptance or authorizing any later input. This is
a development-only feasibility observation, not a general terminal adapter,
browser workflow, provider test, or proof of native command recomputation.

The consumed baseline attempt observed Claude Code 2.1.302 inside isolation.
Initial context inspection, nonce echo/clear, natural exit and one synthetic
loopback SDK message passed. The resumed context route rejected after eight
acknowledged command bytes and one Enter. It stopped in 11.118 seconds, not at
the 25-second dialogue or 165-second overall deadline. Skill-turn did not run.

The frozen first rejecting row matched completion grammar at the noted
pre-Enter menu position, outside pinned/retired history. A numeric sample was
present, no supported new history commit was found, and the tracker remained
AWAIT_DISPLAY. These closed facts establish neither exact row identity nor
what would have appeared later. No native raw row is available to reconstruct.
The exact-commit grant is consumed; all older grants remain consumed.

The source identifies three independent uncertainties:

- The first Enter may execute the command or only complete its menu selection.
  Write acknowledgement proves transport, not application completion.
- The ordered assessor stops at the first rejected marker. Other unsupported
  rows or a still-rendered command at the input may be hidden behind that row.
- Every pre-Enter completion position enters an immutable inventory. A later
  committed command at the same position remains unsupported by the current
  profile. Waiting alone cannot remove this ambiguity.

External development evidence is the content-free outcome and structural result
named `p004b-offline-d3e9816-*` under the project's
`.review-runtime/p004b-terminal-state` directory. Do not copy raw native content
or the development chat into this specification or Git.

## Decision and alternatives

Add an explicitly selected, mutually exclusive observational mode to the
existing disposable offline harness. Reuse its isolation, owned pre-Enter
handshake, terminal parser, synthetic text-turn setup, supervision and cleanup.
After the one acknowledged Enter, route only to a private read-only observer.
The acceptance route must remain inaccessible in this invocation.

Keeping immediate rejection is safe but cannot answer the later-timeline
question. Directly adding PENDING to acceptance was not selected: diagnostic
position is insufficient authority and compatibility with the final profile is
unknown. A generic sleep, greater timeout, global regex exception, cursor-only
assessment, second key, or catch-and-resume fallback is rejected.

This design does not supersede the pre-Enter-only menu contract or
HISTORY_COMMIT_V1 acceptance. It observes a distinct route. Any later change to
acceptance, history-position rules, key sequence, supported geometry, or
recognition profile requires another explicit design decision.

## Scope, mode selection and components

- `tests/offline-terminal-resume-probe.py` gains the test-only mode
  `--observe-post-enter`, mutually exclusive with `--run-offline`,
  `--audit-isolation`, both content-debug flags and duplicate mode selection.
  Inner dispatch must independently enforce the same separation and actual
  namespace audit. A flag or environment variable alone is not an audit proof.
- Run one synthetic text-turn case only: unchanged initial context handshake,
  one existing SDK invocation against the loopback gateway, then resumed
  observation. Do not run skill-turn or a second case. Preserve max-turn and
  gateway request ceilings; this design grants no increase or repeat.
- `tests/headless_context_driver.py` and its CLI wrapper provide a private
  observer-only seam under the audited scope. Ordinary initial, resumed,
  default/live/provider and content-debug calls retain existing behavior.
- A focused test-only `tests/terminal_post_enter_observation.py` owns ephemeral
  observation state, composed structural classification and terminal outcome.
  Reuse reviewed pure row/numeric/history grammar helpers where suitable; do not
  add a second generic parser or permissive public assessment method.
- `tests/terminal_context_echo.py` provides a narrowly checked private handoff
  from the original live pre-Enter command to the observer. No receipt, nonce
  challenge, row index or caller-supplied diagnostic can construct this handoff.
  Normal submission still destroys its original menu authority at Enter.
- The new module is mounted read-only only into the audited test namespace.
  No Nori component, installed script, production setting, dependency, provider,
  runtime pin, operator preference or package-version change is introduced.

## Handoff and irreversible state boundary

Create the observer only through the mutually exclusive offline mode before
typing. Require the original strict empty baseline, actual case/SDK/resume
offer, live process/helper/controller/scope/run/transition, original deadline,
and independently validated old-history view. Preserve exact eight-byte write
progress, owned echo, private menu correlation and latest-frame checks before
the existing single Enter. A pre-Enter failure terminates normally; it must not
activate observation as a fallback.

Before submission, prepare a sealed private observation binding to the original
evidence, validated history/inventory, numeric baseline, geometry and optional
exact correlated menu reference. This is a lifetime-limited reference to the
already parsed temporary evidence, not a serialized copy or content hash.
Its only consumer is this observer under the same original identities.
Preparation must not freeze the submit boundary prematurely: finalize the menu,
inventory, numeric baseline and frame barrier from the last validated pre-Enter
state, including every consumed writable-wait frame before the Enter byte is
acknowledged. Preserve original evidence identity while updating this boundary.

Activate the handoff only after the same controller records exactly one actual
Enter byte, with eight command bytes and full echo already proven. Reject zero,
partial/extra, boolean, copied, stale, foreign or delayed acknowledgements.
The handoff is single-use. No mode switch after a failure is allowed.

At activation, permanently retire the original command's acceptance path in this
invocation. It must be unable to call display acceptance, bind history, create
a context receipt, construct a nonce challenge, or resume after observation.
Do not catch an acceptance exception and resurrect its command/view. Observation
owns separate read-only lifetime checks against the original process, scope and
case; it cannot depend on treating a revoked acceptance view as valid.
Do not implement retirement by calling existing invalidation APIs that also
close the shared case or destroy evidence needed for those independent checks.
Define a one-way withdrawal of acceptance alone, retaining only the original
read-only guard facts until cleanup. Never reopen a case, renew a scope or use
this separation to keep a failed prerequisite alive.

Process every actual observed frame in order, including output consumed while
waiting for writable Enter. No skipped transition, fresh deadline, rebinding to
a lookalike snapshot, or restoration from serialized metadata is permitted.

## Passive observation contract

After activation, the terminal-input writer must reject every further byte,
including an extra Enter, Escape, Tab, nonce, Ctrl+U, /exit and terminal-generated
responses. Continue only bounded PTY reads, awaited parser processing, snapshots,
independent guard checks and classification. Reuse the existing policy of not
forwarding parser-generated terminal responses. A write attempt is a terminal
failure, not a retry. Cleanup uses process supervision, never prompt ownership.

Each consumed snapshot must first pass cancellation/deadline, monotonic clock,
native/helper/controller/scope/run/transition/case identity, capture/protocol,
authentication/modal and supported buffer/viewport/geometry checks. Keep old
history's exact pinned/retired discipline and numeric conflict tracking. These
checks remain fatal even when a known menu is the first marker on screen.

Then inspect all relevant rows in one composed observational assessment. The
observer may classify only two explicitly known transient forms without stopping:
the exact privately correlated off-cursor menu at its original cell, and the
exact owned command still at its original input anchor with supported cells and
cursor geometry. Neither is an empty input or grants write authority. An absent
pre-Enter menu cannot be learned from later output. Unknown or additional marker
rows, another command, conflicting input, duplicate candidates or unsupported
cells stop immediately; do not ignore the remainder after a known row.

Track disappearance of the original menu and current command echo monotonically.
Once absent, their return is unsupported. Movement, mutation or duplication
ends observation with a classified unsupported outcome. An exact bare /context
history shape replacing the menu at that same cell may be reported only as an
inventoried-cell replacement and ends observation. It is not proof that this is
the same row/widget or a fresh command commit. Never promote that cell.

At the first snapshot whose structural conditions all match the existing
HISTORY_COMMIT_V1 profile, drain already available bounded output and recheck
against the latest consumed snapshot. The new history position, numeric sample
and genuinely empty input must still match; conflicting intervening evidence
must not be erased. A lost/moved/changed candidate ends observation rather than
returning to waiting. No acceptance witness or receipt is created by this check.

The complete profile means one supported new command-history row outside all
original inventory and validated old exclusions, supported empty current input,
no persistent completion/competing marker, complete numeric sample, unbroken
numeric-conflict tracking and all independent guards. It certifies an observed
structural profile only, not internal recomputation, trusted content provenance,
native acceptance or authorization for later input.

Silence, parser completion, elapsed time, a numeric grid, menu disappearance or
empty input alone cannot satisfy this outcome. If Enter only completes a menu,
do not send a second key to discover or execute the next state.

## Outcomes and reporting

Use a distinct closed schema `p004b-post-enter-observation-v1`, not the acceptance
event/result schema. Include literal `acceptance: false` and the mode identity.
Existing acceptance aggregators must reject this report even when its CLI exit
is zero. Never emit passed context_display, resumed context_inspected, nonce,
natural-exit, CONTROLS_PASSED or browser/provider acceptance evidence.

Terminal outcomes are:

| Outcome | Meaning | Next decision |
| --- | --- | --- |
| CURRENT_PROFILE_OBSERVED | Full current profile survived latest-output revalidation | Consider a separate narrowly correlated passive-state acceptance design |
| INVENTORIED_CELL_REPLACEMENT | Bare command-history shape appeared at a forbidden pre-Enter position | Reassess profile compatibility; waiting alone is insufficient |
| UNSUPPORTED_TRANSITION | Mutation, movement, reappearance, unknown row, competing marker, history or numeric ambiguity | Stop and assess the classified limitation |
| DEADLINE | No full profile before the original deadline | Waiting was not demonstrated useful within scope |
| SAFETY_STOP | Independent auth/lifetime/cancellation/process/geometry/protocol guard failed | Stop; no compatibility conclusion |
| SETUP_BLOCKED | Isolation, initial dialogue, SDK or strict pre-Enter prerequisites failed | No post-Enter observation occurred |
| CLEANUP_FAILED | Owned cleanup cannot be proved | Suppress observation detail and report cleanup failure |

The parent returns zero only for CURRENT_PROFILE_OBSERVED after proved cleanup;
all other outcomes return two. Zero means this diagnostic observation completed,
not P0-04B acceptance. No automatic repeat follows any outcome.

Retain at most one bounded summary per resumed observational phase: menu state
(NOT_BOUND, EXACT_PRESENT, DISAPPEARED, CHANGED, MOVED, DUPLICATED, REAPPEARED),
input state (OWNED_COMMAND_ECHO, EMPTY, UNSUPPORTED, UNOBSERVED), commit relation
(NONE, NEW_CELL, PREENTER_INVENTORY, PINNED, RETIRED, MULTIPLE), numeric relation
(ABSENT, BASELINE_EQUIVALENT, DISTINCT, CONFLICT), profile-observed boolean,
outcome and a closed stop category. Stop categories are COMPLETE, SETUP,
AUTHENTICATION, CANCELLED, DEADLINE, OWNER_LOST, PROCESS_EXIT, GEOMETRY,
CAPTURE_PROTOCOL, UNKNOWN_ROW, MENU_CHANGED, INPUT_CHANGED, HISTORY_CONFLICT,
NUMERIC_CONFLICT, PROFILE_LOST, WRITE_ATTEMPT, REPORT and CLEANUP. Relations
describe position/shape only.
Missing facts use UNOBSERVED where defined, otherwise omit the optional field;
do not infer a negative or accept an arbitrary string. Booleans are not integers.
No menu description, coordinate, process/session ID, row text, frame sequence,
exception message, path, hash of content or raw timing trace is exported.

Keep 16 records / 3072 actual JSON bytes per phase and 16384 bytes for the outer
report including final disposal metadata and newline. Base failure/cleanup
records have priority over optional summary detail. An observation or projection
fault cannot fabricate success, delay cleanup, displace a base failure, or fall
back to acceptance. Do not emit per-frame public records.

## Limits, privacy and cleanup

Keep 25 seconds per context dialogue and 165 seconds total with the existing
outer supervision/cleanup allowance included, not added. Use the same original
remaining post-Enter deadline. Keep bounded reads, parser byte limits, operation
cancellation and process-group ownership/reap. No busy loop, extra timeout grace,
version fallback, service update, runtime installation or automatic retry.

Require loopback-only gateway, hidden operator state, dropped capabilities,
synthetic authentication and disposable HOME/config/project/history. Do not read
operator credentials/settings or contact a real provider. Startup confirmations
remain limited to the existing synthetic initial handshake; late authentication
in the resumed observer is always fatal.

Retain exact-row references only in temporary private memory. Existing capture,
SDK streams and native history remain confined to owned disposable storage.
Disable both content-debug modes and all excerpt export. Release references,
close capture/helper/PTY descriptors, reap owned processes and delete owned raw
evidence/history/roots before aggregation/publication. A retained report can
contain only the validated structural envelope after cleanup. Do not claim
physical memory zeroization or erasure of earlier authorized chat copies.

## Verification and acceptance of this development change

Implementation requires synthetic TDD before behavioral code and an independently
reviewed immutable final source. Cover at least:

- CLI/inner-mode exclusivity, default/live/provider/debug unchanged, no automatic
  installed-Claude launch and no installed/staging activation;
- valid strict setup/handoff, no menu path, exact persistent menu/input echo,
  monotonic disappearance, supported later profile and first-outcome stopping;
- missing/partial/wrong echo, Enter count, stale/copied/foreign evidence, owner,
  case/SDK, lifetime, deadline, scope/run/controller and geometry substitutions;
- known menu plus a second unknown row, input draft, duplicates, malformed cells,
  auth/modal elsewhere, menu/input mutation/movement/reappearance;
- invented or reused history positions, pinned/retired history corruption,
  conflicting-then-restored samples and candidate loss after discovery;
- zero post-Enter bytes, including attempted terminal responses and all existing
  nonce/clear/exit writers; exceptions must not reactivate acceptance;
- bounded delayed/fragmented synthetic PTY output, parser completion versus
  application completion, deadline/cancellation, process/helper exit and partial
  capture, with no use of the installed native runtime;
- separate-schema rejection by acceptance aggregation, forged success fields,
  projection failure, report pressure and cleanup failure/disposal ordering.

Run focused tests and the complete package gate on final immutable source, then
resolve independent findings and revalidate proportionally. Record actual skips,
hashes and scope. Synthetic success cannot establish native feasibility.
Any real observational execution requires a fresh exact-final-commit one-shot
grant explicitly naming this mode, one synthetic text-turn case, the unchanged
limits and structural-only retention. Do not consume a grant while writing this
specification or its later implementation plan.

## Risks, rollback and document state

The native renderer may never produce this profile, may need a different key
protocol, or may reuse forbidden positions. The probe can establish a limitation
without solving it. It must not grow into a general recorder or an exception
ladder. Reusing pure classifiers does not make observed text trusted. Private
Python state is trusted-process discipline, not arbitrary-code isolation.

Rollback removes the observation-only mode, handoff, module/mount and synthetic
tests together. Keep original submission/menu retirement, HISTORY_COMMIT_V1,
irreversible acceptance revocation, diagnostics and all safety/cleanup controls.
No consumed grant is restored by rollback.

This specification is indexed from ADR-010 as proposed, not enforced. The
design-only commit updates the changelog truthfully without a version bump.
Written-spec approval permits producing the implementation plan, not executing
it. Obtain plan review and the operator's execution-method choice first.
Implementation must later update ADR/index,
validation notes and changelog with observed behavior, not intentions.
No push, PR, merge, release, staging refresh, remote CI/Security claim or
definitive TODO completion follows from this design approval.

## Related contracts and official references

- [Correlated command-menu design](2026-10-15-p0-04b-correlated-command-menu-design.md)
- [Correlated context-display design](2026-10-19-p0-04b-correlated-context-display-design.md)
- [ADR-010](../../architecture/ADR-010-browser-automation-boundary.md)
- [Claude Code command reference](https://code.claude.com/docs/en/commands)
- [xterm write callback contract](https://xtermjs.org/docs/api/terminal/classes/terminal/#write)

The command reference describes /context, not the private HISTORY_COMMIT_V1
terminal contract. The xterm callback establishes parsed buffer availability,
not native application-command completion. These references grant no authority.
