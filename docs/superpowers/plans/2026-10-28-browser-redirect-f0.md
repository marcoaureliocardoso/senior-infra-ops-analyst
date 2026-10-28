# Per-hop Redirect Transport F0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with the preserved direct/inline method. Steps use checkbox (`- [ ]`) syntax for tracking. Plan confirmed by the operator on 2026-10-28; direct implementation is in progress.

**Goal:** Build the smallest test-only candidate for public-CDP per-hop admission,
without changing production routing or mistaking synthetic tests for native feasibility.

**Architecture:** Separate bounded public-session message routing from the
operation-owned target/request state machine. Exercise both through synthetic
protocol fixtures, then emit a closed structural F0 report. F1 native feasibility
and production integration are separate gates, not automatic next commands.

**Tech Stack:** Existing Node test runner, JavaScript ES modules, standard-library
events/timers, existing origin/lifetime contracts and documented Chromium CDP.

**Spec:** [Approved per-hop design](../specs/2026-10-27-browser-redirect-transport-design.md),
approved by the operator on 2026-10-28. This plan implements its F0 milestone only.

<!-- cspell:ignore CDPSession OOPIF requestPaused sendMessageToTarget runIfWaitingForDebugger autoattach -->

## Global Constraints

- Reuse the isolated p0-04b-browser-automation worktree and preserve all four
  existing author repairs. Baseline HEAD is eb895f60cfc39188f73141a5e5ede19c89ec6f10;
  the repair/design changes are currently uncommitted and must not be discarded.
- No production admission change. Do not edit either production adapter,
  detector, registry, approval policy or capability claims during F0.
- No provider/model/window/version pins, credential inspection, daily browser
  profile attachment, trust-store changes, TLS interception, certificate bypass,
  proxy installation, browser installation or automatic workflow retry.
- No browser process, network listener, provider, operator configuration or
  credentials, APT/root operation, push, CI dispatch, merge, release or TODO completion.
- No custom browser launcher, raw debugging endpoint, alternate CDP client,
  private Playwright fields, internal patching or page-injected enforcement.
- Missing or changed capability is unavailable/unproven, never a legacy fallback.
- Keep the current browser1.0.5/root0.15.0/command1.2.1 metadata; F0 is test-only.
- Test code must not enter the Nori component. No raw protocol stream, page,
  headers, cookie, body, credential, content hash or native identity is published.
- A pure F0 result is always `SYNTHETIC_ONLY` and `nativeStatus: NOT_RUN`.
  It cannot set `ACTIVE`, `redirects: true` or satisfy F1/production acceptance.
- Stop if the candidate needs an API outside the approved public interface.
  Do not invent upstream events, fake an installation acknowledgment, or conceal
  the deprecated non-flattened session route to make a test pass.

## Review Focus

1. A parent session acknowledges a nested command before the child responds:
   the target must remain paused; Task 1 tests transport versus child acknowledgment.
2. An OOPIF migrates or a detached session ID is reused: stale frame authority
   cannot continue traffic; Task 2 tests target swap and identity reuse.
3. A second client resumes or handles a request: exclusivity is unproven,
   not restored by later success; Task 2 injects the conflict and Task 3 keeps
   native exclusivity explicitly unqualified.
4. A timeout/close failure arrives after provisional success: the report must
   stay unavailable with failed cleanup; Task 3 tests finalization precedence.
5. Extra response/request fields contain content or oversized data: no content
   reaches the report or an unmodified continuation; Tasks 1/3 test bounded
   parsing, fixed command construction and structural projection.

## File and interface map

- Create `tests/browser_redirect_protocol.mjs`: bounded public-session router;
  no browser imports, launcher, filesystem, generic CLI or production exports.
- Create `tests/browser_redirect_feasibility.mjs`: candidate state machine and
  closed F0 report; consumes the router and genuine existing lifetime contract.
- Create `tests/browser-operations/redirect-protocol-helpers.mjs`: deterministic
  public-session double with separate parent/child acknowledgments and scheduler.
