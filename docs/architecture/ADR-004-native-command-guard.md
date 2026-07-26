# ADR-004: Native executor command guard

- Status: Accepted
- Date: 2026-07-26
- Scope: P0-04 command authorization for executor subagents

## Context

P0-01 gave the model one operational risk taxonomy, P0-02 preloaded focused
skills, and P0-03 bounded each subagent's tools and turns. Those controls still
depended on the LLM classifying a proposed shell call correctly. The eight
evidence-collecting roles require `Bash` to work as operational executors, and
`bypassPermissions` must provide useful autonomy without making destructive,
ambiguous, or credential-exfiltrating calls autonomous.

The solution must run inside standard Claude Code agent mechanics and the
Nori-installed skillset. It must not introduce a model proxy, daemon, custom
DeepSeek API parser, or fixed Claude Code, Nori, Node.js, or model version.

## Decision

Attach a native `PreToolUse` hook with matcher `Bash` to the eight executor
subagents. The hook invokes a shared deterministic Node.js validator from the
installed `command-driven-operations` skill through `{{skills_dir}}`.

The validator returns Claude Code's native `allow`, `ask`, or `deny` response.
Normal modes allow narrow reads and ask for bounded sensitive reads and
catalogued changes. `bypassPermissions` allows bounded reads and catalogued
non-destructive changes. `DESTRUCTIVE` always asks. Unknown, ambiguous,
dynamic, unbounded, or prohibited calls deny. A future unknown permission mode
uses conservative normal-mode semantics rather than a version allowlist.

## Implemented architecture

1. A strict stdin contract accepts one bounded `PreToolUse`/`Bash` event for a
   registered executor, including the documented common hook fields and Bash
   description, while rejecting duplicate security keys, unexpected fields,
   excessive nesting, background requests, and invalid timeouts.
2. Separate bounded Bash and PowerShell lexers preserve quoting and escapes,
   recognize literal operators and redirects, and reject substitution,
   dynamic interpreters, unmatched syntax, and control characters.
3. A composition graph binds ordered stages, operators, redirects, and
   source-to-sink edges instead of blanket-blocking pipes.
4. A finite catalogue classifies host/log reads, services, Kubernetes,
   containers, AWS/Azure/GCP, PostgreSQL/MySQL/MongoDB/Redis, network probes,
   packet capture, HTTP, SSH/file transfer, sudo, Git/CI, PowerShell reads, and
   Windows service control. Mutations require explicit target/environment
   bindings.
5. The policy aggregates the highest risk and approval modifiers, then applies
   the permission-mode matrix. Every changed call is evaluated independently.
6. Redaction precedes normalization and SHA-256 fingerprinting. Append-only
   audit records contain only bounded non-secret metadata and fail closed when
   they cannot be written.
7. The process writes exactly one native JSON response after successful audit.
   Parsing, policy, serialization, encoding, or audit failure emits no allow
   decision and exits `2`.

## Enforcement points

- Source validation requires the exact hook in `audit-evidence-collector`,
  `cloud-platform-operator`, `database-operator`, `diagnostic-operator`,
  `kubernetes-operator`, `network-edge-operator`, `observability-sre`, and
  `release-cicd-operator`; the four analytical roles remain hook-free and lack
  `Bash`.
- Installed-artifact validation resolves the validator under the installed
  skills root and compares source and Nori-installed hook semantics.
- The deterministic guard validates the current tool call. Model-facing
  instructions preserve session/context rules the hook cannot observe.
- Claude Code remains responsible for displaying and resolving native `ask`.
  A `deny` includes `systemMessage` for direct operator visibility and a
  redacted reason for safe model reformulation.
- Package validation runs command-guard tests before schema and release gates.

## Credential handling

Provider profiles, cached sessions, agents, askpass, keychains, credential
helpers, runtime variables, and protected files are preferred. A literal
credential supplied in conversation is classified as
`MODEL_VISIBLE_LITERAL`: it is already visible to the model, provider, and
Claude Code transcript, so the guard promises only to prevent additional
output, audit, persistence, or unsafe-flow disclosure.

