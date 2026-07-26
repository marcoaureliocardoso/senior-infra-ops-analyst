# P0-04 Native Command Guard Design

**Status:** Approved, revised after operator review
**Date:** 2026-07-25
**Scope:** P0-04 — apply native `PreToolUse` enforcement to executor subagents

## Context

The project is an AI-first operational skillset executed by Claude Code,
distributed by Nori, and interpreted by the operator-selected model. Its
executor subagents must remain capable of performing real infrastructure
operations. Safety therefore cannot be implemented by removing shell
execution or by relying on the model to classify its own command correctly.

P0-03 limited `Bash` to eight executor roles. P0-04 adds deterministic
command-level enforcement at that remaining capability boundary. Runtime,
installer, and model identifiers are observed during validation and are not
package requirements.

The design was approved with three explicit product requirements:

1. `bypassPermissions`, including sessions started with
   `--dangerously-skip-permissions`, represents deliberate operator selection
   of autonomous execution.
2. Operational authentication must support SSH/sudo passwords, database
   credentials, HTTP/API tokens, PowerShell credentials, cloud and Kubernetes
   identities, credential helpers, and generic secret-bearing environment
   variables.
3. A literal credential explicitly supplied in the Claude Code conversation
   may be reused during the same `bypassPermissions` session for the same
   credential domain and identity, including different explicit catalogued
   targets in that domain, without asking the operator to enter it again.

## Goals

- Keep the eight executor agents operational rather than diagnostic-only.
- Use Claude Code's native `PreToolUse` decision contract.
- Apply a deterministic shared validator to every executor `Bash` call.
- Respect the effective Claude Code permission mode.
- Allow recognized operational changes in autonomous mode.
- Require an exact native decision in non-autonomous mode.
- Fail closed when a command cannot be analyzed conclusively.
- Support bounded operational pipelines without treating shell composition as
  automatically unsafe.
- Support legitimate credential use while preventing additional disclosure.
- Permit session-scoped reuse of an operator-supplied model-visible credential
  without turning the guard into a secret store or reusing command approval.
- Preserve the hook and validator path after Nori installation.
- Record hook decisions independently from the model's justification.

## Non-goals

- Do not pin Claude Code, Nori, Node.js, or a model identifier.
- Do not parse DeepSeek APIs or model reasoning content.
- Do not create a daemon, model proxy, approval service, or parallel runtime.
- Do not make Nori a credential vault.
- Do not claim that inline credentials are confidential from the model
  provider or the Claude Code transcript.
- Do not authorize arbitrary, encoded, or semantically ambiguous shell.
- Do not replace later typed MCP interfaces for operations that benefit from
  stronger schemas, idempotency, or transaction semantics.

## Native installation architecture

The following executor agents receive the hook:

- `diagnostic-operator`;
- `observability-sre`;
- `cloud-platform-operator`;
- `kubernetes-operator`;
- `database-operator`;
- `network-edge-operator`;
- `release-cicd-operator`;
- `audit-evidence-collector`.

Each source agent declares a `PreToolUse` hook in native Claude Code
frontmatter with matcher `Bash`. Nori installs Claude Code agents as Markdown
and substitutes `{{skills_dir}}` with the installed skills directory. The hook
uses exec form to invoke the shared validator by absolute installed path:

```yaml
hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: node
          args:
            - "{{skills_dir}}/command-driven-operations/scripts/validate-ops-command.mjs"
          timeout: 5
```

Node.js is used because it is already part of the Claude Code/Nori execution
pair. No separately managed Python runtime is introduced.

Source validation checks the exact hook semantics for all eight executors and
the absence of this `Bash` hook from the four analytical roles. Installed
validation compares the source and Nori-produced hook structure and confirms
that the validator path resolves to the installed shared script.

## Input and output contract

The validator reads one JSON event from stdin and requires:

- `hook_event_name` exactly `PreToolUse`;
- `tool_name` exactly `Bash`;
- `agent_type` in the executor allowlist;
- `permission_mode` as a non-empty bounded string; only documented semantics
  receive a mode-specific policy;
- `tool_input.command` as a non-empty bounded string;
- optional `tool_input.timeout` within policy;
- `tool_input.run_in_background` absent or `false`.

