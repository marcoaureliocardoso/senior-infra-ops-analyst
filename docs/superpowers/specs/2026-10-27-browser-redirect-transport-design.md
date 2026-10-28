<!-- cspell:ignore CDPSession CDPSessions OOPIF WebRTC WebTransport autoattach requestPaused redirectedRequestId sendMessageToTarget runIfWaitingForDebugger -->
# Browser redirect transport with per-hop authorization

Status: written design approved by the operator on 2026-10-28; the selected
direction controls every redirect hop, not a blanket redirect prohibition.
The [F0 implementation plan](../plans/2026-10-28-browser-redirect-f0.md) was
confirmed on the same date and its test-only candidate is implemented locally.
Production transport implementation and native qualification are not claimed.

Baseline: PR58 at eb895f60cfc39188f73141a5e5ede19c89ec6f10. The other four
confirmed review repairs are a separate, locally tested author correction.
This proposal amends [ADR-010](../../architecture/ADR-010-browser-automation-boundary.md)
only after implementation and qualification; existing acceptance remains open.

## Intent and boundaries

Preserve legitimate HTTP(S) redirects in infrastructure UIs while authorizing
each actual outbound hop before the browser sends it. Cover main-document and
subresource redirects, including chains longer than one redirect. Preserve
native URL, relative-resource, cookie, method and TLS semantics.

Do not change operation approval, protected references, effect classification,
the exact step origin, authentication origins, lifetime or outcome reconciliation.
An approved authentication origin is not permission for an active step to
navigate there implicitly. A separate declared step still selects that origin.
No provider/model/window/version pins, credential inspection, daily browser
profile attachment, trust-store changes, TLS interception, certificate bypass,
proxy installation, browser installation or automatic workflow retry.

The guarantee is HTTP(S) redirect authorization, not host-wide egress isolation
or a browser sandbox against a compromised engine. DNS pinning, WebRTC,
WebTransport and arbitrary non-HTTP transports are not silently covered.
Do not use this narrower capability to advertise universal network containment.

## Evidence and approaches

