# P0-04 Eighth Review Remediation Design

**Status:** Approved design pending implementation plan

**Date:** 2026-07-29

## Context

An independent read-only review of the complete PR #25 worktree verified the
Redis `EXPIRE` and `CLIENT KILL` corrections but reproduced five remaining
authorization defects:

1. curl's zero-argument `-O` and `--remote-name` flags consume a following body
   or upload option in the current parser, hiding the effective mutable method;
2. repeated PostgreSQL and MySQL connection selectors bind the first audited
   value while the client uses a later effective value;
3. HTTP output sinks do not validate or bind their effective local path;
4. long Git branch-deletion aliases fall through to low-risk classification;
   and
5. the mutation runner treats any non-zero witness process exit as a killed
   mutant without first proving the witness passes against pristine source.

The implementation remains AI-first and runs through native Claude Code hooks
from a Nori-installed skillset. It must remain portable across compatible
future Claude Code, Nori, Node.js, and model versions. No component or runtime
version becomes an installation requirement.

## Decision

Use small closed parsers for each affected client rather than a universal CLI
parser or isolated regex patches. Shared helpers may validate literal values,
bounds, canonical paths, and singleton occurrence counts, but curl,
PowerShell HTTP, PostgreSQL, MySQL, and Git retain client-specific grammars.

Every accepted grammar consumes the complete command form relevant to that
client. Unknown options, missing values, unsupported aliases, repeated
singletons, dynamic selectors, and unconsumed tokens fail closed.

## Hook and Policy Context

`parseHookEvent()` preserves the already validated `cwd` field as `cwd` on the
normalized event. Absence remains valid for read-only commands, but a relative
file sink cannot be authorized without a working directory.

`evaluateHook(raw, env)` passes the supplied environment to
`analyzeCommand(event, env)`. Policy code never enumerates or copies the
environment. It requests only explicitly configured output-variable names and
passes the minimum context required for sink resolution into the command
catalogue.

Direct tests and installed-corpus tests inject synthetic environments. The
default environment parameter preserves existing callers and exposes no output
variables when configuration is absent.

## HTTP Invocation Parsers

### curl

The curl parser distinguishes three option classes:

- zero-argument flags, including `-O` and `--remote-name`;
- options requiring one value, including output, method, body, upload,
  credential, timeout, certificate, and URL options; and
- explicitly repeatable options such as headers and body fragments.

Singleton method, URL, and output selectors reject repeated or mixed-alias
forms. Every option is consumed with its correct arity. `-O` and
`--remote-name` therefore cannot consume `-d`, `--data*`, `--json`, `-F`, or
`-T`. Existing denial of local request-file sources remains in force.

`-O` derives a deterministic filename from the final segment of the one
literal URL path. An empty, dot, dot-dot, encoded separator, or otherwise
ambiguous filename denies. Options that let the remote server replace the
filename, including remote-header-name behavior, remain outside the catalogue
and deny.

### PowerShell HTTP clients

`Invoke-WebRequest` and `Invoke-RestMethod` receive a case-insensitive closed
option parser. It consumes every supported option and rejects unknown,
missing, dynamic, or repeated singleton values. Method, URI, body, upload, and
`OutFile` are derived only from the parsed invocation, never by rescanning raw
words with first-occurrence helpers.

### HTTP effect identity

Mutable `POST`, `PUT`, and `PATCH` remain `DISRUPTIVE_CHANGE` with
`EXTERNAL_SIDE_EFFECT`, so every permission mode returns native `ask`.
`DELETE` remains `DESTRUCTIVE`. `GET` and `HEAD` without sinks retain read
semantics.

Every accepted local output sink is `LOW_RISK_CHANGE` with both `FILE_WRITE`
and `ALWAYS_ASK`. When a mutable HTTP call also writes a local response, the
higher disruptive risk and both effect modifiers are retained.

The canonical non-secret target contains both effects:

```text
METHOD /remote/path -> file:/normalized/local/path
```

The environment remains the literal remote origin. Changing either source
route or local destination changes the structural action identity. Audit
records contain this canonical target and never contain the raw command,
headers, bodies, credentials, or complete process environment.

## Output Path Resolution

Output-variable expansion is opt-in through a bounded comma-separated control
variable:

```text
OPS_COMMAND_GUARD_OUTPUT_VARIABLES=OPS_OUTPUT_DIR,OPS_EXPORT_DIR
OPS_OUTPUT_DIR=/var/tmp/operations
OPS_EXPORT_DIR=/srv/exports
```

The allowlist accepts at most eight unique simple environment-variable names.
Names containing credential or provider-control terms such as `TOKEN`,
`SECRET`, `PASSWORD`, `AUTH`, `COOKIE`, or `KEY` deny configuration. Missing,
empty, duplicate, malformed, or over-limit configuration denies the attempted
expansion without logging values.

Each configured value is declared non-secret operator metadata and must be a
bounded absolute POSIX or Windows directory. The resolver accepts only these
forms in an output operand:

- a literal path;
- `$NAME/literal-suffix` or `${NAME}/literal-suffix` for Bash; or
- `$env:NAME\literal-suffix` for PowerShell.

Nested/default/indirect expansion, command substitution, globs, additional
variables, and inline overrides deny. A resolved suffix must remain inside the
configured root after lexical normalization; dot-dot escape denies.

