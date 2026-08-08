# P0-04 Catalogue Closure Remediation Design

## Context
The independent review of PR #25 reproduced four catalogue gaps after the
credential and remote-identity remediations:

1. `git push` accepts repository and receive-pack overrides without consuming
   or auditing them;
2. `journalctl` and container log clients accept infinite follow streams while
   reporting a bounded read;
3. supported GitHub CLI read verbs accept arbitrary options, including watch,
   broad logs, and excessive list limits;
4. `kubectl cluster-info dump` is classified as a narrow read despite its
   broad diagnostic and log output.

All four defects have the same root cause: a command family recognizes the
verb or one numeric bound but does not prove that every remaining option and
operand belongs to the modelled invocation. This violates the P0-04
fail-closed rule. The package remains version `0.11.0`; Claude Code, Nori,
Node.js, and the model remain observed runtimes rather than compatibility pins.

## Decision 1: parse `git push` as a complete invocation
Replace the push regular expressions with one closed parser. The parser
requires one literal repository, selected either positionally or by one
`--repo` spelling, and one to `LIMITS.fanOut` literal refspecs. It rejects
missing or conflicting repositories, unknown options, `--exec`,
`--receive-pack`, server push-options, local-hook bypass, dynamic operands, and
ambiguous option repetition. Every repository containing the `::` delimiter,
including transports such as `ext::<command>` or `1helper::address`, denies
because Git can execute the prefix as an unmodelled local helper.
For `scheme://` URLs, only Git's reviewed exact-lowercase native `file`, `git`,
`ssh`, `http`, and `https` transports are accepted. Git preserves the scheme's
case when selecting its helper, so unknown or case-altered schemes would invoke
a distinct external `git-remote-<scheme>` helper and therefore deny.

Named remotes such as `origin` also deny. Git can resolve them through
`remote.*.pushurl`, `remote.*.url`, or `url.*.pushInsteadOf`, so the literal
alias is neither the effective destination nor a safe audit domain. Accepted
destinations must instead be explicit native URLs, SCP-like addresses, or
local paths whose syntax cannot be a configured remote name.

Explicit syntax still does not prove the effective destination. Git applies
`url.*.pushInsteadOf` and `url.*.insteadOf` to literal URLs, SCP-like
addresses, and local paths before transport selection. The command-only guard
does not inspect or neutralize every system, global, local, included, and
conditional Git configuration source. Consequently, every successfully parsed
push carries `ALWAYS_ASK`, including in `bypassPermissions`. Native operator
confirmation is the boundary that authorizes execution despite that unresolved
configuration state.

The parser consumes a deliberately finite option set. Ordinary pushes are
`LOW_RISK_CHANGE`; force, deletion, mirror, prune, or destructive refspec
spellings are `DESTRUCTIVE`. Its result binds the literal requested repository
address as environment and the normalized refspec list as target. Permission
and audit therefore describe the requested operation without claiming that
the address is Git's effective destination or helper.

## Decision 2: make log reads finite by grammar
Add separate closed parsers for `journalctl` and container `logs` invocations.
Both consume every accepted option and operand, reject unknown or repeated
semantic selectors, and deny every enabled `-f` or `--follow` form. A numeric
line/tail bound remains mandatory and cannot exceed `LIMITS.outputRows`.

The journal parser retains the existing destructive classification for rotate,
vacuum, flush, sync, and relinquish operations. The container parser supports
the documented finite Docker, Podman, Nerdctl, and CRI client spellings,
including timestamps and literal since/until selectors, while requiring one
literal container target. The hook deadline remains only a guard-evaluation
deadline and is not treated as command-runtime containment. The parsed
container remains the audit target rather than collapsing to `local`.

## Decision 3: close GitHub CLI read verbs individually
Replace the shared read-prefix expression with verb-specific schemas for
`repo view`, `pr view`, `pr list`, `pr checks`, `run view`, `run list`,
`workflow view`, and `workflow list`. Each schema consumes its literal selector,
one repository selector, bounded list limits, and only documented output or
filter options. The repository must be explicit through `--repo` or the
`repo view` operand; implicit current-directory selection denies because it
cannot form a stable credential or audit domain. Unknown, repeated, routing,
web, and watch options deny.

`run view --log` and `--log-failed` remain operationally useful but are
classified `SAFE_READ_ONLY` with `SENSITIVE_OUTPUT`, `RESOURCE_INTENSIVE`, and
`ALWAYS_ASK`. List limits, when supplied, must not exceed `LIMITS.outputRows`;
an absent limit retains the client's finite default. The effective repository
continues to form the non-secret credential and audit domain.

## Decision 4: reject broad Kubernetes dumps
Reject the positional `dump` subcommand from the accepted `cluster-info`
grammar. Plain `kubectl cluster-info` remains a bounded read. `cluster-info
dump`, its `k3s kubectl` form, and any
unconsumed variant deny until the catalogue can model a finite destination and
scope; it does not inherit `SAFE_READ_ONLY` merely because the parent verb is a
read.

## Verification architecture
Every decision is protected by:

1. focused policy tests observed RED before production changes and GREEN after;
2. stable RV-76 through RV-88 source and installed-corpus fixtures;
3. exact one-site security mutations with typed behavioral witnesses;
4. finite-inventory/orphan checks, 100 percent critical coverage, package
   byte-equivalence, repository validators, and an independent read-only review.

The review ledger, ADR-004, README, and CHANGELOG will record the closed-parser
boundary. No raw command, credential, runtime pin, or new dependency is added.
