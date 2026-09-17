# ADR-010: Guarded browser automation boundary

- Status: Accepted
- Date: 2026-09-01

## Context

Infrastructure diagnosis and repair can require a web UI when no suitable CLI
or typed API exists. Public information retrieval is not enough: operators may
need authenticated router, switch, service, cloud, or appliance workflows. At
the same time, browser page data and tool metadata are untrusted, UI effects can
be ambiguous, and credentials must not become instructions or retained evidence.
The canonical behavioral contract is `references/browser-operations.md`.

## Decision

Browser automation is an operational transport governed by the same operation
envelope, authorization, effect, and evidence model as other protected routes.
The main-session MCP route and the protected runner route both require a bound
operation, per-call policy evaluation, current native authorization, and exact
hook coverage. The legacy per-command runner is read-only because separate
processes cannot truthfully claim one persistent browser session. Authentication
and mutation use one protected `--step workflow` process whose reference-only
manifest receives native approval before exact fingerprint activation. Runtime
capability must prove confinement for every step; execution closes before a
fresh adapter performs independent validation. The
package gives no generic MCP grants to subagents; all 12
roles keep their declared tool boundaries and may use only an explicitly routed
and proven capability.

Nori installation does not activate browser hooks, enable an MCP server, install
a browser, or overwrite operator preferences. Activation is transactional and
project-local. Exact installed settings establish configuration only; a harmless
structured deny proves runtime coverage before an operational call.

## Capability states and routing

Runtime capability detection yields `AVAILABLE_RECOGNIZED`,
`AVAILABLE_UNRECOGNIZED`, `UNAVAILABLE`, or `CONFLICT`. Execution additionally
stops on `GUARD_UNPROVEN` and unresolved `OUTCOME_UNKNOWN`. A recognized main-session MCP
has precedence, followed by a recognized protected runner; an ambiguous,
conflicting, or unproven route fails closed.

Every mutable one-shot is `ALWAYS_ASK`, including in `bypassPermissions`.
Approval stages only the canonical invocation fingerprint; it does not persist
the decoded workflow. Requested steps are intersected with the effective
runtime adapter before browser open or protected reference resolution. The
runtime-detected adapters use fixed optional imports and do not install or
download Playwright, Puppeteer, an MCP server, or a browser. Detection reports
what is present rather than pinning Claude Code, Nori, provider, model, adapter,
or browser versions.

## Authentication and human-only challenges

Interactive login is allowed when the operator authorizes the target and effect.
A credential may come from an existing protected session, a recognized vault or
helper, or a direct operator request. It remains authentication data, never
authority, page content, or reusable approval. Raw values, cookies, session
profiles, secret-derived identifiers, and credential-bearing evidence are not
retained. CAPTCHA, WebAuthn touch, consent, and comparable human-only challenge
states pause for the operator rather than being bypassed.

## Origin and artifact controls

Every navigation, redirect, subresource, popup, upload, and download is checked
against the bound origin policy. Cross-origin transitions require an explicitly
approved origin expansion. Downloads, screenshots, traces, and other artifact
classes are denied unless the operation envelope permits their exact class,
size, path, and retention policy. Approved artifacts use opaque handles,
verified system-temporary roots, bounded sizes, redaction rules, and
deterministic cleanup.
The current package rejects retention and requires an injected reviewed redactor
before binary capture.

Mutating calls that time out or lose confirmation become `OUTCOME_UNKNOWN`.
They are not retried automatically; an independent validator must first
classify the state as applied or not applied. Applied operations cannot repeat.
The same rule applies to a failed fill, select, navigation, or interactive
control that might have triggered autosave, and to a later failure after a
successful fill, select, click, submit, or declared mutation. Credential-class
references are bound only to explicit authentication origins and
configuration-class references only to service origins. Navigation holds an
exact destination-origin lock through redirect completion. Page-bound adapter
actions check the actual top-level origin before and after dispatch while
holding the same lock. Both deny a top-level transition to another allowed
origin while the action is in flight.

Installed settings and ownership records establish only
`CONFIGURED_UNPROVEN`; no persisted proof object can represent current-session
hook or tool lifecycle. One-shot pending state is consumed on every attempted
workflow, including capability failure before activation. The workflow owns
and closes any injected artifact manager, and its structural result reports the
envelope's actual maximum effect. If a process ends after one-shot activation,
any legacy step for that active fingerprint quarantines and invalidates the
binding before adapter dispatch.

