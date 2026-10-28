# P0-04B stage-owned structured context measurement

Status: approved by the operator, 2026-10-23. Implementation and native execution
are not authorized by that approval; the implementation plan is the next gate.
The operator selected option2: eight reads, before/after each of four main
stages, then approved this written specification. This specification was promoted to Git during approved inline implementation on 2026-10-24;
the architectural amendment follows in the implementation plan.

## Intent and evidence boundary

Replace separate interactive context-only probes for the MAIN measurement
stages with public structured reads on the client that performs each stage's
already-required turn. Preserve stage-specific tool/MCP policy and expose the
new sampling semantics rather than pretending to reproduce the old baseline.
This changes test acceptance instrumentation, not operational browser authority.

Product baseline: 9e6eaf623bd46777f3f167817a4f9ed0f365ceb6 in the existing
p0-04b-browser-automation worktree. No product changes are made by this draft.
The one-client offline provenance artifact
488de64310a64ab3fbd17194812b91a666ecee7db8123b2c8fb5197787ad6632
passed M0_M1_PROVENANCE_SUPPORTED. It proved accounting association across one
synthetic turn, including zero new M1 counting requests. It did NOT prove resume,
project loading, real tokenizer accuracy or the four-stage workflow.
Its consumed grant and frozen files remain unchanged and cannot authorize this
new work. See ../../reviews/2026-10-23-p0-04b-native-provenance-result.md.

Success for this increment is qualified main-stage evidence only. It cannot
produce full P0-04B acceptance, ACTIVE browser coverage, role acceptance or a
merge. The canonical twelve-role gate remains mandatory and unresolved here.

## Approaches and selected tradeoff

1. Five anchors: one initial before plus four after reads. Minimal schema
   change, but successive readings cross tool/MCP configuration boundaries.
2. Eight reads, selected by the operator: one pair per stage with configuration
   fixed for that pair. Adds three public context calls, not three generation
   turns. Makes each observation's configuration boundary explicit; does not
   establish causal attribution of every token delta.

A single always-enabled client with the union of tools/MCPs is not equivalent:
it changes exposure, schema loading and stage safety. Public MCP toggling exists
in the installed SDK, but is not a replacement for all native built-in tool
allowlist changes. Private control messages or broad union grants are excluded.

## Goals, non-goals and anti-goals

Goals: one owned client per stage; two structured observations on that client;
unchanged required stage actions; native event/identity validation; bounded
content-free evidence; fail closed on unsupported/ambiguous capabilities.

Non-goals: twelve-role redesign, browser allow/deny transport replacement,
no-new-turn M2 proof, status-line/TUI repairs, token accuracy, changing provider
models, changing compaction thresholds, installing dependencies or automatic
provider fallback. The existing browser workflows and their guards stay intact.

Anti-goals: synthetic percentages standing in for native data; a requested
resume ID standing in for native association; silently broadening tools; copying
operator settings; adding a warm-up/model request to rescue a failed read;
claiming a main-only result passes the full aggregate; building another generic
observer after an inconclusive result.

## Stage lifecycle and fixed configuration

Each stage owns its connection, stream consumer and child processes. Clients
run sequentially, never concurrently. A single owned temporary project/config/
HOME contains the installed project and the synthetic session history shared
between stages. Operator state is not mounted or searched. Only this temporary
history persists until all four stages close; it is deleted before aggregation.

| Stage | Native built-in tools | Allowed call | MCP configuration |
| --- | --- | --- | --- |
| skill | Skill | Skill(context-continuity), once | empty |
| subagent | Agent | Agent(diagnostic-operator), exact existing input, once | empty |
| discovery | ToolSearch | existing select query once when available | measurement fixture only |
| use | no built-in tools | exact context_fixture_ping with run nonce, once | measurement fixture only |

These are acceptance-fixture identifiers, not fixed operational browser tools.
The discovery unavailable branch retains its existing zero-search behavior;
absence is measured, not manufactured into a successful search. MCP connection,
listing and one nonce-bound use still need actual structural evidence.

For each stage:

1. Validate the current reservation, immutable artifact and stage index. Freeze
   options before connection; no mutation of tool/MCP policy within the pair.
2. Connect once. First stage creates the requested fresh session; later stages
   request the session actually observed in the prior stage. No continue/fork.
3. Read before using get_context_usage. Keep it provisional: before-turn reads
   alone cannot confirm native session identity or qualify a resumed session.
