# PR #25 Independent Review Verdict

**Date:** 2026-07-26

**Scope:** P0-04 native command guard, PR #25

**Initial reviewed commit:** `0f03bb999afc7c6f878eb28b770357cdb06ddc88`

**Final reviewed commit:** `7c2e32751001adfbf8bdc1036465d7ec2bdbfa1a`

**Previous verdict:** Ready to merge with RV-11 accepted as a temporary
exception; superseded by the 2026-07-28 re-review below

**Re-review base commit:** `99800545ba998931a022855a962f0357a86a0d0e`

**Current verdict:** Changes required. The latest self-review remediation is
implemented in the PR worktree, but merge authorization requires a fresh
independent review of the new head. RV-11 remains an accepted temporary
exception.

**Remediation design:**
[P0-04 review remediation](../superpowers/specs/2026-07-26-p0-04-review-remediation-design.md)

## Initial verdict

The implementation establishes a useful deterministic enforcement boundary,
but it is not safe to merge in its reviewed form. The source suite reported 62
active passing tests, one intentional skip, 100 percent structural coverage,
and 11 killed mutations. All nine GitHub checks were green. Those results do
not cover several executable semantic paths that can be incorrectly allowed,
nor do they prove equivalence between source and installed behavior.

The blockers below were independently reproduced. Each requires a failing
regression fixture before its correction. The verdict remains open until the
source validator, installed artifact, and applicable live smoke have passed
the remediated gates and a new independent review records no blocking finding.

## Final independent disposition

The second independent review of the final head found no remaining blocker. RV-01
through RV-10 and RV-12 through RV-17 are resolved. RV-11 remains an explicitly
accepted temporary exception: normal provider credentials may enter the live
smoke process only after the dedicated acknowledgement, while provider egress
remains open and is reported as residual risk.

The final independent review executed 31 targeted cases and the complete
suite of 87 active tests with one intentional mutation-only skip. It observed
100 percent line, function, and branch coverage, killed all 11 security
mutations, validated all 11 installed-artifact checks, executed the same
27-fixture adversarial corpus against source and installed forms, and passed
the formatting check. The reviewer also reproduced the corrected PostToolUse
no-op behavior, sensitive process and AWS classifications, the real audit
failure path, and the executable RV-12 fixture linkage.

## Blocking findings

| ID | Finding | Reproduced behavior | Required outcome | Status |
|---|---|---|---|---|
| RV-01 | Hook bootstrap can fail open | Native hook infrastructure errors outside the validator do not reliably block execution | A launcher must convert missing runtime, missing artifact, validator crash, malformed output, and internal deadline failure into native blocking exit `2` | Resolved |
| RV-02 | PowerShell wrapper drops outer composition | Only the argument after `-Command` is analyzed; outer operators, redirections, and remaining arguments can escape analysis | Parse the complete outer command and accept only one fully consumed, unambiguous wrapper invocation | Resolved |
| RV-03 | Arbitrary environment assignments can replace execution semantics | Generic `NAME=value` prefixes permit control variables such as `PATH`, `LD_PRELOAD`, and `GIT_EXTERNAL_DIFF` | Permit only explicitly modelled non-control assignments; deny unknown and execution-control variables | Resolved |
| RV-04 | HTTP side effects and file sinks are underestimated | Body, upload, and output options can be classified as safe read-only operations | Use client-specific parsers that derive effective method, request body, upload, redirect, authentication, and every local sink | Resolved |
| RV-05 | Protected credential flow accepts sequence instead of pipe | A decryptor followed by `;` can print a secret and still be accepted as a protected consumer flow | Require exactly one immediate `|` edge from the decryptor to one direct catalogued consumer and reject every other edge or sink | Resolved |
| RV-06 | Credential reuse is not bound to prior operator approval | A literal is accepted from its current generic consumer without trusted session, domain, identity, or transport state | Activate only non-secret binding state after a matching operator-approved tool use and require the same binding for reuse | Resolved |
| RV-07 | Redaction and audit identity depend on raw secret material | Several credential forms survive redaction and different secret values alter the command fingerprint | Detect secrets with parser-aware schemas and remove raw-command or secret-derived fingerprints from decisions and audit | Resolved |
| RV-08 | Generic read families expose secrets or perform mutations | Examples include secret reads, environment-bearing process listings, journal vacuum, socket destruction, and broad inspect operations | Replace generic read labels with executable-specific argument schemas, sensitive-output rules, and explicit mutating variants | Resolved |
| RV-09 | SQL classification relies on an incomplete keyword blacklist | Side-effecting functions can execute inside statements classified as reads | Authorize only a narrow parsed read subset and deny or ask for unproved functions, clauses, and multi-statements | Resolved |
| RV-10 | Destructive Git push forms are underestimated | Mirror, prune, deletion refspecs, and force refspecs can receive low-risk autonomous treatment | Parse push refspecs and destructive flags explicitly; destructive variants always require an exact operator decision | Resolved |
| RV-11 | Live smoke exposes normal provider credentials | The harness imports normal credentials without provider-egress isolation | Retain them only as an accepted temporary exception with explicit opt-in, acknowledgement, Bash environment-use denial, isolation, and residual-risk reporting | Accepted temporary exception |
| RV-12 | Coverage manifest fabricates labels instead of proving fixture execution | Generated positive and negative labels are not linked to executed cases | Register stable IDs on executable fixtures and fail when a declared case was not executed | Resolved |
| RV-13 | Installed validation proves paths, not artifact equivalence | Installed modules can differ from source while path checks still pass | Compare installed module content with source and execute the same adversarial fixture corpus against both | Resolved |
| RV-14 | Aggregate result hides relevant stages | Only one highest-risk stage is retained, including when later stages have equal risk | Emit bounded, redacted per-stage findings and aggregate all policy-relevant edges and sinks | Resolved |
| RV-15 | Event schema is too rigid for harmless runtime evolution | Unknown observational metadata and future effort values can reject an otherwise understood event | Keep execution-affecting input strict while tolerating bounded observational top-level extensions conservatively | Resolved |
| RV-16 | External side effects can be autonomous | GitHub comments, issues, and similar externally persisted actions can be allowed in bypass mode | Mark externally persisted effects explicitly and always return `ask` | Resolved |
| RV-17 | Formatting gate reports a trailing blank line | `git diff --check` reports `tests/command-guard/helpers.mjs` | Remove the whitespace defect and retain the diff check as a gate | Resolved |

## Accepted temporary exception for live smoke

