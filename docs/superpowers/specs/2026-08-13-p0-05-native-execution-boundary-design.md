# P0-05 Native Execution Boundary Design

Last updated: 2026-08-21.

## Goal
Define an unambiguous, enforceable boundary between protected native shell
execution and operational tools that require additional typed guarantees.
Close the uncovered direct-main-session Bash route without replacing Claude
Code, Nori, the existing command guard, or future typed operational tooling.
## Scope
This delivery covers:
- a canonical execution-routing policy for diagnosis, proposal, execution,
  validation, and rollback;
- explicit criteria for protected Bash, executor delegation, typed tools, and
  refusal;
- opt-in, reversible project-local activation of the existing command guard
  for direct Bash calls from the main Claude Code session;
- preservation of operator-owned Claude Code settings and hooks;
- fail-closed behavior when guard coverage cannot be confirmed;
- deterministic source, installed-artifact, and live behavioral validation;
- an accepted, indexed ADR for the implemented boundary.

P0-04B owns browser automation controls. P3-16 owns implementation of the
typed MCP operational gateway. P0-05 defines the interfaces and routing rules
that both must later satisfy, but it does not implement browser actions, an MCP
server, a model proxy, a custom provider client, or a parallel runtime.

The design does not pin Claude Code, Nori, a provider, a model, Node.js, or an
MCP protocol revision. Runtime-sensitive acceptance is capability-based and
records observed versions only as evidence.
## Established Runtime Facts
Current official Claude Code documentation establishes these contracts:
- `PreToolUse` hooks run before the permission prompt and can return `allow`,
  `ask`, `deny`, or `defer` through `hookSpecificOutput.permissionDecision`.
- Multiple `PreToolUse` decisions use the precedence `deny`, `defer`, `ask`,
  then `allow`. An `allow` hook does not override configured `deny` or `ask`
  permission rules.
- `bypassPermissions` approves calls that reach the permission-mode step, but
  hooks and applicable deny/ask rules are evaluated first. It is a session
  autonomy choice, not an operational risk level or a safety control.
- Claude Code explicitly warns that `bypassPermissions` offers no protection
  against prompt injection or unintended actions and recommends isolated
  environments for that mode.
- Project hooks can be stored in `.claude/settings.json`; local project hooks
  can be stored in `.claude/settings.local.json`; skill and agent frontmatter
  hooks are active only while that component is active.
- A custom subagent's frontmatter hooks run when it is spawned and when that
  agent is selected as the main session through `--agent` or the agent setting.
- Ordinary main-session hook input omits the optional `agent_type` and
  `agent_id` fields. Those fields identify `--agent` and subagent execution;
  their absence is therefore the native ordinary-main-session shape, not a new
  executor identity.
- MCP tools use the `mcp__<server>__<tool>` naming convention and require
  permission. Exact tool grants are narrower than granting all tools through a
  broad permission mode.

Current MCP specifications establish these contracts:
- every tool has an `inputSchema` and may have an `outputSchema` for structured
  results;
- tool annotations such as `readOnlyHint`, `destructiveHint`,
  `idempotentHint`, and `openWorldHint` are hints, not enforcement claims;
- clients must treat annotations as untrusted unless the server itself is
  trusted;
- authorization, consent, access control, validation, and safe execution
  remain responsibilities of the host and server implementation.

Official references:
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/hooks-guide
- https://code.claude.com/docs/en/permissions
- https://code.claude.com/docs/en/permission-modes
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/mcp
- https://code.claude.com/docs/en/tools-reference
- https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- https://modelcontextprotocol.io/specification/2025-06-18/basic/index
## Existing Boundary and Gap
ADR-004 attaches the deterministic native command guard to the eight executor
subagents through `PreToolUse` and `PostToolUse` Bash hooks. That implementation
already provides:
- a closed command catalogue;
- bounded Bash and PowerShell parsing;
- target, environment, pipeline, redirect, and data-flow binding;
- one canonical risk level plus orthogonal modifiers;
- native `allow`, `ask`, and `deny` decisions;
- destructive confirmation in every permission mode;
- credential-use binding without storing credential content;
- content-minimal audit records and compaction invalidation;
- fail-closed handling of unknown, malformed, evasive, or unmodelled calls.