It returns only fields from the current structured Claude Code contract. A
policy `deny` includes the top-level `systemMessage` so the operator receives
the redacted explanation directly; `ask` uses the native permission prompt:

```json
{
  "systemMessage": "optional redacted operator warning for deny",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|ask|deny",
    "permissionDecisionReason": "redacted deterministic reason"
  }
}
```

Malformed input, unknown schema, internal exceptions, audit failure when audit
is required, and unsupported policy states exit with code `2`. No allow
decision is emitted on an error path.

### Decision semantics and operator feedback

The three decisions have non-overlapping meanings:

- `allow` means the complete operation is permitted by the current policy;
- `ask` means the complete operation is understood but requires an exact
  operator decision;
- `deny` means the operation is prohibited or cannot be analyzed safely and is
  not overridable for that tool call.

An authorizable condition must never be represented as `deny`. In an
interactive session, `ask` deliberately requests operator confirmation even
when the effective mode is `bypassPermissions`. In a non-interactive surface
where that prompt cannot be completed, the operation does not execute and the
validator must not downgrade `ask` to `allow`.

Every `ask` and `deny` response contains a deterministic, redacted explanation
with:

- a stable policy reason code;
- the affected command or composition stage;
- the risk and policy category;
- non-sensitive target, environment, and scope when known;
- the required operator decision for `ask`, or safe remediation guidance for
  `deny`;
- an explicit indication when sensitive fields were redacted.

The explanation never contains a raw credential or an unredacted command that
contains one. For `ask`, `permissionDecisionReason` is displayed in the native
operator prompt. For `deny`, the same safe summary is routed to the operator
through `systemMessage`, while `permissionDecisionReason` provides enforcement
feedback to the model so it can safely reformulate the operation. A `deny` is
not converted into a generic operator override prompt.

## Permission-mode-aware policy

`permission_mode` is the authoritative effective mode. The validator does not
attempt to distinguish whether `bypassPermissions` originated from
`--dangerously-skip-permissions`, `--permission-mode bypassPermissions`,
settings, or an in-session mode change.

| Command classification | Normal modes | `bypassPermissions` |
|---|---|---|
| Narrow `SAFE_READ_ONLY` | `allow` | `allow` |
| Bounded read with approval modifier | `ask` | `allow` |
| Catalogued `LOW_RISK_CHANGE` | `ask` | `allow` |
| Catalogued `DISRUPTIVE_CHANGE` | `ask` | `allow` |
| Catalogued `DESTRUCTIVE` | `ask` | `ask` |
| Ambiguous, encoded, evasive, or unmodelled | `deny` | `deny` |
| Suspected credential exfiltration | `deny` | `deny` |

Normal modes are `default`, `plan`, `acceptEdits`, `auto`, and `dontAsk`.
Claude Code remains responsible for the final behavior of an `ask` decision
in modes or non-interactive surfaces where a prompt cannot be completed.

An unknown future mode name does not receive autonomous privileges and does
not reject the whole runtime merely because its label is new. It follows the
conservative normal-mode policy: narrow `SAFE_READ_ONLY` can remain `allow`,
catalogued changes require `ask`, and forbidden or inconclusive operations
remain `deny`. The decision carries an `UNKNOWN_MODE_CONSERVATIVE` modifier so
live capability tests can determine whether a reviewed semantic mapping should
be added later.

The guard uses `ask`, rather than `deny`, for every fully analyzed operation
that policy permits only after human confirmation. This includes catalogued
`DESTRUCTIVE` operations and any composition whose aggregate policy requires
an exact decision. Native `PreToolUse` evaluation occurs before the permission
mode check, so this decision remains an intentional approval boundary in
interactive `bypassPermissions` sessions.

`bypassPermissions` is session-level authorization for catalogued
non-destructive operations. It is not a new risk level and does not suppress
deterministic validation. Every call is parsed again and receives its own
redacted audit decision.

`DESTRUCTIVE` retains an exact just-in-time human decision in every mode. This
is the non-negotiable recovery boundary.

## Deterministic command analysis

The validator never executes the proposed command and never asks an LLM to
classify it. It performs bounded lexical analysis and command-family policy
matching.