The operator explicitly approved retaining normal Claude provider credentials
in the opt-in live smoke for the current remediation. This is an accepted
temporary residual risk, not a closed finding and not evidence that the smoke
is safe for arbitrary prompts or commands.

The minimum compensating controls are:

- live execution remains disabled unless separately and explicitly requested;
- a dedicated acknowledgement confirms that normal provider credentials will
  enter the isolated model process;
- the command guard denies Bash references to provider-control-plane
  credential variables and denies environment-dump or equivalent discovery
  forms;
- the test home and writable paths remain isolated and runtime mounts remain
  read-only where supported;
- live targets remain synthetic, loopback, or disposable;
- output and retained artifacts are scanned for synthetic markers and known
  provider variable names without reading or comparing the provider values;
- test output states that provider egress remains available and that the
  controls reduce, but do not eliminate, exfiltration risk.

Disposable credentials or provider-egress allowlisting remain the preferred
future replacement. They are not prerequisites for this remediation because
the operator accepted the temporary exception above.

## Closure criteria

The final independent review verified every closure criterion below for the
final head, subject to the accepted RV-11 exception:

1. Every open blocker has an executable red regression and a reviewed fix.
2. The complete source suite, branch coverage gate, mutation gate, content
   validation, and formatting checks pass.
3. The installed Nori artifact is content-equivalent for the security-critical
   modules and passes the same adversarial corpus.
4. Launcher failure paths are demonstrated to block before execution.
5. The explicitly acknowledged live smoke passes under the approved exception
   and reports its residual risk.
6. ADR-004 and user-facing documentation describe the implemented behavior,
   not the superseded behavior.
7. A new independent reviewer inspects the patch and records the final
   disposition of every finding.

This authorization was valid for the reviewed commit at the time. It is
superseded by the 2026-07-28 re-review below; repository integration now
requires another independent disposition.

## Verified remediation evidence

The final independent reviewer inspected the remediated head and reproduced
the following evidence:

- Stable fixture IDs execute every reproduced regression and fail on orphan,
  undeclared, duplicate, or unexecuted cases.
- The source gate passes 87 active tests plus one intentional mutation-only
  skip, 100 percent line/function/branch coverage, four deterministic property
  seeds, and 11 killed security mutations.
- Source-to-installed validation byte-compares every security-critical
  launcher, entrypoint, and module, then executes the same 27-fixture review
  corpus against both forms.
- Launcher tests prove missing runtime, missing artifact, timeout, crash,
  malformed output, and unexpected stdout block before command execution.
- The complete package gate, architecture tests, static smoke contract,
  installed validation, and `git diff --check` pass.
- The explicitly acknowledged Debian WSL2 live smoke passes and reports that
  normal provider credentials entered the Claude process while provider egress
  remained open. This is evidence for the compensating controls, not closure
  of RV-11.

## 2026-07-28 re-review disposition

A later review of PR head `9980054` reproduced six semantic gaps that were not
represented by the green suite. PowerShell expression evaluation also escaped
the guard in normal mode, so line and branch coverage did not establish the
claimed authorization boundary. The previous merge authorization is therefore
withdrawn.

The remediation adds executable regressions and tightens the finite grammar.
The statuses below mean the local implementation satisfies the reproduced
case; they do not replace independent verification of the resulting head.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-03 | Execution-control assignments remained allowlisted | `GIT_ASKPASS` and an arbitrary `KUBECONFIG` could introduce external helpers | Restrict in-command assignments to credential transports and the named AWS profile reference | Remediated; independent verification pending |
| RV-04 | Curl inline file sources escaped detection | `--data=@file` and related attached forms were autonomous in bypass mode | Parse separated, equals-attached, and compact curl values and deny every local request-file source | Remediated; independent verification pending |
| RV-08 | Raw Kubernetes API bypassed sensitive-resource detection | `kubectl get --raw=.../secrets/...` was a narrow read | Deny raw API endpoints before resource classification | Remediated; independent verification pending |
| RV-18 | PowerShell arguments evaluated nested commands | A read cmdlet containing `(Remove-Item ...)` was allowed in every mode | Reject unquoted expression, type, and call delimiters before token classification | Remediated; independent verification pending |
| RV-19 | SSH option denylist omitted executable hooks | `KnownHostsCommand` executed a local helper while the remote read was allowed | Replace the denylist with a closed literal transport-option schema | Remediated; independent verification pending |
| RV-20 | Kubernetes streams were not finite | `logs --follow`, `get --watch`, and disabled pagination were allowed | Deny enabled follow/watch/raw streams and invalid or zero chunk sizes | Remediated; independent verification pending |

The executable fixture ledger now includes the new stable IDs, and the direct
security suite covers spelling and boundary variants. A new independent
reviewer must inspect the patch, reproduce the cases against source and
installed form, run the complete gates, and record the resulting commit and
verdict before merge.

## 2026-07-28 third review disposition

A subsequent self-review of published head `e0aa2c3` found four additional
credential-boundary gaps despite green structural coverage and mutation gates.
The same agent that implemented the preceding changes performed this review,
so it is explicitly not an independent disposition and cannot authorize merge.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-21 | Catalogued literal spellings escaped credential detection | Curl OAuth bearer, compact/equal Basic Auth, generic Authorization schemes, and Redis `--pass` returned autonomous `allow` | Recognize every accepted separated, equals-attached, and compact literal form and retain exact transport metadata | Remediated; independent verification pending |
| RV-22 | Identity metadata replaced the actual transport | `OPS_CREDENTIAL_IDENTITY` became a `VARIABLE` span, allowing an approved Authorization binding to authorize Cookie or Basic Auth | Exclude the non-secret identity marker and bind the first actual client credential transport | Remediated; independent verification pending |
| RV-23 | Curl route and TLS overrides did not change the bound domain | An approved origin could be rerouted with `--resolve` and `-k`, then reuse the active binding | Deny proxy, name-resolution, and insecure-peer overrides that the domain record cannot represent | Remediated; independent verification pending |
| RV-24 | Kubernetes context hid an overridden server | `--server` plus insecure TLS was treated as a safe read in the named context | Consume a closed option schema and reject endpoint, credential, trust, impersonation, plugin, and unknown options | Remediated; independent verification pending |

