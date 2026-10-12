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
The acceptance budget is exactly six top-level invocations and at most 40 model
turns, with no automatic retry. Provider-backed observation of the complete
ordered allow/effect/validation/deny/no-effect sequence remains pending.
Provider-free verification on 2026-09-17 passed the complete package gate and
the 40-record real-browser matrix; a fresh preflight observed Claude Code
`2.1.274`, Playwright recognized, exact guard deny, and verified cleanup.

The harness now also has a provider-free model-dispatch diagnostic. On
Linux/WSL, Claude Code runs under `--bare` inside a Bubblewrap user, PID, and
network namespace with no egress, using a minimal allowlisted environment,
disposable home, synthetic authentication material, disabled tools, and an
in-namespace loopback API sentinel. The diagnostic records only structural
request counts and route categories, never the request body or model value.
Absent, auxiliary-only, mixed, remapped, timed-out, or interrupted dispatch is
not an exact observation; interruption tears down the namespace and full
process tree. A direct proxy-bypass regression proves the child cannot reach a
host-network listener. The namespace is assembled from an explicit filesystem
allowlist rather than a host-root bind. Operator homes, mounted host paths,
runtime sockets, host configuration, and unrelated temporary directories are
not mounted; only the resolved executable, diagnostic helper, required
read-only system runtime, and disposable work bind are exposed. The harness
derives a configured runtime label without
executing `claude --version` outside isolation.

This isolated request shape is an explicit informational diagnostic, not an
authorization gate for live traffic, and neither preflight nor live acceptance
invokes it. P0-04B controls the configured provider boundary, browser
capability, native permission path, and workflow evidence. Model names and
provider-internal remapping are outside its security boundary. A live run must
bind `ANTHROPIC_BASE_URL` exactly to the bounded HTTPS endpoint named by the
operator in `P004B_AUTHORIZED_PROVIDER_ENDPOINT`; credentials, query, fragment,
whitespace, empty authority, or a mismatch fail before runtime dependencies are
used. An earlier proxy-only observation with Claude Code
`2.1.280` and configured `deepseek-v4-pro[1m]` produced a model mismatch, but it
is not an egress guarantee or live-route proof. The corrected no-egress
diagnostic reached its 30-second limit and rejected the partial observation;
the historical aggregate reported `PREFLIGHT_MODEL_DISPATCH_UNPROVEN`,
`AVAILABLE_UNRECOGNIZED`, and verified cleanup. This remains diagnostic history,
not a pending acceptance condition. Provider-backed acceptance still requires
an explicit authorization bound to the final commit and provider endpoint.

When an authenticated Claude process exits before producing a trusted sample,
the harness reduces bounded stderr to one existing allowlisted category. If no
category matches, it may retain only the normalized process exit status and one
allowlisted structural stream state: empty, system event, assistant event,
result, error result, invalid JSONL, or other event. The reducer never copies an
event value, message, prompt, URL, response, model value, or provider error into
the diagnostic. Fail-closed rejection provenance is limited to four content-free
codes: `CLAUDE_EVIDENCE_REJECTED_INPUT` for rejected diagnostic arguments or
evidence, `CLAUDE_EVIDENCE_REJECTED_PARSER` for reducer execution failure,
`CLAUDE_EVIDENCE_REJECTED_ALLOWLIST` for output outside the closed vocabulary,
and `CLAUDE_EVIDENCE_REJECTED_CLEANUP` for failed immediate deletion. Prompt,
stream, and transcript are deleted before the harness blocks. Only `INPUT` may
come from successful reducer output; `PARSER`, `ALLOWLIST`, and `CLEANUP` are
reserved to the shell stage that observes each condition. These fingerprints are
diagnostic only: they cannot prove provider receipt, permit a retry, or satisfy
the live acceptance gate.