4. Submit exactly the existing synthetic stage prompt once. Validate actual init,
   tool input/result completion and successful native terminal result. The
   first stage must observe its requested fresh identity; later init/result
   must agree with the preceding observed identity. Requested IDs are not proof.
5. Read after on the SAME connected client. Validate its accounting association
   and observation shape before accepting the pair.
6. Close the client, reap its children and capture final fault/event state.
   Late tool, error, reset or compaction events invalidate provisional success.
   Only then may the next stage start. Final cleanup failure dominates success.

One continuous public message consumer spans the stage; do not create competing
receive_response/receive_messages consumers. A ResultMessage is a turn boundary,
not permission to ignore later lifecycle events while reading context/closing.
Reject unexpected background/deferred work instead of abandoning a live task.
Reuse existing timeout/process ownership patterns, not a new supervisor stack.
An unsupported public lifecycle/event surface is inconclusive, never a reason
to inspect private wire operations or use an interactive fallback automatically.

## Identity, resume and project-equivalence gates

Same-client before/after association is provisional until the required turn
supplies matching native init/result evidence. No extra identity turn is added.
Native reset/compaction, mismatched identity, absent terminal success or an
unrequested call stops before the next stage. A missing/corrupt history file
must not be accepted as an implicitly new session with the same requested ID.

Resume must be qualified by a bounded offline integration control using the
required stage turns, not an M2-only observer. The owned gateway must observe
the expected prior synthetic history marker in the resumed generation request;
retain only its boolean association. Negative controls remove/corrupt/substitute
owned history or replay a different session and must fail LOCALLY, as defined
below; they are not additional native runs. This proves the
fixture's history route, not cryptographic identity for arbitrary native state.
The actual provider-backed route remains a later independent gate.

For the OFFLINE positive control, the gateway creates a fresh opaque marker for
each of the first three stage-terminal synthetic assistant replies. It returns
the normal stage acknowledgment plus that marker as inert text. The next
stage's first top-level generation request must contain the immediately prior
marker in its assistant history. A fixed acknowledgment, requested session ID
or marker merely appearing in a new user/system prompt does not satisfy it.
The gateway binds its in-memory expected marker to this attempt and ordered
stage; copied history from another run cannot supply the fresh marker. Nested
agent requests do not replace that top-level check. Preserve the exact existing
user prompts and tool inputs: only the owned emulator's synthetic reply text
changes. Markers/history are temporary and never exported. This synthetic reply
amendment must be named in the later offline grant; it does not authorize
injection or rewriting of real provider replies.

All history-negative controls are unit/in-memory SDK/process-boundary cases,
without launching Claude. Expected rejection is a passing negative test, not an
inconclusive native attempt. The one proposed native run contains ONLY the four
positive stage turns; stop at its first missing/ambiguous proof. Do not claim
native remove/corrupt/substitute failure-mode coverage from the local negatives.
That unexecuted native negative matrix is not a hidden prerequisite or an
automatic request for more grants in this increment.

Use the existing Python public SDK route and canonical CLI selected by the
harness. Detect required methods/options/event fields at runtime; do not pin
versions or silently choose a bundled executable. Record only bounded observed
runtime labels. Missing capabilities block the adapter; no auto-install/update.

Unlike the minimal provenance fixture, load the installed project instructions,
skills, agents and native hooks. Use the Claude Code system-prompt preset and
explicit project/local setting sources inside the disposable project. Do not
load the operator's user settings or programmatically replace the installed
agent definitions. Verify actual expected init/tool/hook events and safe native
guard coverage where operational tools can execute; configuration files alone
remain CONFIGURED_UNPROVEN. SDK callbacks must not inject blanket allow or
replace the native command/browser guards. Preserve default permission mode.

Mandatory native hook proof for this MAIN-ONLY increment is the installed
PreToolUse:Agent measurement hook on its one exact diagnostic-operator call:
matching hook_started/hook_response, session/tool identity, successful hook
completion, P004B_MEASUREMENT_GUARD_FIRST_CALL and the fresh exclusive claim.
Reject missing/duplicate/conflicting evidence. Reuse the existing narrow native
measurement guard, not a new SDK allow callback. Do not invent PostToolUse:Agent
coverage: that matcher is not configured by the current measurement setup.
The prescribed stages do not require operational Bash/browser execution; do
not add a guard probe or change the acknowledgment-only agent prompt to produce
it. Command/browser operational coverage remains CONFIGURED_UNPROVEN, never
ACTIVE, in this increment. Its real native Pre/Post/ask proof remains part of
the separate allow/deny and full acceptance gates, unchanged here.