The TDD red phase reproduced autonomous literals, cross-transport reuse, curl
rerouting, and Kubernetes server replacement. The corrected critical gate now
runs 98 active tests plus one intentional mutation-only skip, retains 100
percent line/function/branch coverage, kills all 11 registered mutations, and
executes 37 stable review fixtures. The complete package, installed-artifact,
schema, workflow, static smoke, content, and Python gates passed in Debian WSL2
with the SHA-256-verified official user-local Node.js `v24.17.0`; the Debian
system Node remains unchanged. Independent review of the final published tree
is still required.

## 2026-07-28 fourth independent review disposition

An independent reviewer inspected PR head `f0d56f7` without prior task
history, reviewed the full `18127ac..f0d56f7` range, ran adversarial cases
against the real `analyzeCommand` entrypoint with Node.js `v24.17.0`, and used
a loopback HTTP server to compare classified and executed methods. The review
found that green structural coverage did not include client last-wins
precedence, two accepted credential spellings, or unbound remote route/config
controls. The PR was not ready to merge.

The remediation below was implemented with a witnessed RED/GREEN cycle. Its
status records local closure of each reproduced case and does not replace a
new independent verification of the resulting head.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-25 | Repeated curl methods hid the effective destructive request | `curl -X GET -X DELETE ...` returned `allow/SAFE_READ_ONLY` while loopback observed `DELETE` | Reject multiple method selectors across short, long, equals, compact, and mixed aliases before risk derivation | Remediated; independent verification pending |
| RV-26 | Accepted cookie and Redis spellings escaped literal detection | Curl `-b/--cookie` and Redis `-a"secret"` returned `allow` with no credential metadata | Detect separated, equals-attached, compact, and quoted cookie/password forms and preserve `COOKIE` or `FLAG` transport | Remediated; independent verification pending |
| RV-27 | Repeated Kubernetes selectors broke audited context binding | Later `--context` or `--namespace/-n` values could replace the first audited value | Reject duplicate singleton context and namespace alias groups before closed-schema classification | Remediated; independent verification pending |
| RV-28 | AWS route and trust controls were outside the binding | Endpoint, alternate CA, insecure TLS, unsigned, debug, and external-input controls remained autonomous | Deny unrepresented route/trust/auth/diagnostic/input overrides and bind a named `AWS_PROFILE` assignment | Remediated; independent verification pending |
| RV-29 | Docker remote transport and external configuration looked local | `--host`, `-H`, `--connection`, and `--config` reads returned a local binding | Deny unmodelled remote/config selectors while retaining one literal `--context` | Remediated; independent verification pending |
| RV-30 | Dynamic HTTP origins were authorized before expansion | `curl https://$OPS_TARGET/...` returned a narrow autonomous read | Require a literal origin and deny variables, globs, and brace syntax before URL parsing | Remediated; independent verification pending |

Seven targeted assertions failed on the unsafe decisions before production
changes. After the minimal parser and redaction changes, all 37 targeted tests
passed. Stable fixture IDs RV-25 through RV-30 execute the same cases against
source and installed form; final full-gate and installed-artifact evidence is
recorded only after it is freshly observed.

Fresh local remediation evidence on the resulting worktree records 103 active
Node tests passing plus one intentional mutation-only skip, 100 percent
line/function/branch coverage, four deterministic property seeds, and all 11
registered security mutations killed. The complete package, content,
architecture, schema, workflow, Python, Bash, and host PowerShell syntax gates
passed. An isolated local Nori installation registered all 12 subagents and 24
skills; source-to-installed semantic comparison passed and the installed guard
executed all 44 stable review fixtures. No model was started and no Claude
model-provider credential was loaded; the Nori CLI used its own existing
authentication context for the local install. A new
independent review of the resulting commit remains required before merge.

## 2026-07-28 fifth independent review disposition

A second independent re-review of the remediated worktree found four remaining
authorization-boundary gaps. The reviewer exercised the real policy entrypoint
and approval lifecycle rather than inferring behavior from structural coverage.
The reviewed worktree was not ready to merge.

<!-- markdownlint-disable MD013 -->

The remediation below was implemented through executable RED/GREEN cases. Its
status records local closure only; a new independent reviewer must verify the
resulting commit before merge.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-31 | One approved transport authorized an additional literal transport | An active Authorization binding allowed the same curl call to add a new Cookie because only the first detected span selected the transport | Deny any command containing more than one distinct literal credential transport before binding lookup | Remediated; independent verification pending |
| RV-32 | First parsed values diverged from shell/client last-wins behavior | Repeated `AWS_PROFILE`, `OPS_CREDENTIAL_IDENTITY`, and Redis host selectors audited the first value while execution used the last | Reject repeated allowlisted assignment names and every Redis host, port, database, password, or user singleton alias group before derivation | Remediated; independent verification pending |
| RV-33 | Separated Docker short host option escaped the route boundary | `docker -H tcp://attacker.invalid:2375 ps` was classified as a local safe read | Treat exact separated `-H` as the same prohibited remote-host selector as compact and equals spellings | Remediated; independent verification pending |
| RV-34 | Mixed quote concatenation left credential suffixes visible | Curl Cookie and Redis password tokens built from adjacent quoted fragments retained the later raw fragment after redaction | Supplement semantic detection with Bash lexer raw-token spans and prefer the complete outer value span over overlapping inner matches | Remediated; independent verification pending |

The RED run failed in all five affected assertions: cross-transport approval
reuse, complete mixed-quote redaction, installed review-fixture semantics,
repeated effective-value selectors, and separated Docker `-H`. The corrected
targeted suite passed all 66 cases. Stable fixture IDs RV-31 through RV-34
cover six source-to-installed commands, including separate assignment and
Redis precedence variants. Final full-gate and installed-artifact evidence is
recorded only after fresh verification.

Fresh local remediation evidence records 106 active Node tests passing plus
one intentional mutation-only skip, 100 percent line/function/branch coverage,
four deterministic property seeds, and all 11 registered security mutations
killed. The complete package, content, architecture, schema, workflow, Python,
Bash, and host PowerShell syntax gates passed. An isolated Nori installation
registered all 12 subagents and 24 skills; security-critical artifacts matched
source byte-for-byte and the installed guard passed all 50 review fixtures.
No Claude process or model-provider credential was loaded. This evidence does
not replace the required independent verification of the resulting commit.

## 2026-07-28 sixth independent review disposition