In normal modes, a detected literal raises the current call to at least
`ask`. In `bypassPermissions`, the model may reuse the available value only in
the same session, credential domain, identity, and transport, including
different explicit catalogued targets in that domain. Every command is still
re-evaluated and destructive use still asks. Mode, session, or model-context
loss requires a new prompt.

The hook is intentionally stateless about secret material. It never stores,
hashes, fingerprints, derives an identifier from, compares, or searches the
transcript for credential values; therefore it cannot prove that two literals
are equal or reconstruct historical provenance. Encrypted-file use is
authorizable only through a direct catalogued decryptor-to-consumer stdin flow.
Display, logs, generic files, background jobs, unrelated consumers, and
ambiguous destinations deny.

## Alternatives rejected

- Blocking every pipe: rejected because bounded read pipelines and direct
  credential flows are legitimate operational primitives.
- Requiring approval for every change in `bypassPermissions`: rejected because
  it defeats the operator's deliberate permissive-session intent.
- Treating every unsafe condition as `deny`: rejected because a fully analyzed
  authorizable action belongs in native `ask`.
- Regex or LLM-only command authorization: rejected because substrings do not
  establish shell structure, target binding, aggregate risk, or data flow.
- Persisting a credential fingerprint for reuse: rejected because secret-
  derived state would expand exposure and still would not prove conversational
  provenance.
- A daemon, model proxy, custom API wrapper, or companion runtime: rejected
  because native agent hooks are sufficient for this enforcement point.
- Pinning runtime or model versions: rejected in favor of capability probes,
  semantic installed validation, and recorded observed evidence.

## Validation evidence

- The deterministic gate runs 61 active Node tests plus one intentionally
  skipped mutation-only fixture, four recorded property seeds, a finite
  inventory orphan check, and exact mutation-site validation.
- Critical contract, lexer, composition, credential-flow, policy, redaction,
  response, audit, and entrypoint modules achieve 100% line, function, and
  branch coverage with native Node test coverage.
- Eleven registered security mutations are killed, including background and
  size bounds, dynamic syntax, unknown family, target binding, destructive
  precedence, risk aggregation, unsafe credential sink, authorization
  redaction, forbidden audit fields, and fail-closed exit.
- The installed-form self-test validates both agents and skills roots and
  probes normal, bypass, destructive, unknown, Bash pipeline, PowerShell
  pipeline, credential, malformed-input, and audit-failure behavior using
  synthetic data.
- A static safety contract constrains opt-in live Claude Code/Nori probes to a
  generated home, Bubblewrap, disposable local processes, loopback targets,
  synthetic credentials, and redacted retained evidence.
- A real live P0-04 model probe was not produced on the implementation host
  because WSL has no installed Linux distribution with Bubblewrap. The live
  harness remains opt-in and reports this as unavailable, never as passed.

## Consequences and limitations

Executor shell autonomy is now bounded by deterministic current-call policy;
auditing failure also prevents execution. The catalogue and shell grammar are
deliberately finite, so a legitimate but unmodelled command denies until a
versioned policy and adversarial tests add it. This favors explicit safe
extension over permissive guessing.

The hook is executor-scoped. If the main Claude Code session can invoke
`Bash` directly and the installed artifact exposes no supported global hook
path, that direct main-session call remains outside this guard. P0-05 must keep
the native-shell boundary explicit and require typed operational tools where
shell semantics cannot provide adequate transactional, multi-target,
idempotency, or rollback guarantees.

The validator cannot prove operator provenance, secret equality, interactive
prompt completion, or future model adherence after context loss. Native
Claude Code permission handling, model-facing invariants, installed behavioral
tests, and operator practice remain separate enforcement layers.

## Forward compatibility

Runtime selection stays inherited and versions remain observations. Hook
installation is validated semantically, the validator uses the effective
`permission_mode`, and unknown future modes fall back conservatively without
blocking solely because their names are new. Catalogue, reason-code, limit,
grammar, credential-transport, and security-predicate inventories are
versioned; orphan and mutation gates require every extension to add matching
positive, boundary, negative, and adversarial evidence.