The live diagnostic now uses `--claude-failure-observation` instead of the
legacy single-category reducer, whose interface remains compatible. One
closed fingerprint preserves the observed nonzero supervisor exit status,
structural stream state, recognized terminal subtype, model-route advisory
presence, and stderr category. The advisory is excluded from the error-category
selection; ambiguity remains `PROCESS`. A parent-owned timeout overrides the
category without discarding other structural fields. Missing or unsafe evidence
is rejected. Reads retain the 64 KiB bound, regular-file/no-follow checks,
nonblocking open, and change detection. Detailed JSON parsing rejects duplicate
keys and non-JSON constants; multiple or nonterminal result records produce an invalid terminal label.
Unknown subtypes never cross the boundary as input text. A `SUCCESS` subtype
with `RESULT_ERROR` remains explicitly distinguishable from successful work.
The shell accepts only closed enum fields, the matching numeric supervisor status,
and coherent parent-timeout provenance. It deletes raw data before blocking.
Neither the fingerprint nor a terminal label proves provider receipt,
failure cause, native permission, browser effect, or acceptance, and neither
authorizes a retry. Existing signal encoding and reserved timeout-status
mapping are unchanged, so this is not a claim to preserve an unmodified raw
child status. No provider-backed run occurred for this correction.

Canary detection is independent of workflow and permission proof. Both phase
reducers inspect literal raw occurrences and decoded JSON strings and keys;
no user input, tool result, metadata, unknown field, or thinking channel is
whitelisted. Text and thinking blocks are recomposed separately within one
assistant message. Cross-event recomposition requires the exact bounded native
session ID, explicitly present parent tool-use ID (including null), and message ID. Only a suffix
shorter than the canary is held per channel in ephemeral memory. The scanner
bounds the marker to 256 characters, each event to 4,096 value nodes and depth
64, message content to 64 blocks, and cross-event identities to 64. Exceeded
bounds, malformed known message/channel and hook field types, duplicate keys,
and non-JSON constants prevent a passing phase; a detected canary remains a
failure. Fan-out is checked before enqueueing traversal nodes, independently
of the bounded input's unavoidable JSON parsing allocation. Invalid records
discard correlation suffixes but do not disable scanning or recomposition of
later valid records; acceptance rejection remains sticky. Arbitrary encodings and
unidentified cross-event fragments are not reconstructed, and this is not a
universal confidentiality claim.

Failed private samples may add only one `canarySource` enum:
`ASSISTANT_TEXT`, `ASSISTANT_THINKING`, `ASSISTANT_TOOL_INPUT`, `USER_INPUT`,
`TOOL_RESULT`, `SYSTEM_METADATA`, `TERMINAL_RESULT`, `RAW_INVALID`, `UNKNOWN`,
or `MULTIPLE`. These labels describe observed record shape, not trusted
authorship, exposure causality, or provider behavior. The closed classifier
`--workflow-canary-source` reads the bounded private sample and emits only a
known enum; missing, unsafe, or forged values become `UNKNOWN`. A second shell
allowlist applies before reporting, after raw and whole-root cleanup.
Unknown attribution never permits continuation or retry. The aggregate schema,
native authorization, fixture validation, time/turn limits, and fresh
commit-bound live authorization remain unchanged. Deleted historical streams
cannot be recovered or reclassified by this correction.

Unexpected nonzero harness exits also have a shell-owned diagnostic boundary.
An EXIT handler captures the process status, attempts the verified-prefix
cleanup, and checks that the disposable root is absent before reporting
`BLOCKED: unexpected harness exit` with a closed stage label, numeric exit
status, and `cleanup=verified`. An unknown stage becomes `UNKNOWN`; failed
cleanup forces status 2 and reports only `cleanup=failed`. It never copies
`BASH_COMMAND`, source lines, prompts, streams, filenames, or exception values.
Explicit `blocked` reasons remain authoritative and the EXIT handler is silent
on success. A failed cleanup attempt remains recorded even if the final
cleanup later removes the root. Timeout helpers return failure to their parent
before that parent emits the explicit block reason. Stage labels describe where
the shell stopped, not the failure cause,
provider receipt, workflow outcome, or authorization to retry.