A fresh independent reviewer inspected the complete uncommitted delta from
`origin/main`, read the command, binding, audit, and approval flow, and executed
adversarial lifecycle cases through the real entrypoints. RV-31, RV-33, and
RV-34 were verified closed. RV-32 was only partially closed because unique
Redis selectors and trust state were still absent from the approval domain.
The reviewed worktree was not ready to merge.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-35 | Redis trust could be weakened after approval | A credential approved with `--tls` was reused with `--tls --insecure` and returned `ALLOW_APPROVED_CREDENTIAL_BINDING` | Consume a closed Redis option schema and deny insecure verification, alternate trust/client inputs, SNI, URI/socket routing, cluster redirects, stdin sources, special modes, and unknown options | Remediated; independent verification pending |
| RV-36 | Redis approval omitted effective port, database, and user | A binding approved for port 6379, database 0, and user `app` was reused for port 6380, database 1, and user `admin` | Build one canonical non-secret environment from transport, host, port, database, and user with explicit defaults, and reuse the existing action identity, audit, and binding comparison | Remediated; independent verification pending |

<!-- markdownlint-enable MD013 -->

The TDD RED run reproduced `allow` for the TLS-to-insecure lifecycle, incorrect
reuse across Redis scope changes, and failing source-to-installed review
fixtures. The corrected targeted suite passed all 44 cases. Fresh local full
verification records 108 active Node tests passing plus one intentional
mutation-only skip, 100 percent critical line/function/branch coverage, four
deterministic property seeds, and all 11 registered security mutations killed.
The complete package, content, architecture, schema, workflow, Python, Bash,
and host PowerShell syntax gates passed. A temporary Nori installation
registered all 12 subagents and 24 skills; security-critical files matched
source byte-for-byte and all 52 installed review fixtures passed. No Claude
process or model-provider credential was loaded. A new independent review of
the resulting commit remains required before merge.

## 2026-07-29 seventh independent review disposition

A new independent review of the complete worktree found four remaining gaps in
the command catalogue and in the evidence gate. The reviewer reproduced
incomplete Redis command parsing, autonomous mutable HTTP effects, and the
absence of catalogue coverage and mutation witnesses. The reviewed worktree
was not ready to merge.

The remediation below used executable RED/GREEN tests. Its status records
local closure only and does not replace independent verification of the
resulting tree.

<!-- markdownlint-disable MD013 -->

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-37 | Redis TTL semantics and trailing operands were incomplete | Non-positive `EXPIRE` was classified as a low-risk change and malformed or dynamic forms could reach the catalogue | Parse the complete literal `EXPIRE` and `PERSIST` grammars, classify zero or negative TTL as destructive, and reject invalid, dynamic, incomplete, or trailing operands | Remediated; independent verification pending |
| RV-38 | Redis client termination was parsed as a standalone verb | Valid `CLIENT KILL` forms denied while composite and unconsumed forms were not represented exactly | Accept only `CLIENT KILL <host:port>` or `CLIENT KILL ID <positive-int64>` and reject standalone `KILL`, unsupported filters, invalid bounds, and extra operands | Remediated; independent verification pending |
| RV-39 | Generic mutable HTTP calls remained autonomous in permissive mode | Uncatalogued `POST`, `PUT`, and `PATCH` could return `allow` in `bypassPermissions` | Classify mutable HTTP calls as disruptive external effects so native confirmation is mandatory in every permission mode | Remediated; independent verification pending |
| RV-40 | The catalogue was outside critical structural and mutation evidence | A green gate could omit catalogue branches and could accept a registered mutation without a dedicated semantic witness | Include `catalogue.mjs` in 100 percent line/function/branch thresholds, require registry equality for predicates, mutations, and witnesses, and add six exact catalogue mutations | Remediated; independent verification pending |

<!-- markdownlint-enable MD013 -->

The catalogue-inclusive gate initially failed at 96.39 percent lines, 91.77
percent branches, and 94.32 percent functions, proving the former evidence
gap. Registering the six new mutations without witnesses also failed the
registry test as intended. Behavior-bearing fixtures then closed every
catalogue branch, and all 17 mutations were killed by dedicated invariants.

Fresh local Node verification records 121 active tests passing plus one
intentional mutation-only skip, 100 percent critical line/function/branch
coverage including `catalogue.mjs`, four deterministic property seeds, and all
17 registered mutations killed. Stable fixture IDs RV-37 through RV-40 extend
the source-to-installed review corpus to 57 cases. The complete package,
content, architecture, schema, workflow, Python, Bash, and host PowerShell
syntax gates passed. A temporary Nori installation registered all 12 subagents,
24 agent skills, and 20 slash commands; security-critical scripts matched
source byte-for-byte and all 57 installed review fixtures passed. The temporary
HOME was removed, no Claude process was started, and no model-provider
credential was loaded. A subsequent independent read-only review is still
required before merge.

## 2026-07-29 eighth independent review disposition

A fresh independent review reproduced five remaining semantic and evidence
gaps. Curl remote-name flags could consume following body or upload options,
database clients could execute against a later selector than the audited one,
HTTP output files lacked a canonical local-effect binding, long Git branch
deletion aliases escaped destructive classification, and the mutation runner
counted any child failure as a killed mutant. The reviewed worktree was not
ready to merge.

The remediation below used witnessed RED/GREEN cycles. Its status records
local closure only and does not replace independent verification of the
resulting tree.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-41 | Curl remote-name arity hid body and upload semantics | `curl -O -d ...` returned `allow/LOW_RISK_CHANGE` while loopback observed `POST`; uploads could also be consumed | Parse curl with exact flag/value arity, derive effects only from consumed entries, and retain remote-name as a local sink | Remediated; independent verification pending |
| RV-42 | Repeated database selectors broke credential-domain binding | PostgreSQL/MySQL bound the first host or port although the client used a later value | Reject duplicate alias groups through closed client grammars and bind scheme, user, host, port, and database | Remediated; independent verification pending |
| RV-43 | HTTP sinks lacked canonical path binding and mandatory confirmation | Dynamic and arbitrary destinations could write files autonomously without an auditable local target | Normalize literal or allowlisted-root paths, record `METHOD path -> file:path`, and apply `FILE_WRITE + ALWAYS_ASK` in every mode | Remediated; independent verification pending |
| RV-44 | Long Git branch deletion aliases escaped destructive classification | `git branch --delete [--force]` fell through to `LOW_RISK_CHANGE` | Route every accepted branch form through one complete subgrammar and classify all deletion aliases as destructive | Remediated; independent verification pending |
| RV-45 | Mutation witnesses were not baseline-proven or failure-typed | Any nonzero child exit, including import errors and crashes, was counted as a killed mutant | Execute every witness against pristine source first and accept a kill only for exit `42` plus the exact matching assertion marker | Remediated; independent verification pending |

