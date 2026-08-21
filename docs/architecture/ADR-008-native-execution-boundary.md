# ADR-008 — Native execution boundary

- **Status:** Accepted
- **Date:** 2026-08-21
- **Scope:** Native command routing for the main Claude Code session and protected executor subagents

## Context

The executor subagents already carried deterministic native `PreToolUse` and
`PostToolUse` command guards, but the main session had no equivalent proven
boundary. Claude Code permission modes, including `bypassPermissions`, are not
evidence that those hooks are installed or firing. Direct execution based only
on settings presence could therefore bypass the package's command catalogue,
risk classification, redaction, and approval semantics.

## Decision

Adopt `references/native-execution-boundary.md` as the canonical routing
contract. Main-session hooks are an explicit project-local opt-in and remain
operator-owned. Exact settings establish only `CONFIGURED_UNPROVEN`. The
current session becomes eligible for direct operational Bash only after its
exact harmless probe `printf P005_GUARD_PROBE` produces a fresh structured
`PreToolUse` denial with reason `DENY_UNKNOWN_COMMAND` through the configured
guard. The probe proves coverage only; it authorizes no later command.

Every later Bash call is independently classified and authorized. If current
main-session coverage is not proven, route to a matching installed executor
whose native hooks are present. If neither route is proven, perform no
execution. Native typed tools remain governed by their own typed contracts and
do not become shell escape hatches.

## Routing matrix

The canonical matrix has four outcomes:

- `PROTECTED_BASH`: use direct Bash only with ephemeral `ACTIVE` proof.
- `PROTECTED_EXECUTOR`: delegate to a role with installed native Bash hooks.
- `TYPED_TOOL`: use the typed tool contract without converting it into Bash.
- `NO_EXECUTION`: report the limitation, unexecuted proposal, required operator
  action, and validation steps.

The configuration inspection states are `ACTIVE`, `CONFIGURED_UNPROVEN`,
`ABSENT`, `CONFLICT`, and `UNSUPPORTED`. Any inability to re-establish the
current-session proof removes direct Bash autonomy.

## Operator ownership

Nori installation does not modify project settings. The installed
`command-driven-operations` component exposes `--check`, `--apply`, and
`--remove-owned`. It merges exact package hook groups into
`.claude/settings.local.json`, records only package-owned entries, uses a
bounded lock and settings-first transaction, recovers interrupted writes, and
never restores or replaces the whole operator file. Conflicting or drifted
entries fail closed.

The lock and raw-byte recheck reject cooperative races and any changed target
observed before replacement. Node's cross-platform filesystem API does not
offer a handle-anchored compare-and-swap rename, so this configurator is not a
security boundary against a malicious same-principal local actor that can
replace a checked ancestor or target between syscalls. Such an actor can also
edit the settings immediately after the operation. Where that actor is in the
threat model, do not run `--apply`; use managed settings or an operator-reviewed
manual change protected by operating-system access controls.

No prompt, transcript, raw command, credential, provider value, or terminal
capture is stored by the configurator or public evidence document.

## Runtime proof

Configuration presence is not Runtime proof. An ephemeral proof is valid only
for the observed session, runtime identity, permission mode, effective settings
and hooks, policy, and installed paths. Resume, clear, compaction, session or
mode change, runtime replacement, settings drift, hook drift, or loss of
identity requires revalidation.

The bounded PTY observer ignores terminal text and accepts exactly one fresh
content-free audit record in a nonce-specific path for each stage. The expected
nonce value emitted by the guard must exactly match the random value carried
only in the launched child environment. Echoed text,
suffix matches, stale sessions, missing, repeated, orphaned, reordered,
malformed, oversized, and timed-out evidence cannot establish `ACTIVE`.

Both hook phases must be exact in effective settings, but the deliberately
denied probe cannot invoke `PostToolUse`. Its observed `PreToolUse` denial proves
the authorization boundary needed before direct Bash. A later successful call
must independently reach the configured `PostToolUse` hook before credential
reuse can activate; missing Post evidence remains a silent no-op and grants no
reuse.

## Alternatives rejected

- Treating `bypassPermissions` as guard proof: permission mode and hook
  coverage are independent properties.
- Treating exact settings as runtime proof: configured hooks may be disabled,
  superseded, unsupported, or not invoked by the current runtime.
- Sending a separate probe as authorization for a later call: authorization is
  per call, while the probe establishes coverage only.
- Persisting transcript or terminal content for proof: it expands secret and
  operator-data exposure and permits echo-based false positives.
- Automatically editing operator settings during Nori installation: it violates
  local ownership and safe rollback.
- Falling through to unprotected main-session Bash: absence of evidence is not
  evidence of coverage.

## Validation evidence

The source routing contract, configuration state machine, exact ownership,
transaction recovery, concurrency, installed artifact, and safety suites pass.
An isolated Nori self-test proves that the installed package includes the
configurator and settings module, preserves operator settings, applies
idempotently, removes only owned hooks, and uses installed rather than source
paths.

The no-provider live-routing self-test on 2026-08-21 observed the exact ordered
synthetic sequence `main-default`, `main-bypass`, and `executor-fallback`, each
as one `PreToolUse` denial with `DENY_UNKNOWN_COMMAND`. It also proves hook
removal before fallback, bounded PTY output, nonce-specific audits, exact
sequence comparison, filesystem cleanup, Bubblewrap requirements for the real
route, and an allowlisted child environment whose values do not enter argv.

Provider-backed Claude Code validation has not been run for this head because
it requires a separate explicit operator acknowledgement. The deterministic
self-test is not represented as direct live main-session or executor proof.

## Consequences and residual risks

Direct main-session automation is deliberately unavailable when the state is
not `ACTIVE`; delegation or no execution is the expected result. The harmless
probe consumes a provider turn on the real route and may remain inconclusive if
the model does not request the exact Bash call or if current Claude Code does
not surface the expected hook contract. Timeout remains `INCONCLUSIVE`, never
success.

The real harness keeps provider egress because Claude Code must reach its
configured provider. Bubblewrap limits filesystem visibility to runtime files,
minimal DNS/TLS data, and the disposable work tree, but cannot reduce provider
disclosure below the content sent to the configured model. Operator credentials
remain a separately acknowledged runtime input and are never retained as
evidence.

## Follow-ups

P0-04B remains responsible for browser automation and its context impact.
P3-16 remains responsible for any broader catalog of typed-tool execution
boundaries. Neither follow-up weakens this fail-closed Bash routing decision.
A provider-backed run and independent final-head review remain acceptance gates
before P0-05 can be marked complete.