The initial grammar accepts either one foreground command or a bounded
composition that the shell-specific lexer can tokenize deterministically.
Bash-compatible and PowerShell syntax are analyzed by separate lexical
profiles because their quoting, escaping, and pipeline semantics differ. A
family policy declares:

- executable aliases;
- allowed operational verbs;
- risk level and modifiers;
- required target and environment selectors;
- bounded flags for time, output, namespace, quantity, and fan-out;
- credential-bearing argument positions;
- forbidden options and destructive variants.

Initial coverage prioritizes commands already documented by the project,
including local diagnostics and controlled families for system services,
Kubernetes, containers, cloud providers, databases, networking, SSH, sudo,
PowerShell, Git/CI, and authenticated HTTP operations.

The composition analyzer builds an ordered representation of command stages,
operators, redirections, and data-flow edges. It validates every stage against
its command-family policy, then evaluates the composition as a whole. The
aggregate decision is not merely the highest individual risk: independently
valid commands can create an unsafe source-to-sink flow when combined.

The initial composition rules are:

- `A | B` is supported when every stage is catalogued and the stdout-to-stdin
  flow is permitted; narrow read-only filters and bounded selectors are the
  first supported subset;
- PowerShell object pipelines are evaluated using a separate catalogue of
  permitted cmdlets, bounded script blocks, and object sinks;
- `A && B`, `A || B`, `A ; B`, and newline-separated commands require every
  branch or sequence member to be independently valid, with the aggregate
  state effects and risk evaluated;
- output and input redirections are treated as explicit read or write sinks
  whose destination must be determinable and permitted;
- background execution, command or process substitution, unsupported nested
  interpreters, dynamically constructed commands, and remote nested commands
  are denied until a specific parser can establish their complete semantics;
- `eval`, `Invoke-Expression`, dynamic `sh -c` equivalents, and unbounded
  command constructors such as unsupported `xargs` forms are not initially
  authorizable;
- a credential or sensitive-data source flowing to logging, persistence, an
  unrelated process, or an unvalidated network destination is denied;
- a supported credential transport flowing directly to its catalogued
  consumer can remain authorizable under the operation's risk policy.

The parser fails closed on unmatched quoting, unsupported operators, control
characters, ambiguous shell selection, an unknown stage, or an unproven data
flow. Broad substring or regex matches cannot authorize a command.

Unknown commands remain denied in both modes. The catalog grows through
versioned policy changes and positive plus adversarial tests.

## Target, environment, and scope

Mutating and remote command families must expose target and environment in
arguments that the parser can bind. Examples include Kubernetes context and
namespace, cloud account/profile and region/project/subscription, resource
identifier, remote host, database endpoint, service unit, or explicit API
origin.

Implicit current contexts are acceptable only for command families whose
policy classifies the operation as narrow read-only. A state change with an
implicit or variable-derived target is denied.

An exact native approval applies only to that tool call. Changing an argument,
target, environment, scope, credential transport, timeout, or background flag
causes a new evaluation. In autonomous mode, the new call can still be allowed
only if it independently satisfies the policy.

For a composed command, the exact approval also binds the ordered stages,
operators, redirections, and normalized redacted data-flow representation.
Adding, removing, reordering, or rewriting any component causes a new
evaluation.

## Credential handling

Credential use is supported; credential disclosure is minimized.

Supported mechanisms include:

- SSH agent, askpass, `sshpass`, and explicit SSH authentication options;
- sudo timestamp, askpass, and `sudo -S`;
- database environment variables, flags, connection strings, and protected
  credential files;
- HTTP Basic, Bearer, cookie, client-certificate, and header authentication;
- PowerShell `PSCredential`, `ConvertTo-SecureString`, `-Credential`, and
  authenticated headers;
- cloud profiles, SSO, cached sessions, credential helpers, kubeconfig, and
  exec credential plugins;
- generic variables whose names indicate password, token, secret, key, or
  credential content.

Credential references and provider-managed authentication do not change the
operational risk decision.

A detected literal credential raises a normal-mode decision to at least
`ask`, with a redacted warning that the value may already be present in the
model/provider and Claude Code transcript. In `bypassPermissions`, a literal
credential does not by itself prevent an otherwise allowed narrow read,
low-risk change, or disruptive change. Destructive actions still ask.