The RED evidence reproduced autonomous remote-name POST classification,
unbound and dynamic sinks, repeated database selector acceptance, low-risk long
branch deletion, and a crashing mutation incorrectly counted as killed. Stable
fixtures RV-41 through RV-44 execute source and installed operational behavior;
RV-45 remains repository-only evidence because Nori does not install the
development mutation harness. The fresh native and Debian package gates pass
167 active tests with zero skips, 100 percent line/function/branch coverage
for every critical module, four fixed property seeds, and 23 of 23
baseline-proven typed mutations. A fresh isolated Nori install, without Claude
or provider credentials, registered 12 subagents, 24 project skills, and 20
slash commands; all 61 installed fixtures passed and every source script
matched its installed counterpart byte for byte. Independent verification of
the completed tree remains pending.

## 2026-07-29 ninth independent review disposition

The post-remediation read-only review confirmed RV-41 through RV-45, then
reproduced four adjacent gaps. A curl `Host` header could reuse an approved
credential against a changed authority, PostgreSQL could inherit unaudited
`PGHOST`/`PGPORT`/`PGUSER` selectors, tilde expansion produced an incorrect
local audit target, and curl header/cookie/trace output sent to `-` was recorded
as a file or remained autonomous.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-46 | HTTP authority headers escaped origin binding | Changing only `Host` after approval reused the active credential binding | Parse literal headers and deny `Host`, `:authority`, dynamic, file-backed, or malformed fields | Remediated; independent verification pending |
| RV-47 | PostgreSQL inherited an unaudited environment domain | `PGHOST`, `PGPORT`, and `PGUSER` changed while the action identity retained defaults | Require a complete explicit network domain and reject socket or implicit-selector operation | Remediated; independent verification pending |
| RV-48 | Tilde output expansion produced a false local target | `~/report.json` was audited beneath the hook `cwd` although the shell expands home | Reject every tilde-prefixed output operand | Remediated; independent verification pending |
| RV-49 | Header-bearing stdout was mistaken for a file or narrow output | Include/head and `-D -`, `-c -`, or trace output exposed headers while `-` became a fake file path | Model `-` as stdout and apply `SENSITIVE_OUTPUT + ALWAYS_ASK` to header-bearing output | Remediated; independent verification pending |

The new RED cases failed through the real policy and binding entrypoints before
implementation. The fresh local Node gate now passes 174 active tests with
zero skips, 100 percent critical line/function/branch coverage, four fixed
property seeds, and 27 of 27 baseline-proven typed mutations. Stable fixtures
RV-46 through RV-49 extend the source and installed corpus to 65 cases. A fresh
isolated Nori install registered 12 subagents, 24 project skills, and 20 slash
commands; all 65 installed fixtures passed and every source script matched its
installed counterpart. Another independent read-only review remains pending.

## 2026-07-29 tenth independent review disposition

The next independent read-only review confirmed RV-46 through RV-49, then
reproduced three adjacent domain and credential-disclosure gaps. An explicit
PostgreSQL command could still be rerouted or have its trust boundary changed
through libpq environment inputs, MySQL special host aliases could select a
local socket despite an audited port, and curl traces could expose a literal
credential to stdout or a file.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-50 | PostgreSQL environment escaped the explicit domain | `PGHOSTADDR`, service, option, password-file, and trust variables could alter the effective route or trust behind explicit selectors | Reject the closed set of route, service, password-file, option, TLS, GSS, channel-binding, and peer-trust variables before domain construction | Remediated; final independent verification pending |
| RV-51 | MySQL special hosts selected socket transport | `-h localhost` or `-h .` could ignore the audited network port and use a socket, including one selected by process environment | Reject both socket-selecting aliases while explicit TCP protocol selection remains outside the supported grammar | Remediated; final independent verification pending |
| RV-52 | Curl trace disclosed literal credentials | `--trace -`, `--trace %`, and file traces could emit authorization material while remaining confirmable or autonomous | Derive credential output/persistence modifiers from the closed curl parser and deny literal credential traces with the specific redacted reason | Remediated; final independent verification pending |

The new RED cases failed through the policy and credential-binding entrypoints
before implementation. The completed deterministic gate passes 179 active
tests with zero skips, 100 percent critical line/function/branch coverage,
four fixed property seeds, and 30 of 30 baseline-proven typed mutations.
Stable fixtures RV-50 through RV-52 extend the source and installed corpus to
68 cases. Debian/WSL package validation and host PowerShell syntax validation
pass. A fresh isolated installation with observed Nori `0.31.0` and Node.js
`v24.18.0`, without Claude or provider credentials, registered 12 subagents,
24 project skills, and 20 slash commands; all 68 installed fixtures passed and
security-critical scripts matched source byte for byte. These versions are
evidence only, not package requirements. A final independent read-only review
of the completed tree remains pending.

## 2026-07-29 eleventh independent review disposition

The final-review attempt confirmed RV-50 through RV-52, then found that the
libpq environment deny set still omitted six current authentication, TLS, and
GSS variables. Two obsolete underscore spellings for TLS protocol versions
did not match the real environment names, allowing an already approved
PostgreSQL binding to execute under a changed trust or credential-delegation
context.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-53 | Direct SSL negotiation was not bound | `PGSSLNEGOTIATION` preserved autonomous approved reuse | Reject the exact current variable and protect it with an installed fixture plus dedicated mutation witness | Remediated; final independent verification pending |
| RV-54 | Authentication requirement was not bound | `PGREQUIREAUTH` preserved autonomous approved reuse | Reject the exact current variable and protect it with an installed fixture plus dedicated mutation witness | Remediated; final independent verification pending |
| RV-55 | Client certificate mode was not bound | `PGSSLCERTMODE` preserved autonomous approved reuse | Reject the exact current variable and protect it with an installed fixture plus dedicated mutation witness | Remediated; final independent verification pending |
| RV-56 | Minimum TLS version used an invalid spelling | `PGSSLMINPROTOCOLVERSION` was absent while an underscore spelling was inert | Replace the inert name with the current exact variable and add lifecycle, installed, and mutation evidence | Remediated; final independent verification pending |
| RV-57 | Maximum TLS version used an invalid spelling | `PGSSLMAXPROTOCOLVERSION` was absent while an underscore spelling was inert | Replace the inert name with the current exact variable and add lifecycle, installed, and mutation evidence | Remediated; final independent verification pending |
| RV-58 | GSS credential delegation was not bound | `PGGSSDELEGATION` preserved autonomous approved reuse | Reject the exact current variable and protect it with an installed fixture plus dedicated mutation witness | Remediated; final independent verification pending |
| RV-59 | Minimum wire-protocol version was not bound | Current PostgreSQL documentation exposes `PGMINPROTOCOLVERSION` as a connection parameter default | Reject the exact current variable and protect it with an installed fixture plus dedicated mutation witness | Remediated; final independent verification pending |
| RV-60 | Maximum wire-protocol version was not bound | Current PostgreSQL documentation exposes `PGMAXPROTOCOLVERSION` as a connection parameter default | Reject the exact current variable and protect it with an installed fixture plus dedicated mutation witness | Remediated; final independent verification pending |