Literal relative paths resolve against the validated hook `cwd`. Literal
absolute paths use POSIX or Windows lexical normalization according to their
syntax. The guard does not use file existence or symlink state as an
authorization premise because either can change between hook evaluation and
execution. `ALWAYS_ASK` therefore applies to every accepted sink, including
paths under configured roots.

Local output-variable expansion is not inherited by nested SSH command
analysis because the hook cannot prove a remote environment. Dynamic remote
sinks deny.

## PostgreSQL and MySQL Binding

Client-specific parsers consume all supported connection selectors and the
query or administrative command. Host, port, user, database, and query options
form singleton alias groups; repeating a group denies before any effective
value is derived.

The PostgreSQL parser supports the existing bounded `psql -c/--command`
operations and literal `-h/--host`, `-p/--port`, `-U/--username`, and
`-d/--dbname` selectors. The MySQL parser supports the existing bounded
`mysql -e/--execute` and `mysqladmin` operations plus literal
`-h/--host`, `-P/--port`, `-u/--user`, and `-D/--database` selectors.

Canonical database environments include client family, host, bounded port,
user, and database with explicit stable default markers. A change from an
omitted selector to an explicit selector changes the domain. Credential reuse
therefore cannot cross a host, port, user, database, or client-family boundary.

Configuration files, service/login-path selectors, sockets, alternate
protocols, and TLS/trust overrides remain denied until a future design models
their complete effective semantics. Literal credential values remain excluded
from target, environment, structural identity, binding state, responses, and
audit.

## Git Branch Grammar

The `git branch` subcommand uses a closed grammar. Read-only list forms remain
`SAFE_READ_ONLY`; creation or rename forms remain catalogued changes; and all
deletion aliases are `DESTRUCTIVE`:

```text
-d
-D
--delete
--delete --force
```

A destructive form requires one or more bounded literal branch targets within
the existing fan-out limit. Missing targets, conflicting modes, unsupported
options, dynamic targets, and trailing unconsumed syntax deny. Existing
classifications for other Git subcommands are preserved in this remediation.

## Mutation Witness Architecture

Replace the duplicated witness-ID list and switch with one exported immutable
map:

```text
security predicate ID -> async witness function
```

Registry validation requires exact key equality among exported security
predicate IDs, source mutations, and witness functions. Each source mutation
must still match exactly one source site.

Before creating mutants, the runner executes every witness against pristine
source and requires success. For each mutant it then executes only the matching
witness in an isolated child process. A mutant is killed only when that witness
raises an identified Node `AssertionError` for its semantic invariant. Missing
witnesses, import or syntax errors, timeouts, arbitrary non-zero exits, and
already-failing baseline witnesses fail the gate rather than count as kills.

The harness remains deterministic, dependency-free, bounded, and based on
temporary copies removed only after verified path-prefix checks.

## Error Handling and Operator Experience

Unsupported or ambiguous command syntax returns an existing redacted native
`deny` with actionable reformulation guidance. Valid local file effects return
native `ask` in every permission mode. No resolution error echoes the command,
environment value, credential, request body, or unredacted path expression.

The permissive-mode contract remains unchanged: `bypassPermissions` permits
fully catalogued non-destructive operations, but it never disables parsing,
binding, credential-flow validation, destructive confirmation, external-effect
confirmation, or local-file-effect confirmation.

## Test Strategy

Each production change follows a witnessed RED/GREEN cycle through the real
policy entrypoint. Stable review fixtures RV-41 onward execute against both
source and Nori-installed artifacts.

Required coverage includes:

- both curl remote-name flags before every supported body and upload spelling;
- a disposable loopback fixture proving executed HTTP methods match policy;
- literal POSIX and Windows sinks, relative and absolute paths;
- configured, absent, arbitrary, credential-like, traversal, nested, and
  overridden output variables;
- repeated sinks, methods, database selectors, and mixed aliases;
- PostgreSQL and MySQL invalid bounds, config/socket/trust overrides, canonical
  environments, and credential-approval lifecycle changes;
- every Git branch deletion alias and malformed/conflicting forms;
- pristine witness success, missing witness, always-failing witness, import
  failure, surviving mutant, and expected semantic assertion failure; and
- exact source-to-installed behavior and byte equivalence.

Final verification runs the native Node gate with 100 percent critical
line/function/branch coverage, all registered mutations, Python repository
validators, host PowerShell syntax validation, Debian/WSL package validation,
and an isolated Nori install. It does not start Claude or load model-provider
credentials.

## Documentation and Versioning

ADR-004 records the new parsing, sink, database-binding, and mutation-witness
decisions. The independent-review record adds RV-41 through RV-45 and clearly
distinguishes local remediation from subsequent independent confirmation.
README operator guidance and the existing `0.11.0` changelog entry describe the
behavior changes. No new version is introduced solely for review remediation.

## Non-Goals

- A universal parser for every operational CLI.
- Autonomous file writes in `bypassPermissions`.
- File existence, ownership, symlink, ACL, or protected-directory enforcement
  as a substitute for operator confirmation.
- Expansion of arbitrary shell or PowerShell expressions.
- PostgreSQL/MySQL service files, sockets, external configuration, or custom
  TLS/trust material.
- Starting Claude or using normal provider credentials during deterministic
  verification.

## Acceptance Criteria

The remediation is complete only when all five independent findings have
stable source and installed-form regressions, the pristine-baseline mutation
protocol is enforced, every full validation gate passes, documentation records
fresh observed evidence, no runtime artifacts or secrets remain, and a new
independent read-only review finds no Critical or Important issue in the
resulting tree.