## Validation evidence

Deterministic tests cover capability routing, MCP mapping, operation binding,
hook decisions, transactional settings, protected runner behavior, optional
adapter detection, origin restrictions, artifact handling, and a 37-scenario
loopback fixture matrix. The provider-free harness self-test and preflight prove
bounded retention and an exact fail-closed deny. Its aggregate distinguishes
the legacy read-only multi-command route from the mutable persistent one-shot
route. It cannot name `persistent-one-shot`, `ACTIVE`, completed authentication,
mutation, or validation without one observed workflow tool call, matching
Claude Code `hook_started`/`hook_response` pairs for the configured
`PreToolUse:Bash` and `PostToolUse:Bash` matchers, the exact native `ask`
response produced by the installed command guard, coherent ordered tool and
post-hook completion, and structural `WORKFLOW_VALIDATED`. The allowed sample
must complete that route; a separate exact denied sample must prove that no
runner execution or additional fixture effect occurred. A mixed
legacy/workflow result cannot be promoted. Cleanup becomes verified only after
deletion. Provider-backed active-runtime acceptance uses `default` permission
mode plus phase-specific disposable test permission servers. Their decisions
are deterministic test policy, not human approval, and they remain a separate
gate excluded from staged or installed artifacts.
The tool-use and tool-result envelopes must share the hook session and parent
tool identity. The terminal must be a same-session SDK success, and any later tool or failure
lifecycle invalidates the sample. Role and context measurements are not inferred
from arbitrary stream records. In the POSIX/WSL harness, a separately retained,
content-free sidecar is accepted only when its exact schema, private regular-file mode, random run nonce,
and workflow session set match; it must contain the canonical 12-role sequence,
five ordered same-session context stages, coherent tool-search state, and
structural MCP discovery and use. Missing, malformed, oversized, symlinked,
permission-unsafe, cross-run, cross-session, incomplete, or extra-field evidence
leaves the aggregate inconclusive rather than `ACTIVE`. Native Windows loading
also remains inconclusive because the parser does not claim equivalent portable
no-follow and ACL proof there.

On 2026-09-07 a provider-free one-shot loopback witness used the existing
Playwright package and system Chrome channel. Eight execution steps and seven
fresh-context validation steps returned structural `WORKFLOW_VALIDATED`; the
disposable workflow state was absent afterward. A test-only fixed import and
channel launcher supplied the already installed runtime without adding a
production module-path interface or installing anything. This observation does
not establish the complete real-browser matrix or provider-backed active-runtime
acceptance.

On 2026-09-15 the expanded provider-free matrix executed all 37 named scenarios
with the existing Playwright package and system Chrome. The matrix classifies
each scenario as production-adapter, protected-runner, or fixture-only support;
the public-read scenario also has a separately labelled deterministic HTTP
fallback check that does not claim native `WebFetch` behavior. Existing-session
and human-challenge pages remain fixture-only because the protected adapter
neither accepts persisted state nor interprets page content as authority.

Production-boundary tests cover password/TOTP/logout, autosave and submitted
changes, fresh validation, compensation, upload, screenshot redaction, explicit
download/trace denial, real drift between successful inspection and attempted
execution, hostile browser channels, ambiguous outcomes, and cleanup. A second
forbidden loopback server counts requests: cross-origin redirect `Location` is
validated with redirect following disabled, and popup/new-tab/subresource
requests are aborted before that server observes any access. Only structural
reason codes and opaque artifact handles cross the adapter boundary; the
redirect and screenshot canaries are absent from retained results and the
temporary sanitized screenshot. The profile-named scenario proves the actual
implemented boundary--an ephemeral context created with no storage state,
downloads and service workers disabled, intercepted top-level responses disposed
on every path, browser/context closure, and operation-state removal--and does not
claim cleanup of a persistent profile that was never created. The adapter is
active only when the detected Playwright interface supports redirect-disabled
route fetching; earlier or unversioned candidates fail closed as unrecognized.
Declared artifact clicks and submits are denied before the protected runner can
dispatch them. Direct adapter navigation also accepts that classification, while
the current protected-runner navigation grammar does not; an unexpected
attachment response is therefore aborted and disposed after its initial
allowed-origin request. Disposal closes retention, not transient acquisition:
Playwright `route.fetch()` does not expose a streaming byte cap, so no effective
response-memory limit is claimed.

