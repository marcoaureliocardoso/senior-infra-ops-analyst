# P0-04 Review Remediation Design

**Status:** Approved architecture; implementation pending

**Date:** 2026-07-26

**Scope:** Remediate all blocking findings from the independent review of PR
`#25` without weakening the executor role

## Context and decision

P0-04 must keep the eight executor subagents operational while enforcing every
native Claude Code `Bash` request deterministically. Independent review found
that the first implementation can lose command structure, underestimate side
effects, reuse literal credentials without trusted approval state, and claim
test coverage that is not bound to executable fixtures.

The approved architecture keeps native hooks and the strict command catalogue.
It adds a fail-closed launcher, complete wrapper consumption, command-specific
argument schemas, approval-derived non-secret credential bindings, executable
coverage evidence, and source-to-installed equivalence checks.

The operator approved one explicit temporary exception: the opt-in live smoke
continues to import normal Claude provider credentials. The design documents
that risk and adds compensating controls; it does not label the exposure as
resolved.

## Security invariants

The remediation must preserve these invariants:

1. A command can execute only when its entire outer and inner composition has
   been consumed by a supported parser.
2. Unknown syntax, executables, options, execution-control variables, stages,
   sinks, or data-flow edges never produce `allow`.
3. `bypassPermissions` can authorize catalogued operational work, but cannot
   override an unproved command, secret disclosure, or an external or
   destructive effect that requires an exact operator decision.
4. Literal credential reuse requires a previously approved, non-secret
   session binding. The guard stores no secret, secret hash, secret-derived
   fingerprint, raw credential-bearing command, or transcript content.
5. Every source decision is reproducible against the installed artifact from
   the same executable fixture.
6. A launch, runtime, timeout, serialization, or audit failure blocks the tool
   call.
7. Explanations remain detailed enough for the operator to act, but contain no
   raw secret.

## Hook and launcher architecture

Executor frontmatter continues to use native Claude Code hooks. `PreToolUse`
for `Bash` invokes a small Bash launcher rather than invoking Node.js directly.
Bash is already a functional prerequisite for these executor roles; no new
runtime is introduced.

The launcher:

- resolves its own installed directory without a mutable search path;
- validates the configured Node.js executable and validator file;
- starts the validator with a deadline shorter than the outer native hook
  timeout;
- forwards exactly one validator JSON response and no diagnostic noise on a
  successful decision path;
- emits a bounded generic failure explanation to stderr and exits `2` for a
  missing runtime or artifact, an internal deadline, a validator crash,
  malformed or polluted output, or an unexpected exit;
- never executes or evaluates the proposed command.

The native hook timeout remains a final outer bound. Because native hook
infrastructure can fail outside project code, the package can prove only the
failure paths it controls. An environment that cannot start Bash cannot use
these Bash executor roles and fails the installed readiness check.

`PostToolUse` records successful approval evidence for credential reuse. It is
called only for the same `Bash` tool use and never authorizes another command.
`PostToolUseFailure` does not activate a reusable binding: a failed operation
does not establish successful authentication or a validated consumer path.

## Complete command parsing

### Outer composition and wrappers

The analyzer tokenizes the complete outer Bash-compatible command before any
wrapper is interpreted. A PowerShell wrapper is accepted only when:

- the outer command contains exactly one foreground stage;
- no outer operator, redirection, environment prefix, or trailing argument is
  left unconsumed;
- the wrapper contains exactly one supported command payload;
- wrapper options are recognized case-insensitively with explicit arity;
- encoded commands, stop-parsing tokens, profile loading, dynamic files, and
  ambiguous option abbreviations are rejected.

The inner PowerShell parser then consumes the complete payload with its own
grammar. The same full-consumption rule applies to every future wrapper.

### Environment assignments

Generic `NAME=value` skipping is removed. A bounded assignment schema permits
only variables explicitly required by a command-family policy, including safe
profile references and the non-secret `OPS_CREDENTIAL_IDENTITY` selector.

The guard denies all unknown assignment prefixes and every variable capable of
changing executable resolution, dynamic loading, shell startup, configuration
injection, pagers, editors, Git hooks or helpers, language runtimes, or plugin
discovery. The denied set includes families such as `PATH`, `LD_*`, `DYLD_*`,
`BASH_ENV`, `ENV`, `SHELLOPTS`, `GIT_EXTERNAL_DIFF`, `GIT_CONFIG_*`, pager and
editor variables, and runtime module search paths. Command schemas may add a
specific variable only with positive, boundary, misuse, and control-variable
regressions.

### Executable-specific argument schemas

Every command family receives an argument parser that declares:

- supported verbs and option aliases;
- option arity and repeatability;
- positional argument roles;
- target, environment, scope, and identity derivation;
- effective reads, writes, mutations, network effects, and local sinks;
- sensitive outputs and credential-bearing inputs;
- destructive and externally persisted variants;
- bounded unknown-option behavior.