Successful reducer execution is not workflow acceptance. The allow reducer
preserves failed or inconclusive stream status and reason before considering
permission proof; a structurally incomplete workflow remains explicitly
`WORKFLOW_INCOMPLETE`. After deleting raw prompt, stream, and transcript,
the shell applies a semantic gate to each reduced phase sample. The gate
requires exact phase, session, route, guard, lifecycle counts, workflow state,
and permission proof, not merely a successful JSON writer exit. Its bounded
4 KiB private read requires current-user ownership, owner-only permissions,
a regular nonblocking no-follow file, unique JSON keys, exact completion fields, and
strict integer counts. Unknown content or classifier output becomes
`WORKFLOW_EVIDENCE_REJECTED`, never an emitted input value. A rejected sample
stops the sequence, removes the complete disposable root, verifies absence,
and then emits its closed reason. Cleanup failure cannot claim verified
cleanup. Valid phase proof still requires the independent fixture-state check
and the complete pair aggregate; this gate cannot establish acceptance alone.

## Acceptance-only native API-key startup

The bounded numeric context dialogue uses collapsed `/context` rather than
expanded `/context all`. Numeric aggregate measurement does not need per-item
detail, and offline installed-profile comparisons exposed viewport sensitivity
in the expanded form. The original geometry and strict native header/percentage/
completion validators are retained; no retry or enlarged-terminal assumption
is introduced. This test-only inspection choice does not alter production,
authorization, credential transport or live request/turn/time budgets.

The disposable acceptance harness may perform one separately operator-authorized
native API-key startup confirmation, only during its initial `main-before`
context probe. This is not browser permission and is not installed in production.
The explicit opt-in requires a clean immutable authorized commit and retains
the existing endpoint, credential transport, six-invocation/40-turn and
120-second/1,800-second limits. An owner-only, no-follow claim binds that commit,
run nonce, native session, exact endpoint, canonical executable and private
configuration directory; it expires within 120 seconds and is consumed before
launch with an exclusive spent marker. Flags and claims are trusted-caller
bookkeeping, not proof of a human grant or a sandbox against same-user races.

The controller recognizes only the fully drawn API-key heading and exact
two-option Yes/No semantics. It confirms once; unknown, ambiguous, repeated,
login or post-startup selectors block. Prompt readiness revokes an unused
decision. The shared PTY CLI stays fail-closed without an enabling option.
Native approval may be remembered by Claude only in the disposable config;
no credential or derived credential identity enters the claim or aggregate.
Claim, spent marker and native HOME/config/cache are deleted before sidecar
construction and aggregate computation, after raw PTY deletion. Structured
measurements remain until computation; the whole root is removed before final
aggregate emission. A structural startup event cannot prove provider
receipt, browser consent or workflow acceptance. See
`tests/browser-launch-diagnostics.md` for the test-only caller contract.

Startup readiness preserves the caller's post-transition observation boundary,
even before a single-use API-key decision is used. A fresh recognized input row
is required for numeric inspection; theme/trust selectors, partial option rows
and status text cannot supply readiness. Unsupported prompt formats block.
Failure diagnostics retain only a closed bounded sequence of stage/outcome
pairs, after verified cleanup of the complete private root. The independent
line reducer rejects unknown fields and labels. Such diagnostic claims neither
establish acceptance nor renew consent; source/session/endpoint/configuration/
executable/expiry bindings and live budgets remain unchanged.

Native measurement continuity requires temporary session persistence. The
acceptance caller omits the history-disabling flag rather than overriding an
operator preference. A live-only prelaunch gate rejects enabled or unknown
explicit `CLAUDE_CODE_SKIP_PROMPT_HISTORY` values before settings/dependencies
or private-state creation; the closed diagnostic never includes the value.
Absence or a recognized false value is not proof of all effective native
settings and does not relax subsequent checks. Native history remains confined
to the existing private disposable HOME and is removed before aggregation.
The current `--resume` sequence and non-resuming workflow persistence policy
remain unchanged; no fake history, new provider call, retry, public live CLI
or production configuration is introduced.

## Alternatives rejected

### Test-only terminal observation boundary