The matrix produced 40 passing test records including its inventory binding and
runtime-selection controls. The deterministic trusted-sidecar contract and its
parent-controlled producer passed 46 focused Python tests in Debian WSL on
2026-09-16; no provider request occurred. The producer assigns UUID sessions,
reduces only exact SDK tool/result pairs and nonce-bound native status-line
`context_window.used_percentage` observations, requires one exact
`context-continuity` skill call, one prospectively guarded
`diagnostic-operator` subagent call, coherent ToolSearch discovery/use, and one
ordered nonce-bound MCP call. It supplies strict minimal MCP configurations,
exposes the fixture only to its measurement stages, and restricts workflow
model tools to Bash. It removes temporary MCP configs, the disposable Claude
session store, prompts, streams, PTY captures, and transcripts before sidecar
construction.

The live harness may receive explicit absolute paths to an existing operator
Playwright module root and browser cache. It validates the current packages and
an executable cached Chromium, links only `playwright` and `playwright-core`
at the nearest module-resolution location inside its disposable probe and
installed-skill roots, rejects any pre-existing skill-local package root, and
still uses the fixed production adapter imports. The probe and installed copy
must report the same adapter ID and observed version and must each open and
close successfully without navigation. The harness neither downloads nor
installs a runtime and the links disappear with the disposable root. A
provider-free preflight on
2026-09-17 observed Claude Code `2.1.273`, the existing Playwright `1.62.1`
package, and `AVAILABLE_RECOGNIZED` through that route after opening and closing
one browser/context without navigation. The expanded 47-test focused WSL gate
passed on the same date.
Provider-backed population of that sidecar, CI/Security, and delivery remain
separate acceptance gates.

The automated active-runtime gate uses a disposable test-only permission MCP,
not a production authority service. It structurally permits one exact synthetic
loopback workflow, denies one different workflow in a fresh session, and proves
the denied phase caused no additional fixture effect. Evidence calls this
`synthetic-deterministic`; it cannot claim observed human approval. The server,
configs, signals, claims, and raw requests are removed with the disposable
runtime and are excluded from Nori staging. Production mutable operations still
use the native interactive Claude Code permission prompt for every `ask`.

## Alternatives rejected

A prompt-only policy was rejected because prose cannot prove the binding between
one authorized operation and one tool call. A mandatory single MCP was rejected
because it would pin deployment topology and could make the package install or
enable operator-owned browser infrastructure. Broad subagent tool grants and
automatic retries after uncertain mutations were rejected for the same
least-authority and outcome-reconciliation reasons.

## Consequences and residual risks

Operators retain browser/runtime ownership and must explicitly activate the
guard. Unsupported or conflicting installations stop safely but may require a
future adapter. A malicious same-principal local process can still race or alter
operator-owned settings and runtime files; managed settings or OS protection are
required for that threat model. A recognized adapter establishes compatibility
only for its observed runtime and does not make untrusted UI content safe.

## Rollback

Run the browser configurator with `--remove-owned`. It removes only exact
package-owned settings and preserves later operator changes. Then remove any
operator-installed browser/MCP runtime separately under that runtime's own
ownership procedure. Pending operations and credential reuse are not restored.

## Links

- Design: `docs/superpowers/specs/2026-08-31-p0-04b-browser-automation-design.md`
- Acceptance permission design: `docs/superpowers/specs/2026-09-17-p0-04b-disposable-permission-handler-design.md`
- Implementation plan: `docs/superpowers/plans/2026-08-31-p0-04b-browser-automation.md`
- One-shot workflow plan: `docs/superpowers/plans/2026-09-02-p0-04b-one-shot-workflow.md`
- Canonical contract: `references/browser-operations.md`
- Related authority boundary: `docs/architecture/ADR-009-global-prompt-injection-defense.md`
- Related execution boundary: `docs/architecture/ADR-008-native-execution-boundary.md`
