# P0-04B Disposable Permission Handler Design

**Status:** Approved design
**Date:** 2026-09-17
**Scope:** Automated active-runtime acceptance only

## Context

The P0-04B active-runtime harness uses Claude Code print mode so it can retain
bounded structural SDK and hook evidence. A mutable browser workflow correctly
receives the native command-guard decision `ask`; print mode therefore needs a
`--permission-prompt-tool` decision before Bash can execute. Requiring a human
to answer that test-only permission is unnecessary because the target is an
ephemeral loopback fixture, all credentials and state are synthetic, the effect
is bounded and reversible, and the complete run already requires explicit
authorization for its authenticated provider requests.

Production is different. The package does not install a permission MCP server
and does not automate production approval. Interactive production work uses the
native Claude Code permission prompt for every `ask` decision.

This design supersedes only the operator-provided interactive permission MCP
assumption in the Task 4 acceptance harness of
`2026-09-02-p0-04b-one-shot-workflow.md`. All browser policy, one-shot binding,
origin containment, credential, validation, cleanup, and evidence requirements
remain unchanged.

## Decision

Add a test-only, disposable stdio MCP permission server. It makes two
predeclared decisions in two independent Claude Code sessions:

1. `ALLOW`: allow one exact synthetic loopback workflow, then require the
   existing independent browser validation to prove the mutation.
2. `DENY`: deny one exact workflow that requests an observably different
   synthetic state, then require an external fixture observation to prove that
   no second effect occurred.

The decisions are deterministic test policy, not observed human approval. Live
evidence and documentation must label the mode `synthetic-deterministic` and
must never claim that a person approved either call.

## Scope and Non-Goals

The handler:

- exists only under `tests/` and a disposable runtime directory;
- is excluded from Nori staging, archives, installed skills, and production
  configuration;
- handles only the two P0-04B synthetic workflow permission requests;
- never handles credentials, browser content, prompts, transcripts, or page
  state;
- never provides a general Bash allowlist or reusable authorization service;
- never replaces the production Claude Code permission prompt;
- never retries a denied, failed, timed-out, or ambiguous workflow.

Testing Claude Code's visual prompt rendering or a person's interaction with
that prompt is not a package acceptance requirement. The package is responsible
for producing and preserving the native `ask` decision; Claude Code owns its
interactive production UI.

## Components

### Structural verifier

A Node.js verifier imports the package's production Bash lexer, composition
builder, and browser runner parser. It accepts one permission request through a
bounded process interface and returns only a bounded structural decision
record. It requires:

- tool name `Bash` and a closed set of supported Bash input fields;
- one command stage with no operators, redirects, assignments, or background
  execution;
- the literal `node` executable token required by the production guard and the
  exact installed browser runner path;
- the expected run nonce, workflow session, loopback origin, phase, role,
  effect, action set, protected-reference classes, expiry bound, and validation
  requirement;
- the phase-specific synthetic desired state;
- one canonical workflow invocation fingerprint.

Malformed, unknown, extra, reordered, expired, cross-session, cross-origin, or
wrong-phase input is a denial. The verifier emits no raw command, workflow
records, protected references, or rejected input.

### Disposable MCP permission server

A small Python stdio MCP server exposes exactly one tool with the schema
required by Claude Code's permission-prompt interface: `tool_name` plus `input`.
It implements only MCP initialization, tool listing, ping, and the one tool
call. Its server configuration contains the expected phase and paths to the
verifier, one phase claim file, and one content-free signal file.

For the `ALLOW` phase, a successful exact structural verification produces the
JSON-stringified permission payload:

```json
{"behavior":"allow","updatedInput":"<the exact unchanged input object>"}
```

For the `DENY` phase, a successful exact structural verification produces:

```json
{"behavior":"deny","message":"P004B_SYNTHETIC_DENY"}
```

The illustrative `updatedInput` value above denotes the original object, not a
string in the implementation. The handler performs a deep equality check before
return and never modifies, augments, or normalizes the tool input.

Any verification failure returns a generic denial. Protocol errors also fail
closed and contain no rejected values.

### Parent harness

The parent harness creates two private, strict MCP configurations after the
loopback fixture origin and both workflow sessions are known. Each configuration
contains only its one disposable permission server. Measurement invocations use
a separate minimal configuration and do not receive the workflow permission
server.