The source baseline on 2026-08-13 passed the complete Debian WSL package gate:
267 command-guard tests, 82/82 semantic mutations, 100 percent critical module
coverage, package validation, and all supporting Python suites.

The remaining gap is execution scope. ADR-004 records that a direct Bash call
from the ordinary main session may be outside the executor-frontmatter guard.
The same operational command can therefore have different enforcement based
only on whether the model delegated it. Instructions alone cannot close that
tool boundary deterministically. The existing input contract also rejects an
ordinary main-session event because it currently requires `agent_type`, so
installing the hook without extending that exact native shape would fail closed
but could never protect a direct call.
## Decision
Use one existing classifier and three enforcement routes:
1. **Protected main-session Bash.** An explicit configurator installs exact
   project-local `PreToolUse` and `PostToolUse` Bash hooks that invoke the
   existing command guard. This route is available only when exact ownership,
   effective settings, runtime capability, and live hook behavior are
   confirmed. The guard recognizes an ordinary main session only when both
   optional agent identity fields are absent; it does not add a synthetic
   main-session name to the executor catalogue.
2. **Protected executor delegation.** If main-session coverage is absent or
   inconclusive, route operational shell work to one of the eight executor
   subagents whose installed frontmatter carries the same hooks. If installed
   executor coverage is also unconfirmed, do not execute; return the plan and
   proposed command.
3. **Typed operational tool.** Require an MCP tool or equivalent typed
   interface when the operation needs invariants the guard cannot establish
   from a bounded shell call. P0-05 specifies the contract; P3-16 implements
   the gateway.

There is no second risk classifier, no JSON wrapper around Bash, and no textual
approval token that can bypass a native hook decision.
## Canonical Routing Matrix
The routing decision is based on required guarantees, not convenience or tool
availability.

| Operation | Required route | Minimum conditions |
|---|---|---|
| Narrow diagnosis | Protected Bash or typed read | Guard proves complete bounded read, target, environment, stages, limits, and data flow |
| Plan or proposed command | No execution tool required | Clearly labelled as unexecuted; includes risk, target, validation, and rollback when applicable |
| Catalogued non-destructive change | Protected Bash | `ask` in normal modes; `allow` is possible in `bypassPermissions` only for the exact fully modelled call |
| Destructive shell operation | Protected Bash with exact human decision | Guard returns `ask` in every mode; changed input requires a new decision |
| Ambiguous, obfuscated, unbounded, uncatalogued shell, or shell without an explicit target | Refuse/reformulate | Guard returns `deny`; permission mode and prose cannot override it |
| Transactional or coordinated multi-target change | Typed operational tool | Bound schema, authorization, idempotency, audit, validation, and rollback |
| Externally persisted workflow mutation | Typed operational tool unless a closed shell grammar proves the complete effect | Exact target, content, authorization, expiry, and compensating action |
| Browser read | Future P0-04B route | Browser-specific observation and untrusted-content controls |
| Browser mutation | Future typed P0-04B route | Explicit action and target binding; exact approval; post-action validation |
| Typed capability absent | Protected Bash only if every shell invariant is proven | Never weaken the shell guard to emulate a missing typed tool |
| No protected route confirmed | No execution | Return observed limitation, plan, proposed operation, and required operator action |
## When Protected Bash Is Sufficient
Protected Bash is sufficient only when the existing guard can derive all of the
following from the actual call and trusted runtime metadata:
- a finite command structure with every stage and redirect parsed;
- one explicit target and operational environment for each effect;
- complete literal or bounded selector semantics;
- the highest plausible risk and every applicable modifier;
- credential source, consumer, identity, transport, and authorization domain;
- the complete external effect and data flow;
- a bounded validation action;
- rollback or compensating instructions when the change is reversible.

The guard may return `ask` for a fully understood call that requires an exact
human decision. It returns `deny` for prohibited or inconclusive forms. `deny`
must lead to safe reformulation, delegation to a suitable typed tool, or no
execution; it must never be converted into a generic approval request.
## When a Typed Tool Is Required
A typed operational interface is required when safe execution depends on one
or more invariants that cannot be proven from a single guarded shell call:
- transaction boundaries, commit state, or atomic multi-step behavior;
- coordinated multi-target state and partial-failure handling;
- durable idempotency or replay protection;
- authorization bound to structured parameters, actor, expiry, and state;
- externally persisted changes whose exact content and target must be reviewed;
- server-side audit correlation;
- structured validation and rollback across calls;
- destructive behavior that cannot be represented by a closed shell grammar.