- Create `tests/browser-operations/redirect-protocol.test.mjs`: router behavior.
- Create `tests/browser-operations/redirect-feasibility.test.mjs`: target/request
  admission, structural projection, finalization and negative controls.
- Modify `tests/validate-package.sh`: run both provider-free suites explicitly.
- Modify `tests/test-ci-isolation-wiring.py`: pin execution of those suites in
  the existing package-gate wiring test, not a new operational workflow.
- Modify `tests/validation-notes.md`, this plan and ADR-010/index: record F0-only
  results and exclusions; no claim that redirects are repaired in production.

Builder choices fixed for this candidate: at most8 targets,64 frames,
64 pending requests,512 received messages,16,384 bytes per protocol message,
20 hops per correlated chain,1,000ms per command and5,000ms total. Effective
time is also bounded by the existing operation lifetime. These are harness
resource bounds, not browser/provider version or context-window assumptions.

## Task 1: Bounded public-session router

**Files:** Create the protocol module, shared fixture helper and protocol suite.

**Interfaces:** `createProbeRouter(rootSession, { lifetime }) -> router`.
`rootSession` exposes public `send`, `on` and `off` only; `lifetime` must pass
`isOperationLifetime`. The router exposes `start()`, `send(path, method, params)`,
`onEvent(listener) -> unsubscribe`, `close()` and `snapshot()`.
The reviewed author correction adds synchronous `revoke()`: it cancels queued
admission before context cleanup, without detaching/disabling a live target.
`path` is a chain of owned child-session IDs, kept only in memory.
`snapshot()` returns finite counters/booleans/reason code, never IDs or messages.
Allowed methods are exactly `Target.setAutoAttach`, `Target.closeTarget`, `Network.enable`,
`Fetch.enable`, `Fetch.continueRequest`, `Fetch.failRequest`, `Page.enable`,
`Page.getFrameTree` and `Runtime.runIfWaitingForDebugger`. Nested routing uses
public `Target.sendMessageToTarget` and records `deprecatedRouting: true`.
No method or params supplied by a model, CLI or page are accepted.

- [x] **1. Write RED tests:** `nested command waits for child acknowledgment`,
  `cross-session response cannot resolve a command`, `unknown response cannot
  restore a failed router`, `duplicate child reply fails closed`, `bounded
  malformed messages never reach listeners`, `unlisted command never dispatches`,
  and `expiry prevents the next public send`. Assert real router promise state,
  fixed native command envelopes and literal structural failure results through
  the external session double. Supply genuine lifetime objects and fake time.
- [x] **2. Run RED:** `node --test tests/browser-operations/redirect-protocol.test.mjs`.
  Expect FAIL because the router export or required behavior is absent;
  unrelated fixture/setup errors do not count as the RED proof.
- [x] **3. Implement the router interface:** correlate both outer dispatch and
  inner child response; recursively wrap nested sessions, bound every incoming
  payload before parsing and reject duplicate JSON keys. Keep one finite
  sticky failure and revoke before shutdown. Acknowledged envelope delivery is
  never acknowledgment of the nested protocol command. No request/body logging.
- [x] **4. Run GREEN:** the full protocol suite must pass, including loss,
  unknown session, recursive routing, timeout and close races. No open timers
  or listeners after close. Verify `deprecatedRouting` is visible structurally.
- [x] **5. Checkpoint:** inspect only this task's diff and record test results
  in the owned work ledger. Do not commit or stage the earlier author repairs
  accidentally; commit the combined approved candidate only at Task 3's gate.

## Task 2: Candidate target and request admission state machine

**Files:** Create the feasibility module and suite; extend the shared helper.

**Interfaces:** `createRedirectProbe({ router, lifetime, ownership,
allowedOrigins, closeOwnedContext }) -> probe`, consuming Task 1's router.
`ownership` is an immutable synthetic fixture tuple of context, primary target
and primary frame IDs; it does not purport to discover native ownership.
`probe.prepare()`, `probe.bindStep({ origin })`, `probe.finishStep()`,
`probe.close()` return promises. `probe.snapshot()` is structural only.
`closeOwnedContext()` is a fixed trusted callback, not a user-selected target.
The candidate consumes only native-shaped public protocol events from its router.