The eight real-entrypoint lifecycle cases and source fixtures failed before the
implementation correction and passed afterward. Each variable now has its own
exact one-site mutation and typed witness, preventing a future typo or removal
from being hidden behind the aggregate environment predicate. The completed
native and Debian/WSL package gates pass 187 active tests with zero skips, 100
percent critical line/function/branch coverage, four fixed property seeds, and
38 of 38 baseline-proven typed mutations. RV-53 through RV-60 extend the
source and installed corpus to 76 cases. A fresh isolated installation with
observed Nori `0.31.0` and Node.js `v24.18.0`, without Claude or provider
credentials, registered 12 subagents, 24 project skills, and 20 slash commands;
all 76 installed fixtures passed and security-critical scripts matched source
byte for byte. These versions remain evidence only, not requirements. One more
independent read-only review of this completed tree remains pending.

## 2026-07-29 final independent verification

The final read-only review found no remaining Critical or Important issue and
returned **Ready to merge: yes**. It independently exercised one approved
PostgreSQL binding against all 29 current environment variables in the guarded
route, service, authentication, TLS, GSS, channel-binding, peer, and protocol
negotiation set; every altered context denied. Explicit command-line host,
port, database, and user selectors retained precedence over their benign
environment defaults. No synthetic secret appeared in audit output.

The reviewer also confirmed individual RV-53 through RV-60 installed fixtures,
mutations, and witnesses; 38 of 38 mutations were killed, all 76 installed
fixtures passed, and 19 installed security-critical scripts were byte-equivalent
to source. `git diff --check origin/main` passed. No Claude process, real
credential, or runtime/model pin was introduced or used. `PGSYSCONFDIR` cannot
alter the accepted domain because service selectors and connection strings in
the database selector remain outside the closed grammar.

## 2026-07-29 twelfth independent review disposition

A subsequent independent review reproduced eight adjacent authorization gaps
despite the prior green gate. Credential reuse followed the composition's
highest-risk stage instead of the literal credential consumer; seven command
families also left options, nested verbs, sinks, or control effects outside
their effective analysis.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-61 | Credential binding followed aggregate risk | A higher-risk Kubernetes stage supplied the binding for a later authenticated HTTP stage, permitting reuse against a changed HTTP origin | Project domain, family, and target class from the exact credential-bearing stage | Remediated; independent verification pending |
| RV-62 | MongoDB accepted multiple execution sources | Repeated `--eval`, file, positional script, and shell forms escaped the first-script analysis | Consume exactly one URI and one inline `--eval`; deny every extra source or option | Remediated; independent verification pending |
| RV-63 | IP batch files inherited read authorization | Separated, equals-attached, and compact batch aliases could load opaque commands while a read object remained visible | Reject every batch alias while preserving literal brief reads | Remediated; independent verification pending |
| RV-64 | Remote transfers accepted local executors and opaque configuration | `scp`/`sftp` execution, configuration, proxy, server, and batch controls were ignored | Consume closed client-specific transport options and exact transfer operands | Remediated; independent verification pending |
| RV-65 | Packet-capture sinks and executors were unmodelled | `-w` remained read-only and post-rotate/input-file controls were accepted | Model resolved capture files as mandatory-confirmation writes and deny executors, opaque inputs, dynamic sinks, and unknown options | Remediated; independent verification pending |
| RV-66 | `ctr` nested image effects were flattened | Pull, import, and remove were classified from the parent `images` noun | Parse exact nested verbs and classify reads, changes, and destructive removals separately | Remediated; independent verification pending |
| RV-67 | Git read verbs accepted output and external execution controls | `git diff --output` wrote autonomously while external-diff controls remained eligible as reads | Close read options, bind resolved output effects, and deny external diff/textconv execution | Remediated; independent verification pending |
| RV-68 | `dmesg` control actions inherited display risk | Clear/read-clear and console controls combined with a level selector remained safe reads | Consume all display/control options and classify clear as destructive and console controls as disruptive | Remediated; independent verification pending |

The eight regressions were observed RED through real policy or binding lifecycle
entrypoints before remediation. RV-61 through RV-68 are executable corpus
fixtures, with the RV-61 lifecycle additionally proving that an approved HTTP
origin cannot be reused for another origin behind a higher-risk preceding
stage. Each protection has one exact one-site mutation and typed witness. The
final source and Debian/WSL package gates pass 204 tests with zero skips, 100
percent critical line/function/branch coverage, four fixed property seeds, and
46 of 46 baseline-proven typed mutations. A temporary isolated Nori `0.31.0`
install registered 12 subagents, 24 skills, and 20 slash commands; installed
semantic validation and all 84 fixtures passed. Host PowerShell syntax
validation also passed. Observed versions are evidence only and remain
unpinned. One fresh independent read-only verification remains pending before
merge.

## 2026-08-01 thirteenth independent review disposition

A fresh review of the complete PR reproduced three residual gaps behind the
RV-61, RV-64, and RV-65 fixes. A literal credential in an earlier stage still
borrowed the last catalogued consumer's domain, accepted remote-transfer
selectors did not participate in the audit identity, and packet stdout plus
duplicate aliases were not represented exactly.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-69 | Literal ownership still followed the last consumer | An approved first-stage HTTP literal followed by a stable `gh` stage reused against a changed HTTP origin | Preserve lexical stage intervals, map all sensitive spans to exactly one stage, and require that exact stage to be the catalogued consumer | Remediated; independently verified |
| RV-70 | Remote-transfer identity omitted accepted selectors | Port, user, ProxyJump, bandwidth, and identity-file changes retained an incomplete host-only environment | Build one canonical identity from explicit user, host, port, jump route, Kbit/s limit, and identity file; reject duplicate aliases and implicit users | Remediated; independently verified |
| RV-71 | Packet stdout was treated as a filesystem sink | `-w -` was denied or resolved as a local file rather than sensitive packet output | Classify it as `SAFE_READ_ONLY + SENSITIVE_OUTPUT + RESOURCE_INTENSIVE + ALWAYS_ASK` with target `stdout:pcap` | Remediated; independently verified |
| RV-72 | Capture alias uniqueness was incomplete | `-s` plus `--snapshot-length` overwrote the earlier value and retained read authorization | Group interface, count, snapshot-length, and sink aliases by semantic role and deny every repetition | Remediated; independently verified |

