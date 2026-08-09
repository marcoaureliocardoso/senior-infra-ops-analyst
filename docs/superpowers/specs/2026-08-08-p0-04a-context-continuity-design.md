# P0-04A Context Continuity and Preventive Compaction Design
## Goal
Prevent long Claude Code sessions from exceeding their effective context window
or losing the current objective, decisions, evidence, authorization state,
operational state, and next actions across context compaction.
## Scope
This change covers the Nori-distributed skillset, Claude Code runtime capability
detection, compact instructions, native task-list guidance, an opt-in local
continuity configurator, a compact status line, non-blocking compaction hooks,
credential-authorization invalidation, context-budget measurement, installed
artifact validation, and live validation through the operator-configured
DeepSeek provider.
P0-04B browser automation is out of scope. This design defines only the generic
context and tool-discovery interfaces that a future browser implementation must
respect. It does not add browser MCPs, browser credentials, or browser actions.
The design does not pin Claude Code, Nori, DeepSeek, a gateway, a provider, a
model, or an absolute context-window size.
## Established Runtime Facts
The implementation is capability-based and must verify these facts against the
installed runtime instead of treating a version number as the contract:
- Claude Code auto-compaction is enabled by default and can be disabled by
  `autoCompactEnabled`, `DISABLE_AUTO_COMPACT`, or `DISABLE_COMPACT`.
- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` accepts a percentage and applies to main
  sessions and subagents. It cannot force compaction later than Claude Code's
  own limit.
- `CLAUDE_CODE_AUTO_COMPACT_WINDOW` is an absolute-window override. It is not a
  normal tuning control and is reserved for demonstrated provider or gateway
  window misreporting.
- Compact Instructions in `CLAUDE.md` are re-injected after compaction.
- Claude Code's native task list survives context compaction. Interactive
  runtimes may expose `TaskCreate`, `TaskGet`, `TaskList`, and `TaskUpdate`;
  non-interactive or SDK surfaces may expose `TodoWrite` instead.
- Status-line context percentages may be unavailable early in a session or
  immediately after compaction.
- `PreCompact` may block when a hook exits `2`; `PostCompact` cannot block.
  Asynchronous hooks are non-blocking but can race subsequent work.
- Invoked skill bodies are re-injected after compaction subject to runtime
  limits, so preloaded skill volume is an active context cost.
- MCP tool search is capability-dependent and can be unavailable by default
  behind a non-first-party `ANTHROPIC_BASE_URL`.
Official references:
- https://code.claude.com/docs/en/context-window
- https://code.claude.com/docs/en/how-claude-code-works
- https://code.claude.com/docs/en/env-vars
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/interactive-mode
- https://code.claude.com/docs/en/checkpointing
- https://code.claude.com/docs/en/statusline
- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/mcp
- https://code.claude.com/docs/en/llm-gateway
- https://code.claude.com/docs/en/sessions
- https://code.claude.com/docs/en/tools-reference
- https://api-docs.deepseek.com/quick_start/pricing
## Nori Distribution Boundary
Current Nori source shows four different ownership semantics that this design
must not blur:
1. Nori translates `AGENTS.md` into a managed block in `.claude/CLAUDE.md` and
   preserves operator content outside that block.
2. The Nori hook loader merges managed hooks with existing user hooks.
3. The status-line loader owns a scalar `statusLine` setting when enabled and
   can replace an existing value.
4. The settings backup is one-time and whole-file restoration can discard
   preferences added after the backup.
The skillset package format does not distribute arbitrary user settings or
global environment variables. P0-04A therefore cannot safely obtain complete
behavior by committing a replacement `settings.json` or by relying on Nori's
whole-file rollback.
Relevant Nori source:
- https://github.com/tilework-tech/nori-skillsets/blob/main/src/cli/features/shared/instructionsLoader.ts
- https://github.com/tilework-tech/nori-skillsets/blob/main/src/cli/features/claude-code/hooks/loader.ts
- https://github.com/tilework-tech/nori-skillsets/blob/main/src/cli/features/claude-code/statusline/loader.ts
- https://github.com/tilework-tech/nori-skillsets/blob/main/src/cli/features/claude-code/settingsBackup.ts
## Baseline Context Inventory
The static baseline measured during design is evidence, not a compatibility
limit:
| Surface | Observed inventory |
|---|---|
| Root `AGENTS.md` | 13,013 bytes, 208 lines |
| Skill bodies | 24 files, 65,942 bytes |
| Skill descriptions | 4,152 bytes |
| Subagent definitions | 12 files, 104,429 bytes |
| Per-subagent lower bound | 27,134 to 37,401 bytes for root instructions, definition, and preloaded skills |
| Package-provided MCP servers | none |

Runtime evidence must add actual context percentages and feature availability.
Byte counts remain useful for regressions but must never be converted into an
assumed token or context-window size.

## Decision
Use a hybrid architecture:
1. Durable, short instructions distributed through the existing Nori-managed
   `AGENTS.md` to preserve semantics across compaction.
2. An explicit, idempotent configurator that merges only P0-04A-owned local
   settings and exposes `--check`, `--apply`, and `--remove-owned` operations.
3. Stateless native status-line rendering as an explicit opt-in.
4. Synchronous, always-successful compaction hooks whose behavior is
   semantically non-blocking and whose retained state contains no conversation
   content or secret.
5. Capability probes and numeric-only measurement for skills, subagents, MCPs,
   and tool search.
6. Deterministic and live tests, including a real auto-compaction path through
   the operator-configured DeepSeek provider.
## Compact Instructions
Add one compact section near the existing authorization and continuity rules in
root `AGENTS.md`. It must direct Claude Code to preserve only the minimum
operational ledger needed to resume correctly:
- current objective, completion criteria, and scope exclusions;
- approved decisions, rejected alternatives, and unresolved operator choices;
- evidence already obtained and the commands or artifacts that produced it;
- authorization status, including anything invalidated by compaction;
- branch, worktree, commits, modified files, test results, and current runtime
  state;
- native task-list state, blockers, immediate next action, residual risks, and
  rollback or validation still required.
The instructions explicitly prohibit retaining transcript excerpts, raw
prompts, secret values, credential material, or a claim of authorization that
cannot be proven again after compaction. They must be brief enough that their
reinjection cost does not defeat their purpose.
## Native Task List
Long work must use the native task list as the durable execution spine. The
instructions describe semantic operations rather than one fixed tool name:
create bounded tasks, keep exactly one active task where the runtime supports
that state, update evidence as work progresses, and read the list immediately
after compaction.
The implementation detects `TaskCreate`/`TaskGet`/`TaskList`/`TaskUpdate` or
`TodoWrite` at runtime. Missing task tools are reported as a capability gap and
fall back to the compact operational ledger; they do not cause the package to
claim that persistence was tested.
## Continuity Configurator
Add a package script that discovers the repository root and Claude Code
capabilities without reading or enumerating credentials. It supports:
- `--check`: read-only report of owned settings, conflicts, capability results,
  and required operator action;
- `--apply`: merge approved P0-04A-owned keys into the selected settings scope;
- `--remove-owned`: remove only values whose ownership and current value can be
  proven from P0-04A metadata.
The default scope is the repository's `.claude/settings.local.json`, which is
personal, local, and not distributed. A user-wide scope requires an explicit
scope argument. The script never replaces an entire settings file, never
silently edits environment variables outside the selected settings object, and
never uses Nori's whole-file restore as its rollback.
Invalid or duplicate-key JSON aborts before any write. Writes are atomic and
preserve unrelated operator keys. Ownership metadata is bounded and contains
only setting names, normalized non-secret values, and a schema identifier.
`--remove-owned` refuses to remove a value changed after installation and
reports the conflict.
## Auto-Compaction Policy
The approved production default is `72`, expressed through
`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`. It lies inside the required 70-75 percent
range and remains configurable.
The configurator follows these rules:
1. If the operator already selected a value from 70 through 75, preserve it.
2. If no value exists, `--apply` writes `72` to the selected local settings
   environment map.
3. A value outside 70 through 75 is a reported conflict and requires explicit
   operator resolution; it is never silently replaced.
4. Any effective auto-compaction disablement is a blocker.
5. `CLAUDE_CODE_AUTO_COMPACT_WINDOW` is never set by normal `--apply`.
6. An absolute override may be proposed only by a separate diagnostic after a
   controlled probe demonstrates that the provider or gateway reports an
   incorrect effective context window. The diagnostic records observed numeric
   metadata and operator approval, not provider credentials.
The live auto-compaction test may use a lower, process-scoped percentage to keep
cost and duration bounded. That test value is evidence-only; production tests
separately assert that the installed default remains `72`.
## Status Line
Provide a stateless renderer using only documented status-line JSON fields. It
shows the current context percentage when available and a neutral unavailable
state when usage is null or missing. It writes no files, calls no network, and
does not calculate token usage from transcript content.
Status-line installation is opt-in. `--apply` does not replace an effective
operator or Nori status line. The explicit status-line flag installs the
package renderer only when no inherited status line exists; otherwise it
reports a conflict and makes no change. Package-owned installation is tracked
for exact removal, while a changed or unowned status line is preserved during
`--remove-owned`.
## Compaction Hooks
Add `PreCompact` and `PostCompact` handlers with strict bounded input schemas.
Both handlers:
- ignore `transcript_path`, `custom_instructions`, `compact_summary`, prompt
  text, content fields, and unknown textual payloads;
- never persist a transcript, prompt, compact summary, raw event, model output,
  command, secret, or credential-derived value;
- retain at most bounded non-secret session identity, hook phase, timestamp,
  schema version, and authorization-invalidation status;
- produce no model-visible conversation content on success;
- always exit `0`, including malformed input, timeout, storage failure, or
  internal error, so compaction is never blocked.
The `PreCompact` handler is synchronous and narrowly bounded. It may await the
atomic invalidation of non-secret credential-binding metadata, but it may not
return a blocking native decision or exit `2`. `PostCompact` verifies or
retries the invalidation and emits only a concise operator warning when it
cannot establish the safe state. An asynchronous notification may supplement
this check but cannot be the only invalidation mechanism.
The local configurator installs the main-session hooks by merging them into the
selected settings scope. Subagent definitions receive package-relative hook
references so Nori distributes the same invariant. Handlers are idempotent and
use event scope to prevent duplicate main/settings and subagent/frontmatter
delivery from changing semantics.
## Authorization Invalidation
Compaction invalidates any authorization or credential reuse that cannot be
proved again from current native state. In particular, P0-04's bounded
literal-credential binding must not remain reusable solely because Claude Code
kept the same session identifier.
`PreCompact` atomically removes or tombstones all pending and active bindings
for the affected session without reading, reconstructing, or storing a secret.
After compaction, the next literal credential use must return native `ask` and
can become reusable only after the existing matching successful
`PostToolUse` flow. Changed mode, missing proof, hook uncertainty, or malformed
continuity state also requires fresh approval.
Tests must prove that state files contain no credential, raw command, prompt,
transcript path, or secret-derived hash. If invalidation cannot be verified,
the system reports degraded continuity and the command guard fails closed for
reuse until a fresh approval establishes a new binding.
## Context Measurement
Add a numeric-only evidence collector that measures each dimension separately:
- root instructions;
- each subagent definition;
- each preloaded and invoked skill body;
- runtime context percentage before and after loading a skill;
- runtime context percentage before and after invoking a subagent;
- connected MCP tool descriptions and schemas when observable;
- tool-search availability and change in visible tool inventory.
The collector records counts, bytes, percentages, feature booleans, reason
codes, and observed non-secret runtime identifiers. It does not store prompts,
responses, summaries, transcripts, tool arguments, tool results, environment
values, headers, or credentials.
MCP and tool-search probes are capability-based. The package does not force
tool search through the DeepSeek gateway. When native tool search is available,
the live test measures it. When it is unavailable, the live evidence records
that branch and a deterministic fixture proves the opposite branch without
misrepresenting it as a live result.
## Large Output and Context Thrash
Instructions and validation cover bounded recovery from context pressure:
- inspect `/context` before loading broad capabilities;
- use focused skills and subagents instead of broad simultaneous preload;
- read large artifacts in bounded chunks and retain only evidence references;
- use focused `/compact` instructions when the default compact summary would
  omit a critical invariant;
- use `/rewind`, `/clear`, and `/resume` only with explicit awareness of which
  context or authorization state is lost;
- disconnect or scope unused MCP servers, including future browser MCPs.
These are operational recovery controls, not substitutes for the automatic
72-percent threshold.
## Alternatives Rejected
### Instructions only
This preserves intent but cannot configure a threshold, display context state,
or invalidate persisted credential bindings deterministically.
### Checked-in replacement settings
This is automatic but can overwrite operator preferences, conflicts with
settings precedence, and does not provide safe per-key rollback.
### Nori status line and whole-file backup as the sole owner
This uses native integration but scalar replacement and whole-file restoration
cannot prove preservation of preferences added after installation.
### Absolute context-window configuration by default
This encodes a provider/window assumption and can hide rather than diagnose a
gateway reporting error.
### Blocking `PreCompact`
This can preserve a stale session indefinitely and violates the requirement
that compaction hooks remain non-blocking.
### Persisting a compact summary or checkpoint
This creates a second transcript-like artifact and expands secret and personal
data exposure.
## Test Strategy
Implementation follows TDD with the following layers.
### Unit and contract tests
- settings merge, precedence, atomic write, invalid JSON, duplicate keys,
  ownership conflict, idempotence, default `72`, preservation of 70-75,
  disablement blocker, and owned-only rollback;
- proof that normal configuration never sets
  `CLAUDE_CODE_AUTO_COMPACT_WINDOW`;
- status-line valid, null, missing, malformed, and forward-compatible fields,
  plus proof of no file or network effects;
- hook size, depth, timeout, malformed input, sensitive-field rejection,
  always-zero exit behavior, idempotence, concurrency, and bounded state;
- credential binding invalidation before compaction and mandatory fresh
  approval afterward;
- static and runtime context inventory with forbidden-content scans;
- every subagent's task-tool and compaction-hook contract.
### Installed Nori tests
- fresh install into a generated home;
- semantic comparison of installed root instructions, agents, skills, scripts,
  and hooks;
- preservation of pre-existing operator settings and hooks;
- switch and rollback with preferences added after install;
- refusal on malformed configuration without partial writes.
### Live DeepSeek validation
Use a generated home and the existing explicitly acknowledged normal-provider
credential exception. Never print, copy, persist, or include credentials in
evidence. Validate:
1. `/context` for the main session and all 12 subagents with numeric-only
   retained metadata.
2. Native task-list survival across manual and automatic compaction.
3. Manual focused and unfocused compaction.
4. Real auto-compaction using a lower process-scoped test percentage while the
   installed production default remains `72`.
5. Credential-binding invalidation and fresh native approval after compaction.
6. `/resume`, `/rewind`, large output, repeated skill use, and context-thrash
   recovery.
7. Skill, subagent, MCP, and tool-search context impact.
8. Actual tool-search capability on the configured DeepSeek route, with the
   unavailable branch recorded honestly when unsupported.
9. Effective-window reporting on the real route and a disposable mock-gateway
   divergence case. Set an absolute override only in the divergent test after
   the mismatch is observed.
### Release validation
Run the complete package gate on supported local environments, independent
review, GitHub CI, and security checks. Version, changelog, README, operational
references, and ADR evidence are updated when implementation behavior becomes
real.
## Security and Privacy Invariants
- No hook or evidence file contains transcript text, summary text, prompt text,
  model output, tool input/output, secret, credential, header, or raw command.
- No secret-derived hash, fingerprint, or identifier is introduced.
- Settings inspection reads only named owned controls and does not enumerate or
  report environment values.
- A failed continuity control cannot authorize execution or credential reuse.
- Compaction itself is never blocked by this package.
- Runtime identifiers and numeric context observations are evidence, not
  compatibility requirements.
## Acceptance Criteria
P0-04A is ready for a PR when:
1. Auto-compaction remains enabled and the installed default is configurable at
   72 percent without an absolute-window assumption.
2. Compact Instructions and native task-list guidance preserve every approved
   continuity field across demonstrated compaction.
3. Settings, hooks, and status line preserve unrelated operator preferences and
   support owned-only rollback.
4. `PreCompact` and `PostCompact` cannot block compaction and persist no
   prohibited content.
5. Credential reuse is invalidated across compaction and requires fresh native
   approval when proof is lost.
6. Context impact is measured for root instructions, all skills, all subagents,
   MCPs, and tool search without retaining content.
7. The real DeepSeek route passes the supported live scenarios and reports
   unsupported capabilities without fabricated success.
8. The correct-window route works without
   `CLAUDE_CODE_AUTO_COMPACT_WINDOW`; the divergent mock route proves the
   evidence-gated exception.
9. Unit, installed, live, package, CI, security, and independent-review gates
   pass with retained non-secret evidence.
10. Version, changelog, README, references, and ADR validation evidence match
    the implemented behavior.
11. The PR is published but not merged without explicit operator instruction.
The definitive unversioned TODO remains incomplete until implementation, real
tests, independent review, CI/security, and merge into `main` are all complete.