- [x] **1. Write RED tests:** `target remains paused until interception ack`,
  `nested child is armed before release`, `unowned and popup worker targets
  never resume`, `late frame migration loses authority`, `each allowed redirect
  hop receives one continuation`, `forbidden second and third hops receive
  none`, `main document cannot switch to another approved origin`, `expired
  pending authorization cannot continue`, `competing owner is sticky failure`,
  and `between-step traffic is denied`. Assert literal disposition counts and
  ordering at the router boundary, not a fake broker's own result.
  The conflict fixture uses public symptoms such as `waitingForDebugger:false`
  before owned arming, never an invented competing-client event. Absence of
  that symptom cannot prove native exclusivity; F1 must resolve it independently.
- [x] **2. Run RED:** `node --test tests/browser-operations/redirect-feasibility.test.mjs`.
  Verify the missing state-machine behavior causes failure before implementation.
- [x] **3. Implement the candidate:** use strict existing origin validation
  and genuine lifetime checks before each continuation. Install request-stage
  Fetch handling and recursive paused auto-attachment before target release.
  Prove fixture frame ancestry; deny unknown/worker/popup targets before resume.
  Correlate redirect chains using stable Network events and owned session/network
  identity, not the experimental Fetch redirect-ID field; absent or contradictory
  correlation cannot justify a hop-budget claim. Continue only `{requestId}`
  unchanged; do not replay HTTP, inspect response
  bodies or forward headers/method overrides. Duplicate dispositions, unknown
  frame/resource types, detached or reused IDs invalidate the candidate.
- [x] **4. Extend GREEN controls:** allowed two/three-hop document, iframe and
  subresource sequences, relative locations already resolved by native-shaped
  events, concurrent replies, redirect loops and all exact resource/time bounds.
  Reject known-origin/unknown-frame requests and expiry after asynchronous work.
  `finishStep` cannot unbind while admitted work is unresolved; cancel and fail
  closed rather than release paused requests unguarded. Re-run both suites.
- [x] **5. Checkpoint:** record synthetic coverage and the unresolved native
  startup/ownership/exclusivity questions. No modification of production adapter
  imports, capability booleans, locator behavior or authorization flow.

## Task 3: Structural result, gate wiring and F1 handoff

**Files:** Feasibility module/suite, package test wiring, notes and ADR/index.

**Interfaces:** `finalizeRedirectProbe(probe) -> Promise<F0Report>`.
The exact public report keys are `schemaVersion:1`, `phase:F0`,
`evidenceClass:SYNTHETIC_ONLY`, `nativeStatus:NOT_RUN`,
`candidateStatus:READY_FOR_F1|UNAVAILABLE`, `reasonCode`, `deprecatedRouting`,
`checks`, and `cleanup:VERIFIED|FAILED`.
`checks` contains only booleans `routing`, `startupOrder`, `recursiveTargets`,
`perHopAdmission`, `lifetime`, `singleDisposition`, `contentFree`.
Finite reason codes: `F0_COMPLETE`, `PUBLIC_API_UNAVAILABLE`,
`PROTOCOL_INVALID`, `IDENTITY_UNPROVEN`, `OWNERSHIP_CONFLICT`, `LIMIT_EXCEEDED`,
`OPERATION_EXPIRED`, `OPERATION_CLOCK_UNPROVEN`, `CLEANUP_FAILED`.
Failure cleanup dominates the candidate result; reports cannot carry exception text.

- [x] **1. Write RED tests:** `finalization cannot promote synthetic evidence`,
  `late timeout taints provisional ready`, `failed owned cleanup dominates`,
  `published shape rejects content and unknown fields`, and `import has no I/O`.
  Assert the exact literal report schema after serialization and no new files,
  subprocess, network or browser imports from a sandboxed child loading the
  test-only modules. Include synthetic forbidden fields without exporting them.