The current Playwright route only manually fetches top-level responses, while
other requests continue natively. Playwright documents first-URL-only redirect
interception. Its Chromium implementation automatically continues redirected
requests. Checking the final URL happens after a potentially forbidden request.
See [Page.route](https://playwright.dev/docs/api/class-page#page-route) and
the [upstream network manager](https://github.com/microsoft/playwright/blob/v1.62.1/packages/playwright-core/src/server/chromium/crNetworkManager.ts#L319-L331).
The source version identifies evidence, not a project runtime requirement.

Options considered:

1. Block every redirect before continuation. Smaller and easier to qualify,
   but breaks legitimate UI/authentication flows; not the selected approach.
2. Manually replay requests and fulfill the final response. This changes URL,
   redirect, authentication and relative-resource semantics. Letting the browser
   repeat a preflight instead creates a time-of-check/time-of-use gap. Rejected.
3. A native Chromium request-stage broker, with one interception owner and
   a gate before every actual hop. Recommended direction for the selected
   controlled transport. Native feasibility is a blocking milestone, not an
   assumption established by protocol documentation.

A CONNECT proxy alone cannot inspect encrypted per-request redirect semantics.
A decrypting proxy would add certificate custody and TLS-trust changes. Neither
is an automatic fallback under this design.

## Proposed architecture

Keep semantic UI actions in the existing adapters. Extract network admission
into an operation-owned broker with a closed interface:

- `prepare`: install interception and target lifecycle handling before any
  operation page can issue network traffic; return structural capabilities.
- `bindStep`: bind the immutable operation, exact step origin and lifetime.
- `authorizeHop`: validate native target/frame identity, HTTP(S) origin,
  request stage and live authority; return one allow/deny disposition.
- `finishStep`: wait for admitted work to settle or abort it before releasing
  the step binding. Background traffic has no authority outside that binding.
- `close`: revoke authority first, cancel paused work, close owned targets and
  prove cleanup. Never detach or disable interception on a still-live page.

The broker retains native request/frame/session IDs in memory for correlation,
never in the model-visible result. Each paused request gets exactly one terminal
disposition. Unknown, duplicate, stale, detached or uncorrelated events fail
closed. A sticky failure cannot be cleared by a later successful event.

Use the Chromium Fetch request stage, not `route.fetch` response replay.
The [Fetch protocol](https://raw.githubusercontent.com/ChromeDevTools/devtools-protocol/master/pdl/domains/Fetch.pdl)
describes pre-send pausing and redirect requests as separate events. Continue
the original request without rewriting URL, headers, method or body. The
browser remains responsible for redirect semantics; the broker evaluates every
new destination independently, without relying on experimental chain IDs.

The native browser/target session must belong to this disposable operation.
The [Target protocol](https://raw.githubusercontent.com/ChromeDevTools/devtools-protocol/master/pdl/domains/Target.pdl)
supports paused auto-attachment and recursive child handling. A newly attached
target must not run until its request interception is acknowledged. Main page,
child frames and OOPIFs need proven frame ownership. Popups and workers are
denied before their first request in the initial profile; service workers stay
blocked. Unknown target types invalidate capability instead of escaping checks.

Public [Playwright CDPSession](https://playwright.dev/docs/api/class-cdpsession)
and browser-session APIs are the first integration candidate. Their documented
`send(method, params)` interface does not itself expose a flattened child-session
transport. The feasibility milestone must resolve this explicitly. A public
non-flattened `Target.sendMessageToTarget` path may be evaluated, but it is
deprecated and must never be an invisible compatibility dependency. Private
Playwright fields, patching its internal auto-continue logic and page-injected
JavaScript are prohibited as enforcement mechanisms.

There must be no competing Playwright/Puppeteer request-interception owner and
no independent auto-resume path that can race broker installation. Remove the
old network routing only after the broker is qualified. If public session
routing or target startup cannot satisfy that invariant, stop at capability
unavailable and return for a new design decision. This design does not authorize
a custom browser launcher, raw debugging endpoint or an alternate CDP client.

## Policy at each hop

1. Assert operation lifetime, active step and transport identity immediately
   before native continuation. Recheck after asynchronous authorization work.
2. Normalize the destination using the existing strict origin contract. Reject
   URL credentials, malformed/unknown schemes and unapproved origins.
3. For the main document, require the exact active step origin at every hop.
   For subresources in the admitted page/frame tree, require the existing
   approved operation origins. Never expand that set from page content or a
   redirect header. Known origin alone never approves a new UI effect.
4. An unproven main-frame/subresource classification denies the request. A
   redirect to an unapproved destination is rejected before that destination
   receives any HTTP request, including POST body, authorization or cookies.
5. Bound outstanding requests, targets, message sizes, redirect work and time.
   Builder-selected finite defaults must be explicit, tested and cannot extend
   the operation deadline. A limit or protocol failure cancels the operation;
   it does not resume requests with reduced checks.

Keep default download denial. Preserve the existing artifact policy separately;
the transport must not read response bodies or persist a HAR, trace, page,
request headers, cookies, credentials or raw protocol stream. Any response-stage
check needed for downloads must be qualified without replacing native redirect
processing. Other unsupported channels must be denied by proven native controls
or excluded from the recognized route; JavaScript API stubs are not proof.

Expiry, cancellation, origin rejection, protocol loss and failed cleanup revoke
all admission immediately. After a possible state-changing dispatch, retain
`OUTCOME_UNKNOWN` and independent reconciliation; never claim not-applied from
a network failure alone. Do not automatically retry a failed workflow.

## Capability and compatibility contract

Initially qualify only the detected Chromium/Playwright HTTP(S) route. Presence
of a library, a CDP method or a version string is not enforcement proof. Method
availability, acknowledged installation, complete target ownership and the
qualified native profile are required before redirect containment can be true.
Missing or changed capability is unavailable/unproven, never a legacy fallback.

Puppeteer must not inherit Playwright qualification. Its independent route
requires its own per-hop and startup evidence before exposing the same claim.
This proposal does not remove a previously independently proven capability or
automatically promote an untested alternative.

Runtime detection must not contact an operator target or run a hidden network
self-test. Native qualification is an explicitly authorized synthetic loopback
test, distinct from production detection. The builder will define a structural
capability record and conservative supported-profile matching without fixing
versions. It must invalidate evidence when transport/engine identity changes.

## Milestones and acceptance

F0: after design approval, implement only the smallest feasibility harness using
public APIs and synthetic protocol fixtures. No production admission change.
Prove command/session routing, one owner, startup ordering, recursive target
handling, disconnect fail-closed behavior and no credential/content output.

F1: request separate permission for one bounded, disposable real-Chromium
loopback feasibility run. No provider, operator credentials/configuration,
external targets, downloads or installation. If unavailable or inconclusive,
stop without repetition or an architectural fallback. Documentation alone and
protocol doubles cannot pass F1.

Only after F1 passes: TDD the production broker, adapter integration, cleanup,
capability reporting, documentation and native qualification matrix. Required
native assertions, using synthetic state and per-endpoint request counters:

- Allowed same-origin two/three-hop main-document and subresource chains finish
  with correct final URL, relative resource URL and exactly-once endpoint hits.
- Unapproved second and third hops receive zero requests, for document, iframe,
  image/script and fetch/XHR paths. Include allowed cross-origin subresources
  followed by a forbidden hop and forbidden main-origin changes.
- Exercise 301/302/303/307/308, relative locations, redirect loops, concurrent
  requests and POST-to-GET versus method-preserving behavior. Synthetic cookies
  and body values are never exported; assert structural booleans only.
- Popup/worker/OOPIF startup, target swap, unexpected target, detach, duplicate
  event, authority expiry and cancellation cannot dispatch after revocation.
- Prove there is no unguarded gap before first navigation, between steps or
  during shutdown. Broker and adapter cannot independently release the same
  paused request. Test faults before and after possible persistent effects.
- TLS errors remain errors; no certificate bypass or trust-store writes. A
  separate approved local TLS fixture is needed to qualify HTTPS, not an HTTP
  assumption. Missing HTTPS proof prevents an HTTPS containment claim.
- Downloads, artifacts and cleanup retain their existing fail-closed contract.
  No raw native evidence survives aggregation; finite diagnostics only.

Run affected suites, mandatory package validation, independent review and
exact-head CI/Security after the approved final implementation. Increment the
browser component coherently, update CHANGELOG and ADR-010/index truthfully,
and keep PR58 draft until all acceptance gates are satisfied. No merge or TODO
completion is implied. The current hosted PACKAGE_METADATA failure remains a
separate pending gate until a new exact-head result proves otherwise.

## Risks and builder discretion

Primary risks are native API capability gaps, concurrent debugger clients,
early target traffic, deprecated session routing and unsupported protocols.
The defined response is a stopped milestone with structural evidence, not
another implicit diagnostic/retry cycle or weakened containment.

The builder may choose module names, finite resource bounds, test fixture
layout and a smaller internal state machine. The builder may not change origin
policy, enable TLS interception, create a debugging listener, introduce private
upstream APIs, relax approval/retention, or skip native feasibility. Any such
change needs a new operator decision.
