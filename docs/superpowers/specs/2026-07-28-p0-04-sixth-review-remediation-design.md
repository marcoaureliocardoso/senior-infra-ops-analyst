# P0-04 Sixth Review Remediation Design

## Context

The sixth independent review confirmed RV-31 through RV-36 but found four
remaining gaps. Redis `EXPIRE` is classified without validating the TTL or
arguments, mutable HTTP requests are classified only by method, the central
catalogue is absent from the critical coverage and mutation gates, and the
catalogue models the invalid standalone verb `KILL` instead of `CLIENT KILL`.

These gaps can make the policy decision diverge from the effective operation
or allow a green gate to omit the most important classifier.

## Decision

### Redis command grammar

Use verb-specific, closed Redis grammars after the existing closed connection
option parser.

- `EXPIRE` accepts exactly one literal key, one literal base-10 integer TTL,
  and at most one of `NX`, `XX`, `GT`, or `LT`.
- Positive `EXPIRE` TTL values are `LOW_RISK_CHANGE`. Zero or negative values
  are `DESTRUCTIVE` because Redis deletes the key immediately.
- Missing, extra, dynamic, non-integer, or conflicting `EXPIRE` arguments fail
  closed.
- `PERSIST` accepts exactly one literal key and remains `LOW_RISK_CHANGE`.
- Standalone `KILL` is not catalogued.
- `CLIENT KILL` accepts only one literal legacy `host:port` target or the
  bounded form `CLIENT KILL ID <positive-integer>`. Both forms are
  `DISRUPTIVE_CHANGE`; all other subcommands or filter combinations fail
  closed until explicitly modelled.

Literal operands exclude shell variables, globs, braces, separators, and empty
values. The result target is derived from the validated operand rather than an
unvalidated positional token.

### Mutable HTTP requests

Keep `GET` and `HEAD` as bounded `SAFE_READ_ONLY` operations and keep `DELETE`
as `DESTRUCTIVE`. Classify `POST`, `PUT`, and `PATCH` as
`DISRUPTIVE_CHANGE` with `EXTERNAL_SIDE_EFFECT`, which forces an operator
confirmation in every permission mode.

No mutable HTTP operation receives autonomous execution until a future design
introduces an explicit catalogue keyed by exact origin, route, method, and
effect class. A static repository-wide origin allowlist is rejected because it
would be deployment-specific and would still fail to distinguish harmless and
disruptive routes on the same service.

### Quality gates

Add `catalogue.mjs` to the critical native coverage set with 100 percent line,
function, and branch thresholds. Extend the mutation registry with mutations
that must be killed by executable tests for:

- positive versus non-positive `EXPIRE` TTL classification;
- rejection of malformed Redis verb arguments;
- recognition of `CLIENT KILL` and rejection of standalone `KILL`;
- Redis canonical environment fields and rejected options; and
- mandatory confirmation semantics for mutable HTTP requests.

Coverage fixtures may exercise remaining structural branches, but behavioral
regressions and mutation witnesses must assert externally visible policy
results through the real classifier or policy entrypoint.

## Data Flow

1. The closed executable option parser produces a validated Redis invocation
   and its canonical non-secret environment.
2. A verb-specific parser consumes every remaining Redis argument.
3. Only a completely consumed grammar produces a family result, target, risk,
   and modifiers.
4. Policy applies the existing permission matrix. Destructive Redis actions
   and HTTP external effects always return `ask`.
5. Audit and credential binding continue to receive only the canonical
   non-secret environment and validated target.

## Compatibility and Operator Experience

The design preserves ordinary Redis reads, positive TTL changes, `PERSIST`,
and two explicit `CLIENT KILL` target forms. Unsupported Redis variants fail
closed with the existing actionable deny guidance. Mutable HTTP calls remain
available but require operator confirmation, including in
`bypassPermissions`; read-only HTTP remains autonomous where already allowed.

No Claude Code, Nori, DeepSeek, or Node.js version is pinned. Runtime behavior
continues to be selected through capability probes.

## Verification

- Demonstrate RED then GREEN for every new Redis and HTTP behavior.
- Cover `EXPIRE` with positive, zero, negative, dynamic, missing, extra, and
  conditional arguments in normal and bypass modes.
- Cover `PERSIST`, standalone `KILL`, supported `CLIENT KILL` forms, malformed
  composite forms, and dynamic targets.
- Prove mutable HTTP methods always ask and read-only methods retain their
  existing decisions.
- Prove `catalogue.mjs` satisfies the critical coverage thresholds and each new
  mutation is killed by a named executable test.
- Run the full source test gate, installed-corpus gate, package validation,
  documentation checks, diff hygiene, and secret/version-pin scans.

## Acceptance Criteria

The remediation is complete only when all four independent-review findings
have direct regression coverage, the full test and packaging gates pass, no
secret appears in decisions, audit, or binding state, and the final diff is
documented without weakening the previously closed RV-31 through RV-36.