The authenticated acceptance budget is fixed at six top-level Claude Code
invocations: four trusted measurement invocations, one allowed workflow, and
one denied workflow. The maximum model-turn budget is 40. There is no automatic
retry.

## One-Time and Ordering Guarantees

Each phase has a distinct random session, operation, claim path, and expected
workflow shape. The MCP server atomically creates its owner-only claim file with
exclusive and no-follow semantics before returning a decision. A duplicate or
concurrent call is denied. The parent accepts evidence only when:

- `ALLOW` occurs first and exactly once;
- the allowed workflow receives the installed guard's exact `ask`, executes the
  exact runner once, and finishes with `WORKFLOW_VALIDATED`;
- `DENY` occurs second and exactly once in a different session;
- the denied Bash request has the installed guard's exact `ask` but no runner
  execution, PostToolUse success, mutation, or workflow validation lifecycle;
- an independent fixture observation proves the state still equals the result
  of the allowed phase;
- no later tool activity or permission request exists in either sample.

The first decision cannot authorize the second operation because session,
operation ID, desired state, claim, and invocation fingerprint differ.

## Evidence and Retention

Each phase signal admits only:

- schema version;
- run nonce;
- phase (`allow` or `deny`);
- decision (`allow` or `deny`);
- call count exactly one;
- a canonical invocation fingerprint;
- booleans for exact verification and unchanged input.

Signal and claim files are regular, owner-only, bounded, non-symlink files
inside the disposable root. The trusted parent correlates the signal
fingerprint with the exact SDK Bash tool use and reduces it to the final
content-free aggregate. Raw prompts, SDK streams, permission requests, MCP
configs, signals, claims, session stores, and fixture state are deleted before
the aggregate is emitted.

The final aggregate may report only `synthetic-deterministic` permission mode,
the two decisions, structural counts, runtime labels, route class, workflow
outcome, numeric context measurements, and cleanup status.

## Failure Semantics

The run is blocked or inconclusive when the handler, verifier, claim, signal,
MCP lifecycle, expected decision order, guard response, browser workflow,
external unchanged-state observation, or cleanup cannot be proved exactly.
`ALLOW` without a validated effect is inconclusive. `DENY` followed by any
runner execution or state change is a failure. A timeout or ambiguous mutation
remains `OUTCOME_UNKNOWN` and is never retried.

Native Windows remains unsupported for the disposable handler until equivalent
owner, no-follow, atomic-claim, and process-isolation guarantees are proved.

## Test Strategy

Implementation follows red-green-refactor and adds provider-free tests for:

- exact MCP initialization, listing, and permission response envelopes;
- the complete structural verifier contract and every fail-closed boundary;
- exact input preservation on allow;
- deterministic denial and generic mismatch denial;
- single-use, concurrency, size, ownership, and symlink handling;
- strict separation between measurement, allow, and deny MCP configurations;
- ordered allow evidence, validated mutation, deny evidence, and unchanged
  fixture state;
- rejection of forged, duplicate, reordered, cross-session, and later events;
- cleanup and absence from staged and archived Nori artifacts.

Provider-free pseudo-process tests exercise the server without a TTY or human
input. The existing real-browser matrix, focused WSL gate, complete package
gate, and independent review must pass after integration.

One separately authorized authenticated run then uses the currently configured
provider and model with only synthetic P0-04B prompts. Its authorization must
state the six top-level requests, 40-turn maximum, per-request and total
timeouts, no retry, loopback-only browser target, raw-evidence deletion, and
content-free final aggregate.

## Alternatives Rejected

- A human-interactive test MCP duplicates production UI behavior without
  improving package enforcement evidence.
- A persistent permission MCP broadens deployment and creates an unnecessary
  production authority surface.
- `--allowedTools Bash`, `bypassPermissions`, or a general allow rule bypasses
  the native `ask` path being tested.
- A first-call-wins handler can accidentally authorize an unrelated Bash call;
  both phase decisions therefore require complete structural verification.
- Denying the second call merely because the allow handler was already used
  tests exhaustion, not the explicit permission denial path.

## Official Interface Basis

- https://code.claude.com/docs/en/cli-reference
- https://code.claude.com/docs/en/headless
