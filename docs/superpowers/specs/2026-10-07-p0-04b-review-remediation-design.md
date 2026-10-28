# P0-04B review remediation: freshness, cancellation and approval deadlines

Status: operator-approved written specification at commit `1084a40`;
implementation plans awaiting operator review. No behavior has been changed.
Source baseline: `01414cb192da4c2e9947463f4fb810d46a3d0972`.
Working branch: `p0-04b-browser-automation` in its existing isolated worktree.

## Intent and authority

Correct the three material findings from the final headless-adapter review:
false input freshness, detached-process cancellation gaps, and browser effects
using frozen or extended approval lifetimes. Preserve useful infrastructure UI
operation through an active, explicitly approved envelope; expiry must not
silently remove normal capability while the same approval is still valid.

The operator authorized extending the formerly test-only scope to production
approval-expiry enforcement, then approved the conservative design: retain the
original deadline, recheck before each effect, permit cleanup after expiry and
treat results received after expiry as inconclusive. This document supersedes
the old test-only exclusion solely for that production correction and its
necessary shared adapter/state boundaries. Other exclusions remain unchanged.

No provider request, actual operator credential/configuration access, native
Claude repetition, production UI operation, installation, push, PR, merge,
release or definitive TODO completion is authorized. Tests use repository-owned
synthetic fixtures, injected clocks and disposable state only.

## Evidence and broken boundaries

