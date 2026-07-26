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

Attach native `PreToolUse` and `PostToolUse` hooks with matcher `Bash` to the
eight executor subagents. Both hooks invoke a fail-closed launcher from the
installed `command-driven-operations` skill through `{{skills_dir}}`. The
launcher applies an internal deadline, checks the runtime and artifact, and
rejects crashes, malformed output, and unexpected stdout before delegating to
the validator or approval recorder.

The validator returns Claude Code's native `allow`, `ask`, or `deny` response.
Normal modes allow narrow reads and ask for bounded sensitive reads and
catalogued changes. `bypassPermissions` allows bounded reads and catalogued
non-destructive changes. `DESTRUCTIVE` always asks. Unknown, ambiguous,
dynamic, unbounded, or prohibited calls deny. A future unknown permission mode
uses conservative normal-mode semantics rather than a version allowlist.

## Implemented architecture

1. A strict stdin contract accepts one bounded `PreToolUse`/`Bash` event for a
   registered executor. Execution-affecting fields remain closed; bounded
   scalar observational fields and future effort labels are tolerated without
   changing the decision. Duplicate security keys, nested extensions,
   excessive input, background requests, and invalid timeouts fail closed.
2. Separate bounded Bash and PowerShell lexers preserve quoting and escapes,
   recognize literal operators and redirects, and reject substitution,
   dynamic interpreters, unmatched syntax, and control characters.
3. A composition graph binds ordered stages, operators, redirects, and
   source-to-sink edges instead of blanket-blocking pipes.
4. A finite executable-specific catalogue classifies host/log reads, services,
   containers, AWS/Azure/GCP, PostgreSQL/MySQL/MongoDB/Redis, network probes,
   packet capture, HTTP, SSH/file transfer, sudo, Git/CI, PowerShell reads, and
   Windows service control. Mutations require explicit target/environment
   bindings.
5. The policy retains bounded per-stage findings, aggregates the highest risk
   and approval modifiers, then applies the permission-mode matrix. Every
   changed call is evaluated independently.
6. Parser-aware redaction precedes model-visible output. Audit uses a SHA-256
   identity derived only from the canonical non-secret action structure, never
   from raw command or credential material. Append-only records fail closed
   when they cannot be written.
7. First literal credential use returns `ask`. A matching successful
   `PostToolUse` event activates a time-bounded, owner-only record keyed by
   session, domain, identity, transport, family, and target class. The state
   stores no credential, raw command, or secret-derived hash and is bounded in
   size, lifetime, and entry count. Successful Bash calls with no matching
   pending state are silent no-ops in `PostToolUse`; malformed events or unsafe
   state still fail closed.
8. The process writes exactly one native JSON response after successful audit.
   Parsing, policy, serialization, encoding, or audit failure emits no allow
   decision and exits `2`.
9. The opt-in live harness installs the worktree through Nori into a generated
   home, imports only allowlisted Claude transport settings through a
   non-persistent FIFO, and runs non-root model processes inside Bubblewrap.
   It preserves usrmerge links, mounts only minimal read-only resolver and CA
   paths, selects `diagnostic-operator` through Claude Code's native `--agent`
   option, and targets a disposable loopback fixture that never records
   headers or bodies.

## Enforcement points

- Source validation requires the exact hook in `audit-evidence-collector`,
  `cloud-platform-operator`, `database-operator`, `diagnostic-operator`,
  `kubernetes-operator`, `network-edge-operator`, `observability-sre`, and
  `release-cicd-operator`; the four analytical roles remain hook-free and lack
  `Bash`.
- Installed-artifact validation byte-compares every security-critical launcher,
  entrypoint, and module with source and executes the same adversarial fixture
  corpus against both forms.
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

In every mode, first literal use raises the current call to `ask`. Only a
matching successful `PostToolUse` event can activate reuse. In
`bypassPermissions`, the model may then reuse the available value only in the
same session, credential domain, identity, and transport, including different
explicit catalogued targets in that domain. Every command is still
re-evaluated and destructive use still asks. Mode, session, expiry, or
model-context loss requires a new prompt.

The hook stores state about approval scope but remains stateless about secret
material. It never stores, hashes, fingerprints, derives an identifier from,
compares, or searches the transcript for credential values; therefore it
cannot prove that two literals are equal or reconstruct historical provenance.
Encrypted-file use is
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

- The remediated deterministic gate runs 87 active Node tests plus one intentionally
  skipped mutation-only fixture, four recorded property seeds, a finite
  inventory orphan check, and exact mutation-site validation.
- Critical contract, lexer, composition, credential-flow, binding-state,
  policy, redaction, response, audit, and both entrypoint modules achieve 100%
  line, function, and branch coverage with native Node test coverage.
- Eleven registered security mutations are killed, including background and
  size bounds, dynamic syntax, unknown family, target binding, destructive
  precedence, risk aggregation, unsafe credential sink, authorization
  redaction, forbidden audit fields, and fail-closed exit.
- Installed validation byte-compares the launcher, entrypoints, and all guard
  modules with source, then executes the same 21-case stable-ID adversarial
  corpus against both forms.
- Each finite grammar, shell operator, command family, reason code, limit,
  credential transport, edge case, and review regression is bound to an
  executable semantic fixture. One ledger proves every declared fixture ran
  exactly once and fails on stale, missing, duplicate, or unexecuted evidence.
- A static safety contract constrains opt-in live Claude Code/Nori probes to a
  generated home, Bubblewrap, disposable local processes, loopback targets,
  retained-output scans, and redacted evidence.
- The explicitly acknowledged remediated live run passed on Debian WSL2 with
  observed Node.js `v20.19.2`, Nori `0.27.0`, and Claude Code `2.1.218`. It
  registered all 12 subagents, 24 skills, 20 slash commands, and both hook
  phases, then passed the installed corpus and `default` plus
  `bypassPermissions` probes. The harness emitted the mandatory open-egress
  warning. These observed identifiers are evidence, not requirements.
- The complete package gate passed on host Node.js `v24.17.0`, whose native
  test runner exposes the required line, function, and branch threshold flags.
  The WSL runtime was sufficient for guard execution and live evidence but did
  not expose those coverage-gate capabilities; capability probing, rather than
  a version allowlist, determined which runtime executed that development gate.

## Accepted live-smoke exception

The operator approved temporary use of normal provider credentials for the
opt-in live smoke. The harness requires
`P0_04_LIVE_NORMAL_CREDENTIALS_ACK=I_ACCEPT_PROVIDER_CREDENTIAL_EGRESS_RISK`
before loading settings or credentials, warns that credentials enter the
Claude process, and reports that provider egress remains open. A generated
home, Bubblewrap mounts, provider-control-variable command denials,
loopback-only operational targets, and retained-output scans reduce but do not
eliminate exfiltration risk. Disposable provider credentials or provider-egress
allowlisting remain the preferred replacement.

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