P0-04B numeric context probes explicitly select a passive `@xterm/headless`
engine; the distributed skillset and other PTY dialogues do not adopt it.
An external test-owned dependency is provisioned with its private lock and
lifecycle scripts disabled. Runtime paths are explicit and validated before
native startup or one-use claim consumption; selection never falls back.
The adapter preserves cells, active buffers and cursor columns. Readiness,
freshness, auth/menu rejection and numeric semantics remain separate Python
policy. Legacy `rstrip()` normalization is retained, with deliberate NBSP
padding support and rejection of unsupported invisible cells/whitespace.
Private IPC is bounded, fail-closed and deadline-bound. Terminal-generated
replies are discarded, not sent to Claude. Helpers and native descendants are
terminated/reaped, and cleanup failure cannot yield successful acceptance.

The isolated offline control on 2026-10-07 reached initial numeric context,
but not natural exit. Native resumed-context acceptance is therefore unproven.
No failed control is repeated automatically, no readiness rule is relaxed and
no bidirectional terminal contract is inferred. A new authenticated run still
requires a fresh immutable-final-commit grant after all prerequisite gates.
Rollback reverts the explicit caller selection and adapter/provisioning
changes together; retained external dependencies may remain. Legacy fallback
does not become acceptance. See the specification, plan and validation notes
linked below for test ownership, evidence and unresolved gates.

The 2026-10-08 harness author fix pass anchors freshness to input content rather
than transient status/cursor visits. A location transition requires a complete
numeric context view. Supported input/controlled echo fixtures remain positive
controls, while unsupported redraws block without widening recognition.

Selected POSIX entrypoints use cooperative managed-signal checkpoints and a
gated single-target supervisor before execution. Identity-bound Linux pidfds
and scoped subreaper adoption prove owned descendant termination/reaping even
when descendants create other sessions. Ownership publication precedes release
to the target, and claim consumption is rechecked after source reads.
Unproved capability, unrestorable handlers and cleanup failures block; no
SIGKILL/host-failure cleanup guarantee is inferred. This remains a test harness
boundary, with unchanged legacy routing, consent, provider scope and budgets.
Synthetic regression/full-package evidence addresses the two harness findings,
not the real native resume gate or the production expiry correction.

The 2026-10-09 diagnostic extension is test-only and opt-in at the selected
driver seam; the offline probe supplies the collector. Sampling occurs at
bounded transitions/failure/cleanup, never every redraw. Each phase retains
at most 16 records and 3 KiB in compact JSON, below the approved 16 KiB ceiling
and small enough for four phases within the existing 16 KiB outer report.
Limit exhaustion is explicit `truncated`; invalid fields/observation failures
set `rejected`. Neither flag nor any diagnostic record supplies acceptance.

The collector retains only closed point/reason/authentication/readiness enums,
bounded cursor/buffer coordinates, candidate count, freshness booleans and
optional leader-reap booleans. It rejects cell text, hashes, arbitrary exception
messages and unknown fields. The policy projection is pure: it performs no
freshness observation, terminal IPC or authorization. PTY proof event schemas
and their consumers remain unchanged; raw evidence/native history are still
removed before aggregate reporting. Wait/settle deadlines, close-IPC rejection
and observed process-leader reap are distinguished, not converted to success.
A reaped leader is not independent proof of complete descendant/root disposal.
No timeout extension, readiness relaxation, credential reuse or real retry
is introduced. Existing native/provider acceptance remains unproven.

The eligibility diagnostic follow-up keeps `INPUT_PROBE_INELIGIBLE` unchanged
and attaches an optional closed `inputEligibility` subcode only to that failure
record. The same pure evaluation supplies anchors and rejection metadata:
`FORBIDDEN_STATE`, `NO_MARKER`, `UNSUPPORTED_ROW`, `NONEMPTY_INPUT`,
`MULTIPLE_MARKERS`, `CURSOR_ROW_MISMATCH`, `CURSOR_COLUMN_MISMATCH`, and
`INSUFFICIENT_SPACE`. Unsupported draft/history rows remain `UNSUPPORTED_ROW`;
recognized visible suggestions/ready text are `NONEMPTY_INPUT`. An otherwise
eligible but changed instance-bound anchor is `ANCHOR_CHANGED`, not success.
The error carries the subcode from the actual rejecting evaluation rather
than recomputing it from a later snapshot. Unknown values/types and attachment
to other reasons/checkpoints are rejected. No cells, text, hashes, prompts or
marker are retained. Record/byte limits and acceptance events are unchanged.
The earlier native aggregate cannot retrospectively identify this subcode;
new native evidence still requires a separately bound operator grant.