The future P3-16 tool family remains:
- `ops_read`;
- `ops_propose_change`;
- `ops_execute_approved_change`;
- `ops_validate_change`;
- `ops_rollback_change`.

Each mutable typed call must bind at least target, environment, scope, risk,
authorization reference, idempotency key, expiry, audit correlation,
credential reference, expected precondition, validation, and rollback or
compensating action. The server must validate these fields. MCP annotations
improve discovery and user experience but are not accepted as authorization or
proof of behavior.
## Main-Session Activation
Extend the `command-driven-operations` skill with an explicit configurator:
- `--check` inspects effective scopes, exact owned hooks, capability blockers,
  and ownership drift without modifying files;
- `--apply` adds only the package-owned main-session Bash hooks to
  `.claude/settings.local.json` and records exact non-secret ownership;
- `--remove-owned` removes only entries that remain byte-for-byte equal to the
  recorded package-owned values;
- `--help` performs no discovery or write.

The configurator derives hook commands from its installed skill directory. It
must not assume the repository checkout path, replace a settings object, remove
another owner's hook, overwrite a status line, alter MCP configuration, or
write a credential. It uses strict duplicate-key JSON parsing, link/reparse
rejection, owner-only files, bounded locking, atomic replacement, crash
recovery, and exact owned-only rollback, following the proven P0-04A settings
ownership model.

Both Bash lifecycle hooks are required. `PreToolUse` authorizes the actual
call. `PostToolUse` records only successful non-secret authorization state used
by the existing credential-reuse contract. Installing only one phase is an
incomplete and unusable configuration.
## Coverage State
The package exposes these states without claiming more than the evidence:
- `ACTIVE`: exact effective hooks are owned and a live synthetic call proves
  that the current session invokes the main-session guard;
- `CONFIGURED_UNPROVEN`: exact settings are present but live runtime behavior
  was not exercised in the current validation context;
- `ABSENT`: the package-owned hooks are not effective;
- `CONFLICT`: settings, ownership, managed policy, links, or runtime
  capabilities prevent an exact determination;
- `UNSUPPORTED`: the detected runtime does not expose the required hook
  contract.

Only `ACTIVE` supports a claim that direct main-session operational Bash is
protected. `CONFIGURED_UNPROVEN`, `ABSENT`, `CONFLICT`, and `UNSUPPORTED` route
shell execution to a proven executor subagent or result in no execution.
Runtime proof is evidence, not a durable authorization. It is invalidated by a
new or resumed session, `/clear`, compaction, a changed permission mode,
runtime, settings scope, hook artifact, installed path, policy, or relevant
managed policy.
## Session Proof Protocol
Exact installed settings establish `CONFIGURED_UNPROVEN`, never `ACTIVE` by
themselves. Before the first direct main-session operational Bash call in a
session, issue exactly this stdout-only probe through the native Bash tool:

```bash
printf P005_GUARD_PROBE
```

The command guard deliberately treats this uncatalogued command as a denial.
The session becomes ephemerally `ACTIVE` only when that same tool call returns
the expected structured command-guard `deny` decision and reason. If the hook
does not run, the only effect is bounded synthetic text on stdout; the session
remains `CONFIGURED_UNPROVEN` and must delegate to a proven executor or perform
no execution. A timeout, prompt echo, prose response, settings inspection,
separate process, or result from another tool call is not proof.

The probe proves hook coverage, not authorization for later work. Every actual
command is independently classified and must obey its own native decision.
Proof is held only in the current agent state; it is not written to settings,
ownership, audit, continuity, transcript-derived, or other package evidence.
## Operator Ownership
Activation is opt-in because Claude Code settings belong to the operator. The
package may recommend activation, but Nori installation alone must not silently
edit local preferences. Apply and removal must be idempotent and preserve:
- unrelated settings keys;
- operator and organization hooks;
- P0-04A continuity hooks and status-line ownership;
- managed settings precedence;
- changes made after package activation.