The validator denies:

- deliberate printing or logging of a secret;
- transfer of a secret to an unrelated process or ambiguous destination;
- authenticated redirects to an unvalidated origin;
- destinations built by substitution, encoded content, or unsupported shell
  composition;
- credential-bearing background jobs;
- secret material used by an unrecognised command family.

The validator must not echo, persist, hash, or include the raw secret in its
decision. Redaction happens before normalization and fingerprinting.

The project recommends provider profiles, credential helpers, agents,
keychains, preloaded environment variables, and direct operator login. These
are recommendations, not mandatory blockers.

### Model-visible literal credentials and session reuse

`MODEL_VISIBLE_LITERAL` is the handling class for a literal credential that
appears in a model-produced tool call after the operator supplied it through
the Claude Code conversation. This is a supported fallback, not a masked input
or secret channel: the value has crossed the model/provider and Claude Code
transcript boundary before `PreToolUse` runs. The hook can detect a credential
literal in the current tool call, but it cannot independently prove who
originally supplied it; operator provenance is a model-facing instruction, not
a guard assertion.

In a normal permission mode, every use of a `MODEL_VISIBLE_LITERAL` raises the
decision to at least `ask`. In `bypassPermissions`, the operator authorizes the
model to reuse that credential without asking for the value again when all of
the following remain true:

- the Claude Code `session_id` is unchanged;
- the effective mode remains `bypassPermissions`;
- the non-sensitive credential domain, principal or identity, and transport
  remain the same;
- every destination is explicit, catalogued, and belongs to that credential
  domain; different catalogued targets in the same domain are permitted;
- the current command independently satisfies the complete operation policy.

Credential reuse is not command-approval reuse. Every later command is parsed,
classified, scoped, and authorized again. A destructive operation still
returns `ask`; forbidden, inconclusive, misbound, persisted, logged, or
exfiltrating credential flow still returns `deny`.

The reuse contract has two enforcement layers. Model-facing agent instructions
require the session, mode, domain, identity, transport, and target invariants.
The deterministic hook authorizes only the current call from the metadata and
command it actually receives. It does not read the transcript or model
reasoning to reconstruct credential history.

The guard is stateless with respect to secret material. It never stores,
hashes, fingerprints, derives an identifier from, or compares credential
values. It may validate only the current call's non-sensitive domain,
identity, transport, target, and session metadata. Consequently, the guard
does not claim cryptographic proof that two literal values are the same
secret or that a prior call used the same domain. The deterministic hook
enforces the current call's target and data flow and fails closed when those
cannot be established; installed behavioral tests verify the model-facing
same-domain and same-identity rule.

Leaving `bypassPermissions`, ending the session, or losing the value from
model context ends the no-reprompt reuse behavior. The system must request the
credential again when it is no longer available and must never reconstruct or
invent it. Context compaction, session resumption, or a provider change can
therefore make reuse unavailable. Native provider caches and helpers such as
SSH/GPG agents, sudo timestamps, cloud sessions, keychains, and credential
helpers remain the preferred reliable reuse mechanisms.

For an encrypted credential file, the supported inline path is a catalogued
decryptor whose sensitive output flows directly to a catalogued consumer. The
passphrase and decrypted credential are both treated as sensitive; neither
may flow through stdout presentation, logs, command history created by the
project, intermediate files, unrelated processes, or background jobs.

## Audit model

Hook decisions are distinct from model reasoning. Audit records contain only
the minimum redacted fields needed to explain enforcement:

- timestamp and session identifier;
- agent type and permission mode;
- risk level and modifiers;
- policy family and deterministic rule identifier;
- parsed target, environment, and scope when non-sensitive;
- credential source classification, type, domain, identity, and transport when
  non-sensitive, never the credential value or a derivative of it;
- normalized redacted-command fingerprint;
- `allow`, `ask`, or `deny`;
- stable redacted reason code and affected stage number when applicable.

Raw commands, transcripts, tool output, credentials, cookies, authorization
headers, connection strings, private keys, and unnecessary personal data are
not written by the guard.