The rejected-row refinement adds an atomic optional `inputRowRelation` /
`inputRowCause` pair only when `inputEligibility` is `UNSUPPORTED_ROW` on
`failure` / `INPUT_PROBE_INELIGIBLE`. A frozen pure assessment captures the
actual rejecting row and parser branch without retaining cells or row text.
Existing candidate, anchor and two-value evaluation APIs remain compatible;
their ordered acceptance/rejection tree is unchanged. The controller forwards
the error's sanitized pair, never re-evaluates a later screen for its cause.

Relations are `CURSOR_ROW`, `OTHER_CAPTURED_ROW`, and `CURSOR_OUTSIDE_CAPTURE`.
Parser categories are `INVISIBLE_FORMAT_CHAR` (Unicode Cf),
`UNSUPPORTED_WHITESPACE`, `MARKER_WIDTH`, `CONTROL_COMMAND_SHAPE` and
`UNRECOGNIZED_SHAPE`. First-rejecting character order is preserved. The control
category matches only the complete rendered `/context` or `/exit` shape with
supported indentation/padding; extra text or commands stay unrecognized.
That label proves neither historical provenance nor an authorized operation,
and every such shape remains rejected. Unknown values/types, partial pairs,
other reasons and unrelated eligibility categories cannot retain the pair.
The same 16-record/3072-byte phase and 16-KiB outer limits include these fields.
Diagnostic data is not input ownership, consent, freshness or acceptance.

The approved offline-development exception is opt-in `--debug-context` on
the disposable offline harness only. It cannot activate through installed
settings, an environment flag, a live caller, a serialized request or an
unaudited host. A sealed capture object binds the original offline scope,
terminal, private root identity and deadline; a fresh audit and cancellation
check fence capture. It observes one unsupported-input rejection after numeric
context inspection, never supplies terminal IO, consent, retry or acceptance.

At most one frame of 128 KiB is written to a fixed exclusive no-follow 0600
file in the existing owned 0700 root. No general transcript, native-history,
SDK stream or operator configuration is exported. Auth/provenance mismatch,
credential-like/canary material, invalid frames, changed ownership/permissions,
deadline, IO or size failures omit content. Sensitive detection is conservative
but not a universal redaction guarantee; audited synthetic-only isolation is
the primary exclusion of real operator data. Unknown/bad namespace facts block.

The only export is a maximum 4-KiB recut of the rejecting and cursor rows,
including cell geometry and escaped terminal/control-format characters. It
is labeled untrusted synthetic debug data, never instructions. The capture
object withholds its excerpt while the case root exists; failed case cleanup
omits it, and failed outer disposal discards the entire report. The unchanged
16-KiB outer limit includes debug data: oversized recuts are omitted with a
closed status, and an unfit metadata-only report is a closed failure. Context
25-second and run 165-second deadlines are not extended for inspection.

The raw local file is temporary and removed before the final result. The
sanitized excerpt intentionally sent to the operator's chat can persist in
conversation/tool records; deletion or archival is not promised to erase every
copy. No raw frame is added to Git, staging, CI artifacts or release contents.
The installed policy remains unchanged. This exception needs its own fresh
exact-commit native grant after synthetic tests, review and package validation.
Process/kernel/host failure is not a secure-erasure guarantee. Previously
deleted captures cannot be recovered or substituted by this new mode.