The configurator must refuse malformed, duplicate-key, linked, replaced,
unbounded, or concurrently changed targets. Recovery may complete or roll back
only package-owned values; it must never restore a whole stale settings backup.
## Instructions and Delegation
Root instructions and the command-driven operations skill will state:
- diagnosis, proposal, execution, validation, and rollback are distinct phases;
- operational Bash in the main session requires `ACTIVE` coverage;
- settings presence alone is `CONFIGURED_UNPROVEN`; an exact harmless probe in
  the current session must receive the expected structured guard denial;
- absent or inconclusive coverage requires delegation to a matching protected
  executor;
- analytical subagents without Bash never acquire execution capability;
- an executor obeys the exact native hook result for every call;
- a missing typed capability never authorizes free-form shell;
- a changed command, target, environment, scope, credential transport, or
  authorization context requires fresh evaluation;
- a proposed command is never represented as executed evidence.

This instruction layer provides correct routing and clear operator behavior.
Deterministic protection remains at the tool boundary through hooks and typed
server validation, not through prose alone.
## Validation
Deterministic validation must include:
1. routing-policy tests for every matrix row and phase distinction;
2. source tests proving all eight executors keep exact Pre/Post Bash hooks;
3. settings merge, check, ownership, rollback, interruption, race, malformed
   JSON, duplicate-key, link/reparse, and bounded-input tests;
4. tests proving `bypassPermissions` never changes risk and never bypasses
   destructive `ask` or inconclusive `deny`;
5. tests proving MCP annotations are never treated as authorization;
6. installed Nori artifact inspection with exact hook path resolution and
   preservation of unrelated operator settings;
7. a static safety contract for the opt-in live harness;
8. main-session input tests proving that both optional agent identity fields
   absent select the ordinary main-session route, while partial, synthetic, or
   unknown identities fail closed and executor identities remain exact;
9. a real Claude Code main-session synthetic probe in normal and
   `bypassPermissions` modes, with no production target and no persisted
   prompt, transcript, raw command, or credential;
10. an executor fallback probe proving the same guard decision when direct
    coverage is unavailable;
11. the complete package, schema, content, CI, security, and mutation gates.

The live harness must distinguish configured settings from observed hook
execution. A settings file alone cannot produce `ACTIVE`. If current runtime
behavior cannot be proven, the result is honestly inconclusive and direct
main-session execution remains unavailable.
## Documentation and Release
Implementation will add ADR-008 and index it. Update `AGENTS.md`, the command
skill, operator references, README, `docs.md`, CHANGELOG, validation notes, and
the project version where required by the repository's release-history policy.
The definitive external TODO remains outside Git and is marked complete only
after implementation, real validation, independent review, green CI/Security,
and merge into `main`.
## Alternatives Rejected
- **Documentation only:** rejected because it leaves direct main-session Bash
  outside deterministic enforcement.
- **A second shell classifier or JSON Bash envelope:** rejected because it
  duplicates ADR-004 and can diverge from the actual tool input.
- **Immediate MCP gateway implementation:** rejected because P3-16 owns that
  larger subsystem and depends on additional P0 and P1 work.
- **Silent or whole-file settings installation:** rejected because it can
  overwrite operator preferences and stale backups.
- **Treating `bypassPermissions` as safety or risk:** rejected because official
  behavior makes it a broad permission-mode decision.
- **Trusting MCP annotations as enforcement:** rejected because the MCP
  specification defines them as untrusted hints.
- **Falling back to free-form shell when a typed tool is missing:** rejected
  because missing capability cannot weaken operational invariants.
## Acceptance Criteria
P0-05 is accepted only when:
- the routing matrix clearly distinguishes diagnosis, proposal, execution,
  validation, and rollback;
- every autonomous Bash write is protected by the deterministic guard, a
  catalogued command, explicit target/environment binding, and authorization
  compatible with the current permission mode;
- direct main-session Bash is claimed protected only after exact configuration
  and live proof;
- absent or inconclusive direct coverage delegates to a proven executor or
  performs no execution;
- typed interfaces are normatively required wherever shell cannot establish
  the necessary transactional, multi-target, idempotency, authorization,
  audit, validation, or rollback invariants;
- browser automation and gateway implementation remain outside this delivery;
- settings activation and removal preserve operator ownership;
- source, installed, and real runtime tests pass on the exact reviewed commit;
- independent review has no unresolved Critical or Important finding;
- CI and Security pass on that exact commit;
- the approved final head is merged into `main` before the external TODO is
  marked complete.