## Validation strategy

### Coverage contract

"All cases" means every finite behavior declared by this project, not every
possible byte string accepted by Bash or PowerShell. The supported grammar,
command catalogue, policy matrix, reason-code registry, limits, and edge-case
inventory are versioned finite sets. Tests exhaust those sets; bounded
property and fuzz tests explore input outside them.

The release gate requires:

- every supported grammar production and operator;
- every command family, verb, risk level, modifier, and policy rule;
- every supported `permission_mode` path and the conservative unknown-mode
  fallback;
- every `allow`, `ask`, and `deny` reason code;
- minimum, exact-limit, and over-limit values for every numeric or size bound;
- present, missing, empty, malformed, ambiguous, and conflicting forms of each
  required field;
- positive, boundary, negative, and composition cases for every policy rule;
- 100% branch coverage for the security-critical parser, normalizer/redactor,
  policy evaluator, decision serializer, and audit sanitizer modules;
- zero untested policy or reason-code IDs in a machine-checked coverage map;
- zero secret-marker occurrences across process output, diagnostics, coverage
  output, snapshots, audit records, and retained test artifacts.

Coverage percentage is a secondary signal. A 100% metric does not satisfy the
gate if the behavior matrix, edge-case inventory, mutation checks, or installed
tests are incomplete. Conversely, unreachable defensive branches must be
justified and removed or exercised rather than excluded silently.

Each catalogue or policy entry carries stable test references. The validator
build fails when an entry has no positive, boundary, or negative case, when a
test references a removed rule, or when an emitted reason code is absent from
the registry. Every defect adds a failing regression fixture before its fix.

Tests run in six layers:

1. pure lexer, parser, redactor, policy, and serializer unit tests;
2. generated decision-table and command-family contract tests;
3. composition, adversarial, property, and deterministic fuzz tests;
4. subprocess tests of stdin, stdout, stderr, exit codes, timeout, and failure
   behavior;
5. isolated Nori installation and installed-artifact tests;
6. opt-in live Claude Code smoke tests against synthetic or disposable
   targets.

Randomized tests use recorded seeds and bounded resources so CI is
reproducible. Every discovered failure is minimized into a permanent fixture.
An extended seed corpus may run outside the pull-request gate, but the bounded
deterministic corpus is mandatory on every change.

### Contract and policy tests

Tests first establish failing cases for:

- malformed and oversized JSON;
- empty input, whitespace-only input, byte-order marks, invalid encoding,
  trailing data, duplicate security-sensitive keys, non-object roots, excessive
  nesting, unexpected arrays, and prototype-like property names;
- missing or unexpected event, tool, agent, mode, or command fields;
- exact minimum, maximum, and one-over boundaries for command length, timeout,
  composition stages, output, fan-out, query scope, and audit fields;
- wrong scalar types, empty strings, non-finite numbers, negative values,
  unknown fields, background commands, and invalid timeouts;
- normal versus `bypassPermissions` decisions for every risk level;
- every normal mode individually, unknown future modes using conservative
  non-autonomous behavior without a name-based version gate, and mode changes
  between otherwise identical calls;
- `ask` forcing an exact interactive decision in `bypassPermissions`;
- non-interactive `ask` never being downgraded to `allow`;
- `deny` remaining non-overridable for the rejected tool call;
- redacted explanatory messages for every `ask` and `deny` family;
- direct operator visibility through the native `ask` prompt and deny
  `systemMessage`;
- exact target and environment requirements;
- approval invalidation after changes to any argument, stage, operator,
  redirection, target, environment, scope, credential transport, timeout, or
  background flag;
- complete decision-table coverage for risk modifiers alone and in supported
  combinations;
- source-to-installed hook preservation;
- fail-closed exception, timeout, malformed hook output, stdout pollution,
  audit failure, missing script, and unavailable runtime paths.

### Shell and evasion tests

Adversarial fixtures cover:

- permitted narrow read-only Bash and PowerShell pipelines;
- mixed-risk pipelines and source-to-sink policy escalation;
- destructive pipelines that produce `ask` when fully understood;
- forbidden or inconclusive pipelines that produce `deny` with remediation;
- pipes and redirections carrying synthetic sensitive data;
- zero, one, exact-maximum, and over-maximum pipeline stages;
- operators adjacent to tokens, operators inside quoted arguments, empty
  stages, repeated operators, mixed line endings, and comments near operators;