The 2026-10-09 pinned-input extension separates pure empty-input eligibility
from active proof. Only the audited isolated offline launcher supplies a private
scope bound to its terminal and original deadline. A unique 16-character marker
is typed without submission, matched cell-by-cell in the current anchored input,
then removed using one guarded Ctrl+U. A newer empty frame produces an ephemeral
one-shot proof for the fixed `/exit`; it does not authorize credentials, model
input, tools or permission answers. Instance/transition substitution, auth/menu,
replay, unknown shapes, draft/suggestion text, expiry and partial-write failure
block. Concrete exit writes recheck only their already-owned prefix after waits.
No changed context grid, stale prompt or diagnostic record creates this authority.

The Node engine remains passive and terminal replies are not forwarded. Public
CLI/env activation and live wrappers are unchanged/unavailable for this route.
Audit-only namespace checks now also prove issuer/helper binding without mounting
Claude or changing the existing audit report fields. Shortcut interpretation in
an unproved UI remains a residual risk contained by offline isolation; this is
not a production credential-entry remedy. Original context/run/capture/IPC and
diagnostic budgets, startup consent and raw/history disposal remain enforced.
Rollback removes active selection and protocol integration together, preserving
the prior passive fail-closed behavior, not a recovery fallback. Native resume,
Skill and authenticated acceptance still require separately granted evidence.

The 2026-10-08 production lifetime correction anchors execution and validation
to the exact stored grant. One branded immutable deadline and fresh clock are
shared with the selected adapter; numeric clocks remain only a trusted test
seam. Invalid/backward samples fail closed rather than renewing authority.
An installed lifetime identity is required in addition to discovery, native
consent and the unchanged role/origin/effect/credential/artifact gates.

The runner and both adapters fence concrete dispatch before and after awaits,
including protected-value reads, startup, link metadata, upload materialization,
screenshots and delayed interception. Resource ownership is captured before
post-await expiry checks so disposal remains possible. Supported timeouts are
narrowed, but no guard can unsend an already-dispatched browser API. Late
results are inconclusive; expired authority cannot validate or retry.

Owned one-shot consumption uses bounded raw-state validation and the existing
lock, independent of current-time admission. It removes only the original
approval and tagged calls; later approvals are preserved and ambiguous legacy
ownership blocks completion. Cleanup remains permitted after expiry. Failed
completion or cleanup overrides success. Synthetic proofs address the prior
production expiry finding; scoped candidate review and real native/provider
acceptance are separate gates, not implied by those tests.

The scoped candidate review identified one validation-state ownership gap:
completion selected an active record by operation ID/reference after an await
and could reconcile a different later approval. The fix pass binds activation,
call staging, outcomes and completion to the captured original grant under the
existing lock. Native callbacks additionally match the call's approval tag.
Replacement approvals remain unchanged; mismatched writes cannot report
validated success. No second review cycle or broader historical scan is used.

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
- Test-only terminal design: `docs/superpowers/specs/2026-10-07-p0-04b-headless-terminal-adapter-design.md`
- Test-only terminal plan: `docs/superpowers/plans/2026-10-07-p0-04b-headless-terminal-adapter.md`
- Isolated pinned-input spec: `docs/superpowers/specs/2026-10-09-p0-04b-pinned-input-proof-design.md`
- Isolated pinned-input plan: `docs/superpowers/plans/2026-10-09-p0-04b-pinned-input-proof.md`
- Approved remediation design: `docs/superpowers/specs/2026-10-07-p0-04b-review-remediation-design.md`
- Implemented harness author-fix plan: `docs/superpowers/plans/2026-10-07-p0-04b-harness-review-fixes.md`
- Production-lifetime plan: `docs/superpowers/plans/2026-10-07-p0-04b-approval-lifetime-remediation.md`
- Test-only terminal evidence: `tests/validation-notes.md`
- Implementation plan: `docs/superpowers/plans/2026-08-31-p0-04b-browser-automation.md`
- One-shot workflow plan: `docs/superpowers/plans/2026-09-02-p0-04b-one-shot-workflow.md`
- Canonical contract: `references/browser-operations.md`
- Related authority boundary: `docs/architecture/ADR-009-global-prompt-injection-defense.md`
- Related execution boundary: `docs/architecture/ADR-008-native-execution-boundary.md`