The installed SDK parses AssistantMessage usage and HookEventMessage raw data;
local SDK-boundary tests must show required fields survive parsing. Merely
passing an include-hook-events option is not proof that a future runtime emits
or preserves the evidence. System-prompt snapshot/resume behavior must also be
qualified; no silent snapshot override to change native semantics.

## Sampling and accounting semantics

Record the native six-scalar context projection (total, effective/raw window,
percentage, auto-compact state, category count), plus the closed apiUsage state
ABSENT/NULL/VALID/INVALID and exactly four nonnegative safe-integer usage fields
when valid. No category names, memory paths, prompts or raw response enter the
retained measurement. Keep auto-compaction enabled; no absolute window override.

Each after observation must match the final completed TOP-LEVEL response's
native per-response usage within that stage, exposed through public SDK events.
Project only input_tokens, output_tokens, cache_creation_input_tokens and
cache_read_input_tokens. Do not substitute cumulative ResultMessage.usage,
nested subagent usage, cost, requested model or a computed input+output total.
If no unambiguous complete latest-response tuple exists, fail closed as
USAGE_PROVENANCE_UNPROVEN; do not issue another query to obtain one.
Before apiUsage may be absent/null; malformed numeric accounting blocks the
pair. If after accounting equals valid before accounting, its values do not
distinguish replay: keep the bounded observation but do not qualify provenance
or add a challenge/warm-up turn. Do not send the laboratory's artificial usage
challenge to a real provider or rewrite real accounting.

Equal percentages, zero/negative token deltas and non-monotonic context are not
intrinsically failures in real workloads. The spike's artificial responsive-
total test is not a universal token-growth requirement. Accounting association
must instead satisfy the native response proof above. Denominator drift within
a pair yields NON_COMPARABLE, not a forged delta or a forced window override.
No raw after percentage is synthesized from a different capacity.

Report before/after per stage with observed native deltas only when comparable.
Do not label those deltas exclusive Skill/Agent/MCP cost: prompts, results,
history, estimates and system configuration can contribute. Across connection
boundaries, distinguish measurements rather than claiming a controlled cost
difference. The first restricted Skill baseline is a new sampling profile;
historical default-tool PTY baselines are not equivalent or silently migrated.

## Evidence, schemas and acceptance separation

Use a new test-only private schema MAIN_STAGE_CONTEXT_V2 with exactly four
ordered stage records, each containing one before/after pair, bounded structural
action counters, accounting/identity/continuity/configuration association flags,
closed outcome/reason and final cleanup. Reject extra/missing/reordered records,
unknown fields and forged flags. Run nonce and actual session identifiers may
exist only in the owned private sidecar for current-run validation, never in the
public aggregate. Never hash credentials or raw content as identity evidence.

The existing trusted measurement schema requires five anchors AND twelve roles.
Do not serialize eight reads as that old schema or coerce main-only evidence into
its success result. Introduce a distinct main-only evaluation/profile that
cannot mark ACTIVE, browser-accepted, full-accepted or complete the TODO. The
normal full smoke/validator remains blocked without its canonical role evidence;
no opt-out flag may turn that missing gate into success. Allow/deny workflow
validation, effects, hooks and cleanup requirements are unchanged.

Only final structural/numeric evidence survives. Synthetic native history and
any raw stream required for processing remain inside the owned root and are
deleted before publishing. Refresh facts after all clients/gateways shut down;
the previous stale-snapshot regression remains covered. A failed cleanup never
publishes success or frees the consumed reservation for reuse.

## Budgets and authorization: proposals, not a grant

Local unit/SDK-in-memory tests may prepare this route after implementation
approval, without launching Claude. There is no native/provider authorization
in the operator's selection of option2 or this document's approval.

