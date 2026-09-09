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
post-hook completion, and structural `WORKFLOW_VALIDATED`. Every requested sample must complete the
same route; a mixed legacy/workflow matrix cannot be promoted. Cleanup becomes
verified only after deletion. Provider-backed active-runtime acceptance uses
`default` permission mode plus an operator-provided interactive MCP permission
handler and remains a separate gate; the harness neither installs nor
auto-approves that handler, and its configured name is not approval evidence.
The terminal must be a same-session SDK success, and any later tool or failure
lifecycle invalidates the sample. Role and context measurements are not inferred
from arbitrary stream records; until a separately trusted runtime channel
supplies them, the aggregate remains inconclusive rather than `ACTIVE`.

On 2026-09-07 a provider-free one-shot loopback witness used the existing
Playwright package and system Chrome channel. Eight execution steps and seven
fresh-context validation steps returned structural `WORKFLOW_VALIDATED`; the
disposable workflow state was absent afterward. A test-only fixed import and
channel launcher supplied the already installed runtime without adding a
production module-path interface or installing anything. This observation does
not establish the complete real-browser matrix or provider-backed active-runtime
acceptance.

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
- Implementation plan: `docs/superpowers/plans/2026-08-31-p0-04b-browser-automation.md`
- One-shot workflow plan: `docs/superpowers/plans/2026-09-02-p0-04b-one-shot-workflow.md`
- Canonical contract: `references/browser-operations.md`
- Related authority boundary: `docs/architecture/ADR-009-global-prompt-injection-defense.md`
- Related execution boundary: `docs/architecture/ADR-008-native-execution-boundary.md`