The new lifecycle and parser tests were observed RED before implementation.
The completed deterministic gate passes 215 tests with zero skips, 100 percent
critical line/function/branch coverage, four fixed property seeds, and 50 of
50 baseline-proven typed mutations. RV-69 through RV-72 extend the source and
installed corpus to 88 cases. The package and installed-artifact gates and one
fresh independent read-only review remain required before merge. Runtime and
model versions remain unpinned.

## 2026-08-01 fourteenth independent review disposition

The independent review of the RV-69 through RV-72 remediation found no new
Critical issue, but reproduced two Important gaps. Literal-stage validation
still trusted an executable-name allowlist rather than the effective catalogue
result, and the accepted SSH address-family aliases were neither a singleton
group nor part of the remote-transfer identity.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-73 | Literal ownership did not prove effective consumption | `SSHPASS=<literal> sudo ...` without `-S` created and later reused a `PRIVILEGE/local` binding | Require the owning catalogue result to declare credential consumption and accept the detected transport plus client-specific variable selector; deny nominal or cross-client consumers | Remediated; independently verified |
| RV-74 | Remote address-family aliases were unaudited | `-4 -6`, `-4 -o AddressFamily=inet6`, and repeated `AddressFamily` were accepted under the same host-only environment | Group `-4`, `-6`, and `AddressFamily` as one selector, deny repetition/conflict, and include the accepted family in the canonical environment | Remediated; independently verified |
| RV-75 | Address-family identity retained input case | `AddressFamily=INET` and `AddressFamily=inet` were both accepted but produced distinct environments | Normalize the accepted value before identity construction and protect it with a stable fixture plus mutation witness | Remediated; independently verified |

The cases were observed RED through the real policy or binding lifecycle
before remediation. The deterministic source gate now passes 220 tests with
zero skips, 100 percent critical line/function/branch coverage, four fixed
property seeds, and 53 of 53 baseline-proven typed mutations. RV-73 through
RV-75 extend the shared source/installed corpus to 91 cases. The fresh Debian/WSL
package and installed-artifact validation passed with observed Node.js
`v24.17.0`; a fresh independent read-only verification remains required before merge.
Runtime and model versions remain unpinned.

## 2026-08-01 final independent verification

The second read-only review of the completed delta found no remaining Critical,
Important, or Minor issue and returned **Ready to merge: yes**. It independently
reproduced the credential lifecycle for nominal and cross-client consumers,
the remote address-family conflict and case-normalization matrix, and the
installed fixture corpus. The final Windows and Debian/WSL gates pass 220 tests
with zero skips, 100 percent critical line/function/branch coverage, 53 of 53
typed mutations, and all 91 installed fixtures. Diff and secret scans found no
real credential or new Claude Code, Nori, Node.js, or model pin.

## 2026-08-03 fifteenth independent review disposition

A subsequent independent review found four Important catalogue-closure gaps.
Prefix recognition still permitted executable or output controls that were not
represented in the risk, destination, or audit identity. The reproductions
were added through real policy entrypoints before their parsers were changed.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-76 | Git push did not consume its complete invocation | Remote controls such as `--exec` could be authorized while audit omitted the effective repository | Parse push options, repository, and bounded refspecs; reject executors, opaque server options, duplicates, unknowns, and malformed forms; bind repository and refspec targets | Remediated; independent verification pending |
| RV-77 | Operational log reads could become unbounded streams | Journal and container `--follow`/`-f` forms inherited bounded read authorization | Use separate closed finite grammars, reject every follow spelling and unconsumed control, require explicit bounds and one container target, and preserve journal maintenance risk | Remediated; independent verification pending |
| RV-78 | GitHub CLI read verbs accepted unmodelled output controls | Watch, excessive limits, and broad Actions logs could execute as narrow autonomous reads | Apply one closed schema per supported noun/verb, enforce output bounds, reject watch, and mark broad run logs sensitive, resource-intensive, and always-ask | Remediated; independent verification pending |
| RV-79 | Nominal Kubernetes dump flag inherited summary authorization | `kubectl cluster-info --dump` was accepted as the bounded cluster summary | Remove the nominal flag from the closed option schema while retaining plain `cluster-info` | Remediated nominal spelling; superseded by RV-81 |

The deterministic source gate now passes 232 tests with zero skips, 100 percent
critical line/function/branch coverage, four fixed property seeds, and 61 of
61 pristine-baseline typed mutations. Eight stable executable fixtures cover
the four findings across source and installed-corpus gates. Version remains
`0.11.0`; Claude Code, Nori, Node.js, and model selection remain unpinned. A
fresh package validation and independent read-only review of this resulting
head are still required before merge.

## 2026-08-03 sixteenth independent review disposition

The independent review of the RV-76 through RV-79 remediation confirmed the
nominal cases, then reproduced one Critical, two Important, and one Minor
adjacent gap. The passing structural gates had protected the spellings they
registered but did not yet represent the effective executable transport,
repository domain, positional subcommand, or read target.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-80 | Git repository operand could execute a remote helper | `git push 'ext::/tmp/review-helper %S repo' main` was autonomous in `bypassPermissions` | Reject every literal `scheme::` external remote-helper transport in positional and `--repo` forms | Remediated; final independent verification pending |
| RV-81 | The real Kubernetes dump syntax remained autonomous | `kubectl cluster-info dump` and its `k3s kubectl` form inherited narrow summary authorization | Reject every positional operand after `cluster-info`; retain only the bounded summary grammar | Remediated; final independent verification pending |
| RV-82 | Implicit GitHub repositories shared one reusable domain | Credential-bearing reads in different working directories both bound to `local` | Require an explicit `--repo` or `repo view` operand for every accepted GitHub read; implicit selection denies before binding | Remediated; final independent verification pending |
| RV-83 | Container log target was discarded | The closed parser found the container, but integration recorded `target=local` | Preserve the parsed container target and context in policy, audit, source fixtures, and installed fixtures | Remediated; final independent verification pending |