Proposed separately authorized OFFLINE integration acceptance ceiling:
four main user-query invocations, eight public context calls, at most forty
generation HTTP requests including nested-agent work, at most192 counting HTTP
requests total and48 per stage; one main native process plus at most one SDK
auxiliary version probe per stage. The owned loopback gateway must count and
deny beyond each request budget with a sticky fault. At most25 seconds per
non-generating operation,120 seconds per whole stage and600 seconds overall,
including setup and cleanup. No automatic retry, repetition, fallback or new
diagnostic run. Runtime retries are not silently treated as one HTTP request.
This budget is larger than the consumed one-client spike and needs its own
exact-artifact grant; none of those prior numbers/permissions carry over.

Provider-backed execution is NOT part of this increment. Eight control calls
can generate additional native token-count requests invisible to the ordinary
SDK message stream. The offline cap192 cannot be asserted for direct real-
provider traffic without an observable enforcement route. A future live design/
grant must explicitly settle counting-request observability and cost/timeout
limits, endpoint/model/credential transport and the unresolved role coverage.
Do not add an interception proxy or claim six total HTTP requests here. Existing
six workflow/query invocations and actual provider HTTP requests are different
units. Do not launch the full authenticated smoke merely to rediscover the
already-known missing role gate.

## Verification and completion criteria

Required local controls before a native grant:

- Eight ordered reads and four required turns, fixed policy per pair, one stream
  consumer; no extra identity/warm-up request or concurrent client.
- Actual SDK in-memory parsing/forwarding for usage, init/result, tool lifecycle,
  native hook fields and late faults; no CLI execution in these unit controls.
- Missing/null/malformed/replayed/cumulative/nested accounting cannot manufacture
  after provenance. Zero/negative deltas and unchanged percentage remain valid
  observations where accounting and denominators qualify the pair.
- Missing/changed native identity, reset, compaction, dangling background work,
  reordered/extra calls, configuration drift and denominator drift fail closed.
- Stage allowlists, exact inputs/results, tool-search available/unavailable
  branches and MCP nonce/counter evidence preserve existing behavior.
- Extra/unknown schema fields, old-schema coercion, missing roles, unsafe files,
  wrong run/session or partial success never produce full acceptance.
- Timeout/cancellation, late shutdown faults, child/root cleanup and exclusive
  reservation reuse controls preserve first-fault/no-repeat behavior.
- Declared dependency absence is reported honestly. The adapter cannot qualify
  if its SDK-boundary tests were skipped; no dependency installation is implicit.

Future offline native acceptance must qualify real project loading, required
hook/event preservation, stage-specific exposure, resumed owned history and the
eight accounting observations with those same four turns. Stop on the first
inconclusive result; report its causal boundary rather than automatically
building another observer. Offline support is not provider/browser acceptance.

After implementation: full relevant local gates, independent review, versioned
ADR/index update explaining the new sampling/schema and test-only dependency,
release/changelog changes only if repository conventions require them. Preserve
operator edits and existing immutable experiments. No push/PR/merge is included
in design approval; full P0-04B TODO stays pending until its complete gates pass.

## Builder discretion and current design calls

Builder may choose internal module/function names, typed helper layout and test
fixture organization, while reusing existing ownership/reducers where applicable.
Do not expand native calls, schemas, retained content, tools or authority as a
convenience. The later implementation plan must name exact files/contracts.

Designer calls for operator review: new main-only schema/profile, no universal
positive-delta requirement, response-level rather than cumulative accounting,
owned temporary history between stages, capability-gated existing SDK/CLI,
offline-first qualification and the proposed larger offline budget. Live and
role designs remain separate, explicit blockers; not work silently delegated
to an implementer. No implementation plan is written before design approval.
The offline gateway's reply-only continuity markers, local-only negative
matrix and measurement-hook-only native qualification are also explicit design
calls, not prior operator approvals. The builder check resolved these boundaries before operator approval; its local record remains in the preparation directory.

## Official basis and local anchors

- https://code.claude.com/docs/en/agent-sdk/python#claudesdkclient
- https://code.claude.com/docs/en/agent-sdk/python#claudeagentoptions
- https://code.claude.com/docs/en/agent-sdk/python#contextusageresponse
- https://code.claude.com/docs/en/agent-sdk/sessions
- tests/live-browser-operations-smoke.sh:857-1030, stage/probe ownership and role gap
- tests/browser_operations_live.py:898-970 and1252-1330, full sidecar gates
- docs/architecture/ADR-010-browser-automation-boundary.md, unchanged full acceptance
- ../../reviews/2026-10-23-p0-04b-native-provenance-result.md; local immutable preparation evidence remains outside Git