The review at `bf0ccbc` recorded three Important findings and no Critical or
Minor finding. Its bounded whole-branch passes were not a complete historical
security certification. See [the evidence record](../../../tests/validation-notes.md#independent-final-adapter-review-and-remaining-material-findings).

| Boundary | Observed defect | Required ownership |
|---|---|---|
| Input freshness | Moving the cursor through an unrelated status row latches freshness for an unchanged old prompt | Selected Python input policy |
| Cancellation | Default SIGTERM/SIGHUP can skip cleanup of detached native/helper groups | Selected entrypoint and every owned child lifecycle |
| Approval expiry | Frozen time and reparsed expiry permit later effects after the original approval ends | Runner, original binding and concrete adapter dispatch |

The production trace is available in current source:

- `browser-binding-store.mjs` retains the original envelope and deadline through
  pending-to-active activation.
- `browser-workflow.mjs` intentionally excludes absolute expiry from the
  invocation fingerprint, retaining the requested duration. Reinterpreting the
  same CLI later must not extend the stored grant.
- `browser-runner.mjs` freezes `now`, passes the reparsed envelope to workflow
  execution/validation and awaits reference resolution/startup before dispatch.
- The sibling `executeRunnerStep` has equivalent waits after its initial check.
- Playwright link clicks await a download-attribute read before clicking;
  adapter inspection can await navigation before reading. Interception and
  screenshot-to-artifact transitions also introduce later dispatch boundaries.

This source trace establishes why changing only the workflow's initial timestamp
is insufficient. It does not establish a cause for the inconclusive native
Claude 2.1.293 control or for historical paid failures. Those raw captures are
gone and will not be reconstructed.

## Decision and alternatives

Use one invocation-owned approval-lifetime guard shared by the runner and its
selected adapter, anchored to the stored grant. Independently repair input
freshness and managed-signal cleanup without widening terminal readiness.

A runner-only guard would have a narrower admission contract, but cannot cover
the observed intermediate adapter awaits or later intercepted requests. It is
not the selected per-effect contract. Checking only after a call can classify a
late result, but cannot prevent the next unauthorized dispatch. Resetting a TTL
at parser, adapter, validation or retry boundaries is not permitted.

No new browser provider, global service, permission server or operational
gateway is introduced. Use existing binding locks, origin checks, effect policy,
adapter discovery, private IPC, cleanup and closed result vocabulary.

## Original grant and clock contract

The authoritative approval is the exact pending record selected by session,
operation and invocation fingerprint, and the same record after activation.
Use its original immutable envelope/deadline for execution and validation.
The later request describes the bound steps; its parser-derived expiry cannot
authorize or prolong them. Reject inconsistent stored expiry representations.

Create one trusted clock reader per top-level runner invocation:

- Preserve existing numeric `dependencies.now` as a constant test clock.
- Accept a callable injected clock for deterministic clock-advance tests.
- Without injection, sample current time on every check; never capture one
  `Date.now()` value as the entire invocation's clock.
- Require nonnegative safe-integer samples. Invalid or backward samples make
  authority unproven and fail closed; they cannot resurrect or renew a grant.
- At `now >= originalExpiresAt`, no new operational dispatch is authorized.

Injection remains an in-process trusted testing seam, not a CLI flag, environment
override, model-supplied value or new credential transport. Fingerprint equality
across parser timestamps and exact requested-duration binding remain unchanged.

## Runner-to-adapter lifetime interface

Pass a synchronous operation-lifetime assertion through the existing adapter
factory options. It is bound to the original grant and invocation clock, returns
normally only while live, and otherwise throws a closed expiry/clock failure.
It proves lifetime only; it never replaces role, effect, origin, identity,
credential, capability or native-approval checks.

The selected operational adapter must explicitly expose that this assertion is
installed and enforced. Missing or unsupported enforcement blocks the route;
there is no silent no-op guard or legacy fallback. Repository-owned test doubles
must implement the same contract. Standalone adapter diagnostics without an
installed guard remain unproven and cannot be selected as an operational route.
Do not pin a browser/runtime version to manufacture this capability.

The assertion belongs at the concrete dispatch boundaries, not only at method
entry. Preserve existing origin wrappers and add checks immediately before
browser API, sensitive read, protected-reference and artifact dispatch. When an
intermediate operation is awaited, check again before the next dispatch.
No `await` may sit between a final assertion and its direct call expression.

Required runner checks cover activation, execution/validation adapter startup,
each execution/validation-preparation step, protected-value resolution and its
consumer, final expectation resolution, final verification and the single-step
independent validator. Cover both workflow and legacy read-only entrypoints.

Required adapter checks cover page navigation, locators, reads, fill/select,
click/submit, upload/materialization, screenshot acquisition and artifact capture,
and each request-interception dispatch. In particular:

- Check again after a link's download-attribute await and before clicking.
- Check again after inspection navigation and before the sensitive read.
- Check again after screenshot acquisition and before artifact capture.
- An intercepted request arriving after expiry is aborted, not continued,
  fetched or fulfilled; dispose any already-acquired response during cleanup.
- Cleanup, route abort and owned resource disposal never need renewed authority.

These checks use documented runtime APIs. Narrow per-call timeouts to the
remaining lifetime where the detected API supports it; never enlarge the
existing native/workflow deadline or introduce automatic retries.

## In-flight results and outcomes

Expiry is a dispatch boundary, not an atomic transaction at a remote device.
An API dispatched while live may auto-wait, complete or produce a remote effect
after expiry. This design does not promise to recall or roll back such a call.
Do not claim that an assertion alone cancels a runtime's internal work.

Recheck after asynchronous completion. A result received at or after expiry is
inconclusive, including a late successful independent verification. Do not
report `STEP_COMPLETED`, `WORKFLOW_VALIDATED`, reconciliation or completed
authentication from expired authority. Permit no subsequent operational call.

Before any possibly persistent effect has been dispatched, expiry returns a
closed denial such as `OPERATION_EXPIRED`. After a successful or ambiguous
possibly persistent action, expiry returns `OUTCOME_UNKNOWN` with validation
required. Preserve existing conservative fill/select/click/submit persistence
tracking. Further independent validation or compensation needs fresh matching
authority; neither is automatically attempted with the old envelope.

The legacy single-step path follows the same late-result rule without acquiring
authentication/mutation privileges. Missing or failed completion/reconciliation
writes cannot be ignored as a successful validated outcome.

## Binding consumption and cleanup

Consume the owned original one-shot binding on every success/failure/cancellation
path that acquired it, including after expiry. Current-time reads filter expired
records; that filtering alone is not physical consumption. Cleanup must remove
the owned pending/active/call records without using a historical timestamp as
operational authorization. Use the existing lock and safe state-file discipline.
Do not delete a later, different operator approval sharing an operation ID.

Close execution, validation and artifact resources unconditionally. Clear
temporary credential/value references. Expiry never authorizes new artifacts,
retention, transcripts or raw diagnostic output. Cleanup failure overrides
apparent success and cannot claim a verified empty root or consumed binding.

## Test-only input freshness correction

Track the relevant input candidate and controlled transition separately from
transient cursor visits to other rows. A split status redraw that moves away
and back cannot refresh an unchanged old candidate, even after settling.
An unrelated row's text/cursor changes do not contribute to a freshness latch.

Preserve the legitimate controlled command-echo-to-empty-input transition,
initial supported input forms, cell coordinates, explicit NBSP normalization,
unique current candidate, auth/theme/trust/menu rejection and immediate
pre-send rechecking. Unsupported or ambiguous states continue to block.
Do not broaden chevron/Unicode matching or forward terminal-generated replies.

## Test-only cancellation ownership correction

Install managed SIGTERM/SIGHUP cancellation at selected POSIX entrypoints before
helper/native creation, covering the public selected driver, dedicated startup
entrypoint and offline namespace launcher. Restore prior handlers when ownership
ends. Other shared-driver dialogues retain their default routing/behavior.

Cancellation must be observed at bounded safe checkpoints in startup, private
IPC and PTY waits. Do not asynchronously unwind a child-creation window before
its process handle is owned. The first signal requests cancellation; subsequent
managed signals cannot interrupt the bounded cleanup of the same owned family.
An unsupported signal/entrypoint capability blocks before starting children.

Terminate and reap the exact owned helper/native process groups and descendants,
even if the group leader already exited. Cancelled dialogue cannot report
natural exit/acceptance. Preserve startup-claim one-use/revocation and private
root disposal; cancellation does not restore or renew approval.

Do not promise cleanup after SIGKILL, host failure or an unresponsive interpreter
that cannot reach a checkpoint. SIGKILL is uncatchable; an outer timeout must
never present unverified disposal as acceptance. Fixtures must verify actual
owned-process absence rather than treating directory removal as process proof.

## Compatibility, versioning and rollback

Preserve CLI argument forms, requested-duration fingerprints, immutable session
bindings, native Allow/Deny semantics, effect ceilings, origin containment,
default denied artifacts and read-only legacy scope. Existing numeric-clock
controls remain deterministic; real operation uses the current clock.

During implementation update the affected browser component version/skill
metadata and package-contract expectations coherently. Keep root `0.15.0`
unreleased; do not create a release or claim authenticated acceptance. Update
CHANGELOG, help, canonical browser contract and ADR-010/index to describe the
enforced lifetime and compatibility states only after their implementation.

Rollback restores the prior source as a coherent code/contract/version change,
with its known findings explicitly recorded. It must not restore consumed
approvals, continue an interrupted workflow or present weaker enforcement as
safe acceptance. Retained test dependencies stay externally owned.

## Required acceptance and verification

All regression tests must be observed RED before the applicable correction,
then GREEN with legitimate controls and the full package gate. Use existing
Python/Node fixture conventions; no actual provider, browser UI or native Claude
run is included in this implementation approval.

1. Split status/cursor redraw followed by the same old input stays unready;
   controlled echo-to-empty input and supported fresh candidates still pass.
2. Synthetic CLI SIGTERM and SIGHUP at startup, IPC and PTY wait leave no owned
   native/helper descendants. Cover repeated signals, handler restoration and
   cancellation before claim consumption. Tests clean their own RED leaks.
3. Stage approval at T0, reparse later, pass the original deadline but not the
   reparsed deadline: the next effect is blocked.
4. Advance time during discovery, startup, execution/reference resolution,
   validation discovery/startup/preparation and final expectation resolution:
   no later dispatch; cleanup remains performed.
5. Advance time after a prior persistent action: unknown, no further effects,
   no expired validation and no retry. Late verification cannot report success.
6. Repeat applicable expiry cases through the sibling single-step path.
7. Advance time inside adapter link-attribute/navigation awaits, delayed request
   interception and screenshot-to-capture transition: no later concrete call.
8. At the deadline reject; immediately before it allow a legitimate control.
   Invalid/backward clocks block; numeric constant test clocks retain coverage.
9. Expired completion and one-shot cleanup leave no reusable owned binding,
   including when read at the old fixture timestamp. A different later approval
   is preserved. Cleanup/completion errors never become validated success.
10. Full package/content/schema/workflow/staging checks pass; explicitly report
    unavailable capability tests rather than counting them as acceptance.
11. Reconcile the prior review's three findings against the new evidence. The
    production security correction receives one scoped bypass/regression review
    required by `fix-finding`, not another review of all historical branch work.

The existing native offline result remains inconclusive until a separately
authorized native control proves resumed context and natural exit. Authenticated
acceptance additionally requires its own fresh final-commit-bound grant.
Hosted CI/Security, push/PR/merge and TODO completion remain separate gates.

## Official references and next stage

- [Python signal handling](https://docs.python.org/3/library/signal.html): main
  thread installation, handler execution boundaries and uncatchable SIGKILL.
- [Playwright Locator API](https://playwright.dev/docs/api/class-locator): action
  waits/timeouts are runtime behavior, not an atomic operation-envelope fence.
- [Puppeteer request interception](https://pptr.dev/api/puppeteer.page.setrequestinterception):
  requests can require explicit continuation/abort after an initiating action.
- [Prior terminal specification](2026-10-07-p0-04b-headless-terminal-adapter-design.md).
- [ADR-010](../../architecture/ADR-010-browser-automation-boundary.md).
- [Canonical browser contract](../../../references/browser-operations.md).

Written specification approved. Next stage: operator review of the separate
[harness author-fix plan](../plans/2026-10-07-p0-04b-harness-review-fixes.md) and
[approval-lifetime plan](../plans/2026-10-07-p0-04b-approval-lifetime-remediation.md).
Preserve the Native execution method already selected, subject to confirmation
that these written plans capture the intended scope before implementation.