The new cases were observed RED through real policy entrypoints before the
corrections. RV-80 through RV-83 now have stable source/installed fixtures;
three new exact mutations cover the added boundaries, and the RV-79 mutation
now attacks the real positional dump rejection rather than the nominal
`--dump` spelling. The deterministic source and Debian/WSL package gates pass
235 tests with zero skips, 100 percent critical line/function/branch coverage,
four fixed property seeds, 64 of 64 pristine-baseline typed mutations, and all
103 installed fixtures. Markdown, spelling of changed documents, schema, and
CI workflow validation also pass. One fresh independent read-only verification
remains required before merge.

## 2026-08-03 seventeenth independent review disposition

The final-review attempt confirmed RV-80 through RV-83, then reproduced one
remaining Critical transport gap. Git can execute a remote helper not only for
`scheme::address`, but also for an unknown `scheme://address` URL.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-84 | Unknown Git URL schemes invoked external helpers | Positional and `--repo=helper://opaque-address` pushes were autonomous in `bypassPermissions` | Allow only native `file`, `git`, `ssh`, `http`, and `https` URL transports; reject every other scheme and protect both forms with fixtures and a typed mutation | Remediated; final independent verification pending |

The two real policy-entrypoint cases were observed RED before the finite scheme
allowlist and GREEN afterward. RV-84 adds source and installed fixtures plus a
dedicated exact mutation for the URL-scheme boundary. The deterministic source
and Debian/WSL package gates pass 236 tests with zero skips, 100 percent
critical line/function/branch coverage, four fixed property seeds, 65 of 65
pristine-baseline typed mutations, and all 105 installed fixtures. Markdown,
spelling of changed documents, schema, and CI workflow validation also pass.
One fresh independent read-only verification remains required before merge.

## 2026-08-03 eighteenth independent review disposition

The independent review of RV-84 confirmed unknown URL schemes, `scheme::`
helpers, lowercase native transports, SCP-like repositories, bindings, and
installed behavior. It then reproduced one Critical case-sensitivity gap: Git
preserves the URL scheme when selecting a remote-helper executable.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-85 | Case-altered schemes invoked distinct helpers | Positional `HTTPS://...` and `--repo=HtTpS://...` pushes were autonomous while Git selected case-distinct helpers | Require an exact-lowercase native scheme; protect positional and both `--repo` forms with source/installed fixtures and a typed mutation | Remediated; final verification pending |

The real policy-entrypoint cases were observed RED before removing case
normalization and GREEN afterward. The deterministic source and Debian/WSL
package gates pass 237 tests with zero skips, 100 percent critical
line/function/branch coverage, four fixed property seeds, 66 of 66
pristine-baseline typed mutations, and all 108 installed fixtures. Markdown,
spelling of changed documents, schema, and CI workflow validation also pass.
One fresh independent read-only verification remains required before merge.

## 2026-08-03 nineteenth independent review disposition

The independent review of RV-85 confirmed case-sensitive native URL schemes,
all three repository spellings, lowercase transports, SCP-like repositories,
bindings, fixtures, mutations, and installed behavior. Its adjacent search then
reproduced one Critical explicit-helper gap: Git accepts a helper name beginning
with a digit before the `::` delimiter.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-86 | Digit-prefixed `::` invoked an external helper | Positional, `--repo=`, and `--repo VALUE` forms of `1helper::opaque-address` were autonomous while Git selected `git-remote-1helper` | Reject every repository containing `::`, independent of helper grammar; protect all three forms with source/installed fixtures and the transport mutation | Remediated; final verification pending |

The three real policy-entrypoint cases were observed RED before replacing the
partial scheme regex and GREEN afterward. The deterministic source and
Debian/WSL package gates pass 237 tests with zero skips, 100 percent critical
line/function/branch coverage, four fixed property seeds, 66 of 66
pristine-baseline typed mutations, and all 111 installed fixtures. Markdown,
spelling of changed documents, schema, and CI workflow validation also pass.
One fresh independent read-only verification remains required before merge.

## 2026-08-03 twentieth independent review disposition

The independent review of RV-86 confirmed all `::` forms, case-sensitive URL
schemes, lowercase native transports, SCP-like and local addresses, bindings,
fixtures, mutations, and installed behavior. Its adjacent search then
reproduced one Critical destination-resolution gap: a named Git remote can be
rewritten by repository configuration before Git selects its transport.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-87 | Named remote hid its effective address and helper | `origin` and `review` were autonomous while configuration selected `git-remote-1helper` | Deny aliases and require an explicit literal address | Remediated; binding conclusion superseded by RV-88 |

The three policy-entrypoint aliases were observed RED before the literal-address
boundary and GREEN afterward. Parser collection now distinguishes repository
address validation from refspec validation. The deterministic source and
Debian/WSL package gates pass 238 tests with zero skips, 100 percent critical
line/function/branch coverage, four fixed property seeds, 67 of 67
pristine-baseline typed mutations, and all 114 installed fixtures. Markdown,
spelling of changed documents, schema, and CI workflow validation also pass.
One fresh independent read-only verification remains required before merge.

## 2026-08-03 twenty-first independent review disposition

The independent review of RV-87 confirmed named-remote denial and the complete
repository/refspec grammar, but reproduced a broader Critical Git
configuration boundary. Git applies `url.*.pushInsteadOf` and
`url.*.insteadOf` to explicit URLs, SCP-like addresses, and local paths before
transport selection. The real Git client selected `git-remote-1helper` while
the command guard allowed the corresponding literal-address push and audited
only that literal.

| ID | Finding | Reproduced behavior | Remediation | Status |
|---|---|---|---|---|
| RV-88 | Explicit address did not prove Git's effective destination or helper | All three repository forms were autonomous while persistent rewrites could select another address or helper | Keep aliases denied; parse literal requests; apply `ALWAYS_ASK` to every push; audit only the requested address | Remediated; final independent verification pending |

The bypass behavior was observed RED through the real policy entrypoint before
adding `ALWAYS_ASK` and GREEN afterward. Three stable RV-88 fixtures cover all
repository operand forms, and a one-site typed mutation removes the modifier
to prove that the witness fails. The deterministic source and Debian/WSL
package gates pass 239 tests with zero skips, 100 percent critical
line/function/branch coverage, four fixed property seeds, 68 of 68
pristine-baseline typed mutations, and all 117 installed fixtures. Markdown,
spelling of changed documents, schema, and CI workflow validation also pass.
One fresh independent read-only verification remains required before merge.
