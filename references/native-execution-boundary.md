# Native execution boundary

Use this reference to select the execution route before an infrastructure
operation. The route is determined by the guarantees required for the actual
effect, not by convenience, permission mode, or tool availability.

## Lifecycle phases

- `DIAGNOSE` gathers observed evidence with the least risky bounded read.
- `PROPOSE` describes an unexecuted operation, risk, target, validation, and
  rollback without claiming an effect.
- `EXECUTE` performs only the exact operation authorized by the native route.
- `VALIDATE` observes the postcondition independently of the execution claim.
- `ROLLBACK` performs an independently authorized reversal or compensating
  action when the intended postcondition is not met.

## Coverage states

- `ACTIVE` means exact effective hooks are owned and the current session's exact
  harmless probe received the expected structured command-guard denial.
- `CONFIGURED_UNPROVEN` means exact settings are present but the current session
  has not proved live hook invocation; settings alone establish `CONFIGURED_UNPROVEN`.
- `ABSENT` means the package-owned main-session hook pair is not effective.
- `CONFLICT` means ownership, scope, policy, path, or settings drift prevents an
  exact determination.
- `UNSUPPORTED` means the detected runtime does not expose the required native
  hook contract.

Direct main-session operational Bash requires `ACTIVE` coverage. The exact
session probe is `printf P005_GUARD_PROBE`. Its structured denial proves only
that the current tool boundary is covered; it does not authorize a later command.
A missing hook result leaves the session unproven and requires
delegation or no execution.

## Routing matrix

| Operation | Phase | Route | Minimum condition |
|---|---|---|---|
| `NARROW_DIAGNOSIS` | `DIAGNOSE` | `PROTECTED_BASH` | Guard proves a complete bounded read, target, environment, stages, limits, and data flow; a typed read may be used instead |
| `UNEXECUTED_PROPOSAL` | `PROPOSE` | `NO_EXECUTION` | The proposal must never be represented as executed evidence and identifies risk, target, validation, and rollback when applicable |
| `CATALOGUED_NON_DESTRUCTIVE` | `EXECUTE` | `PROTECTED_BASH` | The exact fully modelled call receives its native decision; permission mode does not change risk |
| `DESTRUCTIVE_SHELL` | `EXECUTE` | `PROTECTED_BASH` | A destructive shell operation always returns `ask`, including in `bypassPermissions`; changed input requires a new decision |
| `AMBIGUOUS_SHELL` | `EXECUTE` | `NO_EXECUTION` | Unknown, evasive, unbounded, uncatalogued, or input without an explicit target is denied and must never be upgraded by prose |
| `TRANSACTIONAL_MULTI_TARGET` | `EXECUTE` | `TYPED_TOOL` | A transaction boundary requires `TYPED_TOOL`; coordinated multi-target state requires `TYPED_TOOL` |
| `EXTERNAL_WORKFLOW_MUTATION` | `EXECUTE` | `TYPED_TOOL` | durable idempotency requires `TYPED_TOOL`, with bound authorization, audit, validation, and compensation |
| `EXECUTOR_FALLBACK` | `EXECUTE` | `PROTECTED_EXECUTOR` | When main coverage is unproven, delegate to `PROTECTED_EXECUTOR` or use `NO_EXECUTION`; the executor must have proven exact Pre/Post Bash hooks |
| `NO_PROTECTED_ROUTE` | `EXECUTE` | `NO_EXECUTION` | Return the observed limitation, unexecuted plan, proposed operation, required operator action, and validation steps |

## Protected Bash invariants

Protected Bash is sufficient only when the existing guard proves the complete
bounded command structure, explicit target and environment, every stage and
redirect, the highest plausible risk and modifiers, credential transport and
authorization domain, complete external effect and data flow, bounded
validation, and rollback or compensation where applicable.

The guard result is authoritative for the exact call. `allow` permits only that
call, `ask` requires the native exact decision, and `deny` requires safe
reformulation or another valid route. A denial must never be upgraded by prose,
a textual approval token, settings presence, or `bypassPermissions`.

## Typed-tool invariants

A typed operational interface is required when safety depends on transaction
state, atomic or coordinated multi-target changes, durable idempotency or
replay protection, structured authorization and expiry, server-side audit,
cross-call validation, or rollback that a single guarded shell call cannot
prove. A missing typed capability never weakens the protected Bash invariants
and never authorizes free-form shell.

Typed mutable calls must bind the target, environment, scope, risk,
authorization reference, idempotency key, expiry, audit correlation,
credential reference, expected precondition, validation, and rollback or
compensating action. The trusted server enforces those fields.

## Delegation and refusal

Use a matching executor only when its installed PreToolUse and PostToolUse Bash
hooks are proven exact. Every executor call receives an independent native
decision. Analytical agents without Bash do not acquire an execution route.

If main-session coverage is not `ACTIVE`, delegate to a proven executor. If no
protected executor or typed tool satisfies the required invariants, do not
execute. Return the observed limitation and clearly label commands as proposed,
not observed evidence.

Session proof is ephemeral. A new or resumed session, `/clear`, compaction,
permission-mode change, runtime change, settings or hook change, installed-path
change, or relevant policy change invalidates it. The probe never carries an
authorization, credential reuse, or operational result across those events.

## Browser and MCP boundaries

P0-04B and P3-16 remain outside P0-05 implementation scope. Browser reads and
mutations require the future P0-04B controls. The typed operational gateway is
owned by P3-16. P0-05 defines routing interfaces only and does not implement a
browser action, MCP server, model proxy, provider client, or parallel runtime.

MCP annotations are untrusted hints. They improve discovery but do not prove
authorization, read-only behavior, idempotency, destructive behavior, or safe
execution; the trusted host and server must enforce those guarantees.

## Related references

- `references/command-execution-protocol.md`
- `references/risk-levels.md`
- `references/diagnostic-order.md`
- `docs/architecture/ADR-004-native-command-guard.md`