- `|`, `|&`, `&&`, `||`, `;`, newlines, input/output/append redirection,
  descriptor duplication, PowerShell all-stream redirection, and background
  jobs;
- `$()`, backticks, process substitution, and nested interpreters;
- here-documents, here-strings, line continuations, functions, aliases, dot
  sourcing, Bash arithmetic and brace expansion, and PowerShell script blocks,
  subexpressions, call operator, splatting, and stop-parsing token;
- environment expansion, assignment, indirection, unset variables, empty
  values, and assignments whose values contain operators;
- shell, PowerShell, Python, Node.js, SSH, and sudo wrappers;
- `cmd /c`, encoded PowerShell, dynamic interpreter flags, `eval`,
  `Invoke-Expression`, and command-building `xargs` forms;
- single, double, nested, unmatched, and escaped quoting; empty arguments;
  whitespace variants; tabs; carriage returns; nulls; and control characters;
- base64, hex, percent encoding, escaped and normalized Unicode, bidirectional
  controls, zero-width characters, homoglyphs, and operator lookalikes;
- path traversal, symlink-sensitive paths, wildcards, and glob expansion;
- relative, absolute, UNC, drive-qualified, spaced, dashed, reserved, and
  case-variant paths;
- downloads, remote scripts, and authenticated redirects;
- fan-out, broad logs, packet capture, and resource-intensive queries at every
  configured boundary;
- separately safe source and sink stages that become unsafe when composed;
- stage reordering, repeated stages, early failure, alternate branches, and
  data flows crossing read, write, process, file, and network boundaries.

### Credential tests

Synthetic markers cover every supported credential transport:

- SSH and sudo passwords;
- database flags, URIs, environment variables, and files;
- HTTP Basic/Bearer/cookie/client-certificate inputs;
- PowerShell credentials;
- cloud, Kubernetes, and Git credential helpers;
- generic token, password, key, and secret variables.

Each transport is tested by reference and literal value, with empty, repeated,
quoted, escaped, Unicode, delimiter-bearing, operator-bearing, and
percent-encoded synthetic values. Tests include URI userinfo, headers, cookies,
connection strings, files, environment assignments, stdin, and supported
direct pipeline consumers, plus benign lookalikes to control false positives.

Deterministic guard fixtures cover repeated literal-bearing calls, independent
authorization of every call, mode changes, explicit and ambiguous current
bindings, and encrypted-file decryptor-to-consumer flows. They do not claim to
prove conversation provenance, prior-domain equality, or context retention.
Installed behavioral scenarios cover initial and repeated use in the same
session, the model-facing same-domain and same-identity rule across different
catalogued targets, a new session, and lost model context. Together the tests
distinguish a reusable credential value from command approval: destructive
reuse asks, while persistence, logging, exfiltration, ambiguous current
binding, and unsupported consumers deny.

Tests assert that normal mode asks, autonomous mode follows the operation's
policy, destructive actions still ask, exfiltration denies, and no synthetic
secret appears in stdout, stderr, audit output, or retained test artifacts.
They also assert that an authorizable operation is never labelled `deny`, and
that a denied operation cannot be executed by accepting a generic prompt.
Forced exceptions at every processing stage assert that redaction occurs
before normalization, fingerprinting, explanation, audit, test reporting, and
failure serialization.

### Property, fuzz, and mutation tests

Bounded generators produce valid and invalid commands for both shell profiles.
The invariant suite asserts:

- no malformed, unknown, ambiguous, or over-limit input returns `allow`;
- parsing and normalization are deterministic and do not execute input;
- redaction is idempotent and no known synthetic marker survives any output;
- adding an unknown stage or unsafe source-to-sink edge cannot make a decision
  less restrictive;
- changing a bound from within policy to outside policy cannot preserve
  `allow`;
- serialized output is exactly one valid JSON object on successful hook paths;
- any uncaught exception or timeout prevents execution;
- equivalent quoted separators remain arguments, while real separators remain
  composition operators.