Unknown options fail closed instead of inheriting a family-level read label.
Generic `SAFE_READ_ONLY` classifications are removed where an executable has a
mutating flag or can reveal secrets.

HTTP clients derive the effective method from explicit methods and implicit
body or upload options. They record request body, upload, redirect,
authentication, response-output, remote-header, and local-file sinks.
PowerShell web clients receive equivalent case-insensitive schemas, including
`-Body`, `-Form`, `-InFile`, `-Method`, `-OutFile`, and redirect behavior.

Git push parsing identifies force, mirror, prune, delete, wildcard, and
deletion or forced refspec variants. SQL authorization changes from keyword
blacklisting to a narrow single-statement read grammar. Unknown functions,
side-effecting functions, multiple statements, procedural constructs, file
access, locks, and administrative clauses are not safe reads.

Sensitive operational reads are separately classified. Direct secret output,
environment-bearing process output, unrestricted inspect output, credential
store reads, and mutating diagnostic flags never inherit narrow read-only
authorization. A protected secret source is accepted only when its output is
consumed directly by the validated credential flow described below.

## Composition and aggregate policy

The composition graph retains every stage, operator, redirect, source, and
sink. A protected decryptor flow has exactly two stages and exactly one
immediate `|` edge. Sequence, conditional, `|&`, display, file, logging,
background, or additional-consumer edges are rejected.

The result contains bounded redacted findings for every policy-relevant stage
and edge, including equal-risk findings. The aggregate decision applies the
most restrictive rule, while its explanation identifies all contributing
stages without reproducing a credential-bearing raw command.

Policy modifiers are explicit:

| Modifier | Normal modes | `bypassPermissions` |
|---|---|---|
| Narrow safe read | `allow` | `allow` |
| Bounded sensitive, active, or privileged read | `ask` | schema-dependent `allow` or `ask` |
| Low-risk or disruptive internal change | `ask` | `allow` |
| Destructive effect | `ask` | `ask` |
| External side effect | `ask` | `ask` |
| Secret disclosure, ambiguous, or unmodelled | `deny` | `deny` |

Creating or changing a GitHub comment, issue, release, deployment, or other
externally persisted record uses `EXTERNAL_SIDE_EFFECT`, even if the underlying
CLI verb is otherwise low risk.

## Credential binding and reuse

### First literal use

A parser-recognized literal credential always returns `ask` unless it is part
of a forbidden flow, which returns `deny`. This remains true in
`bypassPermissions`. The reason explains that the value is already model
visible and asks approval for the exact parsed domain, identity, transport,
target class, and operation.

Identity must be non-secret and explicit. It is derived from a reviewed
username, profile, URI principal, or the bounded
`OPS_CREDENTIAL_IDENTITY=<identifier>` assignment. An opaque bearer token with
no explicit non-secret identity can be approved for the current command but
does not become reusable.

### Approval evidence

Before returning `ask`, `PreToolUse` writes a bounded pending record keyed by
the native session and tool-use identifiers. It contains only:

- session and tool-use identifiers;
- domain or origin;
- non-secret identity;
- credential transport;
- command family and target class;
- expiration and one-time pending state.

It contains no command text or secret-derived value. An atomic, owner-only
state file is stored beneath the Claude session's project-local state path.
File names and fields are length-bounded, entries expire, and the store has a
fixed maximum count.

A matching successful `PostToolUse` consumes the pending record and activates
the domain, identity, and transport binding for the current session. A denial,
missing post event, tool failure, identifier mismatch, expired record, state
corruption, mode change, or new session does not activate or reuse it.

### Subsequent use

A later literal use can follow the operation's normal bypass policy only when
all of these are true:

- the effective mode is `bypassPermissions`;
- session, domain, identity, and transport exactly match an active binding;
- the destination and target class are explicit and catalogued within that
  domain;
- the current command independently passes complete parsing and data-flow
  validation;
- the operation is neither destructive nor externally persisted unless the
  policy returns `ask` for that exact call.

No secret equality is asserted or required. The binding means that the
operator approved use of a literal through that non-secret channel during the
session; it does not prove two values are equal. A changed literal with the
same binding is therefore still model-visible risk accepted by the session
authorization. Leaving bypass mode, loss of explicit binding data, or state
expiration returns to `ask`.

Provider-control-plane credential variables used to run Claude Code, including
the supported Anthropic authentication variables, are never valid command
credentials. Any proposed Bash command that references their names or attempts
general process-environment discovery is denied in every mode.

## Event compatibility boundary

Fields that can change execution remain strict. Unknown keys inside
`tool_input`, unsupported background behavior, command changes, and unknown
security fields fail closed.