- [x] **2. Implement minimal finalization:** revoke authority, cancel pending
  requests, await owned context closure, remove listeners, clear correlation
  state, then return the closed report. Do not disable interception or detach
  from a still-live target. A failed close is not cleanup proof.
- [x] **3. Wire suites RED-to-GREEN:** add both exact Node invocations to
  `tests/validate-package.sh` and the existing wiring test. Execute that wiring
  control; removing either invocation must fail before restoring it. No CI
  retries, new remote workflow or optional skip of F0 tests.
- [x] **4. Run affected suites:** both new Node files; existing browser suites;
  `python3 tests/test-ci-isolation-wiring.py`; schema/content/architecture,
  Markdown/spelling and ShellCheck. Record all failures, including unrelated
  ones. Verify Nori packaging excludes test-only modules in the normal contract.
- [ ] **5. Review and commit the candidate:** use one fresh independent reviewer
  for the combined candidate, preserve the chosen inline method and avoid
  automatic review/repair loops. Confirm no production redirect-capability
  change and no raw evidence retention. After focused checks and review, commit
  the combined candidate with explicit paths, including the earlier repairs and
  their tests/docs. Label it locally verified but full-gate/native-unqualified;
  do not stage unrelated/operator files or push. The immutable gate needs this
  exact source commit, not a stale HEAD archive or a mixed working-tree copy.
- [ ] **6. Run the full project command:** through the established clean Debian
  WSL/Node24.17.0 route, run `bash tests/validate-package.sh` against an immutable
  Git archive of that combined author-repair plus F0 candidate. Preserve
  bounded receipt and owned cleanup proof using the already-qualified wrapper.
  A partial gate or old source receipt is not proof for this candidate.
  Stop and report any failure; do not automatically repeat the full gate. Record
  actual results in a separate evidence-only documentation checkpoint. Keep
  remote/native gates open; no push without explicit publication approval.
- [ ] **7. Stop for F1:** report whether the candidate is ready or unavailable.
  Request a separately bounded, commit-bound real-Chromium loopback feasibility
  grant only if F0 has no unresolved public-API blocker. No native execution,
  automatic repeat, custom launcher or alternative transport follows this plan.

## Deferred milestones, not implementation omissions

F1 must establish actual public session routing, startup before first traffic,
child-target coverage and absence of a competing Playwright auto-resume owner.
Synthetic events cannot establish any of those native facts. If the interface
cannot enforce them, stop and report the structural blocker; return for a new
design decision rather than inventing a capability or trying another route.

Only after an authorized F1 pass will a follow-on production plan map the
approved design's complete HTTP(S),301/302/303/307/308, native URL/method/cookie,
TLS, downloads/artifacts, lifecycle and cleanup matrix to actual runtime code.
That plan must preserve operation approval and reconciliation, define qualified
profile matching without version pins, independently qualify Puppeteer or leave
it unproven, then require full-package/independent/exact-head CI/Security gates.
Until then, PR58's redirect finding and hosted PACKAGE_METADATA gate stay open.

## Plan self-review and execution handoff

All F0 requirements map to Tasks1-3; all five Review Focus conditions have named
tests. Interfaces above are shared verbatim between router, probe and finalizer.
F1 and production acceptance are deliberately deferred because they depend on
native feasibility, not because a synthetic pass waives them. Defaults are
builder choices within the approved design, not operator claims about capability.
Tasks1/2 and the Task3 local controls are implemented; combined qualification is
in progress. The preserved execution method is direct/inline. Native feasibility
and production transport admission remain unimplemented and unqualified.

The independent review found four Important F0 defects; one author TDD pass
corrected revocation queues, request-stage/ID validation, expected close detach
and same-owned-frame navigation.36 local F0 controls pass; full-package evidence
is still required. Native event ordering and exclusivity remain unproven.