Mutation checks remove or invert each policy predicate, risk escalation,
redaction rule, and decision-precedence branch in turn. The suite must fail for
every such mutation. Surviving mutations block release until a test is added
or the allegedly redundant code is removed with review.

### Installed and live behavior

An isolated Nori activation verifies all eight installed executor hooks and
the resolved shared script. The opt-in Claude Code smoke runs only against
synthetic or disposable targets and includes:

- a normal-mode read and controlled mutation;
- a `bypassPermissions` read and controlled mutation;
- a bounded read-only pipeline in each supported shell profile;
- a destructive command that still asks or is safely prevented from reaching
  a real executor;
- a rejected composition whose detailed redacted reason is visible and cannot
  be overridden for that call;
- a malformed-command denial;
- a hook-failure denial;
- a synthetic credential flow with retained artifacts scanned for leakage;
- repeated use of a synthetic `MODEL_VISIBLE_LITERAL` in one
  `bypassPermissions` session, followed by a mode-change or session-boundary
  case that does not silently claim continued reuse.

Installed tests repeat the contract manifest against source and installed
paths so packaging cannot silently drop a fixture, policy entry, reason code,
hook, or validator module. Live tests validate representative outcomes, while
the exhaustive finite matrices remain in deterministic local tests and do not
depend on model wording.

The harness discovers runtime commands and records observed versions without
converting them into compatibility gates.

## Documentation and release impact

Implementation adds ADR-004 and updates the architecture index, README,
project documentation, command-execution policy, risk authorization wording,
release notes, and consistent version metadata. The external TODO is aligned
before implementation and receives final evidence after integration.

P0-05 is narrowed to define when native guarded shell is sufficient and when
typed MCP operations provide materially stronger semantics. It no longer
prohibits every autonomous state change through Bash.

## Capability evidence

The design relies on public native contracts rather than observed version
strings:

- Claude Code hooks reference:
  <https://code.claude.com/docs/en/hooks>;
- Claude Code permission modes:
  <https://code.claude.com/docs/en/permission-modes>;
- Claude Code permission rules and hook ordering:
  <https://code.claude.com/docs/en/permissions>;
- Nori Claude Code subagent installation at the observed reference:
  <https://github.com/tilework-tech/nori-skillsets/blob/skillsets-v0.31.0/src/cli/features/shared/subagentsLoader.ts>;
- Nori installed-path substitution at the observed reference:
  <https://github.com/tilework-tech/nori-skillsets/blob/skillsets-v0.31.0/src/cli/features/template.ts>.

The Nori links document the capability evidence available during design. They
are not compatibility pins; installed-artifact tests remain the forward
compatibility contract.

## Residual risks

- A credential pasted into a prompt has already reached the model/provider
  boundary before `PreToolUse`; the hook can only prevent additional
  disclosure.
- Session-scoped model-context reuse is best effort. Context compaction,
  session resumption, or provider behavior can remove the value, and the guard
  deliberately cannot recover it.
- Because the guard stores no secret or secret-derived identifier, it cannot
  prove that two literal values are the same credential. It validates the
  current call's non-sensitive binding and data flow; conversation provenance,
  prior-domain equality, and same-identity reuse remain model-facing
  invariants validated by installed behavioral tests rather than deterministic
  historical claims from the hook.
- Native credential helpers can cache authentication outside the guard. Their
  lifetime and revocation behavior must be governed by the provider and
  operator environment.
- Command-family policy cannot cover every current or future infrastructure
  CLI immediately. Unknown commands fail closed until reviewed.
- The bounded composition grammar intentionally supports fewer constructs than
  the underlying shells. Unsupported composition is reformulated or added
  through a reviewed policy and adversarial-test change.
- A parser can establish syntactic target and scope but cannot prove the
  operator's real-world intent.
- `bypassPermissions` is deliberately broad session authorization. It
  increases operational autonomy and blast-radius risk by design.
- The main Claude Code session is outside an executor-scoped hook if it can
  invoke `Bash` directly. Global enforcement remains a separate control unless
  the Nori-installed artifact exposes a supported global hook path.
- Later typed MCP tools remain preferable for complex destructive,
  transactional, multi-target, or externally persisted operations.