Bounded unknown top-level observational metadata may be ignored and recorded
as a compatibility modifier when it cannot affect command execution. Known
fields retain strict types and bounds. Future effort labels are treated as
observational; unknown permission modes receive the conservative normal-mode
policy and never autonomous privileges.

## Audit and explanations

The raw-command fingerprint is removed. Audit action identity is derived only
from a canonical structural record of non-secret fields: family, verb, target,
environment, scope, ordered operator kinds, sink kinds, risk, modifiers, and
stable reason codes.

Parser-aware redaction covers every accepted credential position, including
short and attached database options, HTTP header aliases, URI user information,
cookies, query credentials, PowerShell values, environment assignments, and
provider-specific token headers. Unknown credential-shaped input fails before
serialization.

Every `ask` and `deny` lists bounded per-stage reason codes, the safe target and
scope, the required operator action, and whether sensitive fields were
redacted. It never prints a raw command when that command contains or may
contain sensitive material.

## Executable test contract

Implementation follows red-green-refactor for every review finding. Each
reproduced bypass becomes a failing fixture before production code changes.

The existing synthetic coverage labels are replaced by executable fixtures.
Every fixture declares a stable ID, input event or command, mode, expected
decision, expected risk and modifiers, expected reason codes, and expected
stage findings. The runner records IDs actually executed. The manifest fails
for missing, duplicated, declared-but-not-run, or run-but-undeclared IDs.

The same corpus is executed through:

1. direct source-module tests;
2. source validator subprocess tests;
3. installed-module tests after isolated Nori activation;
4. installed validator subprocess tests.

Installed validation compares security-critical module bytes or cryptographic
content digests with the source package before executing the corpus. Hook
frontmatter, launcher, validator entrypoint, catalogue, parser, policy,
credential flow, redactor, audit, registries, and fixtures are in scope.

Required regression groups include:

- complete PowerShell wrapper consumption with actual harmless differential
  execution where PowerShell is available;
- every allowed and denied environment-assignment class;
- HTTP implicit methods, bodies, uploads, redirects, and file sinks;
- exact decryptor pipe topology and every alternate operator;
- first approval, successful activation, failed or denied activation, same and
  changed bindings, session and mode boundaries, expiration, corruption, and
  opaque identity behavior;
- every credential-bearing option and proof that changing only a synthetic
  secret does not change structural audit identity;
- sensitive and mutating variants of system, Kubernetes, cloud, database,
  container, PowerShell, network, and Git families;
- side-effecting SQL functions and grammar boundaries;
- destructive Git refspecs and external GitHub effects;
- equal-risk multi-stage explanations;
- tolerated observational metadata and rejected execution-affecting fields;
- missing Node.js, missing validator, crash, deadline, polluted output,
  malformed decision, and audit failure at source and installed paths;
- an actual executed-fixture coverage ledger and deliberate missing-fixture
  self-test;
- whitespace and package-content gates.

## Live smoke exception and controls

The live smoke remains opt-in and may import the operator's normal Claude
provider credentials. Running it additionally requires a dedicated
acknowledgement flag whose name and warning make that exposure explicit. The
harness never prints, hashes, compares, snapshots, or places the provider
credential values in generated command fixtures.

The smoke retains a generated home, minimal inherited environment, read-only
runtime mounts where supported, isolated writable directories, and synthetic,
loopback, or disposable operational targets. The command policy denies direct
references to provider credential variable names and general environment-dump
families. Retained output is scanned for synthetic markers and provider
variable names.

Network access to the selected model provider remains available and therefore
the normal credentials remain exposed to the Claude process. These controls
cannot eliminate malicious or compromised-process exfiltration. The harness
must print that residual risk before execution and record the accepted
exception in its result. Disposable provider credentials or egress
allowlisting remain the preferred future remediation.

## Documentation and delivery

The implementation phase updates ADR-004 to the behavior actually enforced,
updates README and release notes where operator behavior changes, and keeps the
independent review record linked from the documentation index. The review
record receives a finding-by-finding closure table only after verification.

Delivery requires all local gates, installed validation, the explicitly
acknowledged live smoke, green GitHub checks, and a new independent review. The
pull request remains draft and is not merged as part of this remediation.

## Alternatives rejected

- **Remove executor shell access:** rejected because the skillset must remain
  an operational executor.
- **Allow every literal in bypass mode without state:** rejected because the
  guard cannot distinguish approved reuse from a newly redirected credential.
- **Store or hash credentials for equality checks:** rejected because it turns
  guard state and audit into secret-derived material.
- **Treat every pipe as unsafe:** rejected because bounded direct data flows
  are necessary for operational work and can be modelled deterministically.
- **Require disposable provider credentials immediately:** preferred but
  deferred by explicit operator decision; normal credentials remain the
  documented temporary live-smoke exception.
- **Depend on a new proxy or daemon:** rejected for this phase because the
  native Claude Code and Nori installation must remain sufficient.
