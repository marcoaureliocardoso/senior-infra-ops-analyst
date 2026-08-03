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
   dynamic interpreters, unquoted expression/call delimiters, unmatched syntax,
   and control characters. Quoted delimiters remain literal data.
3. A composition graph binds ordered stages, operators, redirects, and
   source-to-sink edges instead of blanket-blocking pipes.
4. A finite executable-specific catalogue classifies host/log reads, services,
   containers, AWS/Azure/GCP, PostgreSQL/MySQL/MongoDB/Redis, network probes,
   packet capture, HTTP, SSH/file transfer, sudo, Git/CI, PowerShell reads, and
   Windows service control. Mutations require explicit target/environment
   bindings. In-command environment prefixes accept credential transports and
   the named AWS profile reference, but reject configuration, helper, agent,
   loader, plugin, and executable-resolution overrides.
5. The policy retains bounded per-stage findings, aggregates the highest risk
   and approval modifiers, then applies the permission-mode matrix. Every
   changed call is evaluated independently.
6. Client-aligned credential parsing excludes the non-secret identity marker,
   recognizes separated, equals-attached, and compact accepted transports, and
   determines the exact credential transport before model-visible output.
   Audit uses a SHA-256
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
10. Client-specific closed schemas reject curl local-file request sources in
    separated, equals-attached, and compact forms; SSH configuration and local
    execution hooks; Kubernetes raw endpoints; and enabled follow/watch or
    pagination-disabling options. Curl proxy, name-resolution, and insecure TLS
    overrides deny because the current domain binding cannot represent the
    changed route or trust. Kubernetes consumes a closed context-preserving
    option schema and rejects endpoint, credential, trust, impersonation, and
    plugin overrides. Literal HTTP bodies, finite Kubernetes reads, and
    allowlisted literal SSH transport options remain catalogued.
11. Options whose client semantics are singleton or last-wins cannot silently
    diverge from the audited value. Curl method selectors and Kubernetes
    context/namespace aliases reject duplicates; AWS endpoint, trust, unsigned,
    diagnostic, and external-input overrides deny; Docker host, connection, and
    external-config overrides deny. Named AWS profile assignments participate
    in the environment binding, literal Docker contexts remain usable, and
    remote HTTP origins containing variables or globs deny before URL parsing.
    Curl cookie options and Redis compact quoted passwords are recognized as
    literal credential transports before authorization.
12. Commands with more than one distinct literal credential transport deny
    before approval lookup, so an Authorization approval cannot authorize an
    additional Cookie, Basic Auth, flag, or variable transport. Repeated
    allowlisted environment assignments and Redis host, port, database,
    password, or user selectors also deny before the effective value is
    derived. Docker's separated `-H` spelling is treated as the same prohibited
    remote-host selector as its compact and equals forms.
13. Redaction supplements semantic patterns with Bash lexer token boundaries.
    For accepted curl and Redis credential options, the entire raw value token
    is removed even when the shell builds one cooked value by concatenating
    quoted and unquoted fragments. Overlapping inner matches cannot leave a
    suffix in responses, normalized data, audit, or installed-form evidence.
14. Redis uses a closed option schema. Plain TCP and system-trust `--tls`
    remain available, while insecure verification, alternate trust/client
    files, SNI, URI/socket routing, cluster redirects, stdin argument sources,
    special modes, and unknown options deny. Its canonical non-secret
    environment binds transport, host, port, database, and ACL user with
    explicit defaults, so changing any effective selector requires a new
    approval without storing password material.
15. Redis verbs are parsed as complete finite grammars after connection-option
    consumption. `EXPIRE` accepts one literal key, a signed 64-bit TTL, and at
    most one valid condition; zero and negative TTLs are destructive because
    Redis deletes the key. `PERSIST` accepts exactly one literal key. `CLIENT
    KILL` accepts only one literal `host:port` address or `ID` plus one positive
    signed 64-bit identifier. Unknown subcommands, dynamic operands, invalid
    bounds, and unconsumed trailing tokens deny.
16. Generic HTTP `POST`, `PUT`, and `PATCH` are disruptive external effects.
    They remain executable through native `ask` in every permission mode;
    `bypassPermissions` does not convert an unmodelled external mutation into
    autonomous execution. `GET` and `HEAD` retain read classification and
    `DELETE` remains destructive.
17. The critical native coverage boundary includes the command catalogue.
    Each registered security predicate has both one exact one-site source
    mutation and one declared executable witness. Registry equality prevents a
    newly added predicate or mutation from passing through an unknown default
    branch without a dedicated invariant.
18. Curl and PowerShell HTTP clients use separate closed option grammars. Each
    option is consumed with its real arity before method, body, upload, URL,
    and sink semantics are derived. Zero-argument remote-name flags cannot
    consume or hide a following body or upload option.
19. Every accepted HTTP output sink is a local file effect and contributes
    `FILE_WRITE` plus `ALWAYS_ASK` in every permission mode. The canonical
    target is `METHOD /remote/path -> file:/normalized/local/path`. Literal
    relative paths bind to the bounded hook `cwd`; absolute paths are
    normalized with POSIX or Windows semantics.
20. Dynamic output paths are accepted only through names listed in
    `OPS_COMMAND_GUARD_OUTPUT_VARIABLES`. At most eight non-secret names may be
    listed; each value must be an absolute root. The resolver reads only the
    control variable and those named properties, denies credential-like names,
    nesting, defaults, indirection, traversal, globbing, control characters,
    and root escape, and never enumerates the environment. Local path context
    is cleared before nested SSH analysis.
21. PostgreSQL and MySQL consume closed singleton selector schemas. Their
    canonical non-secret approval domains contain scheme, user, host, port,
    and database with explicit defaults. Repeated aliases, dynamic values,
    invalid ports, external configuration/service/login/socket/protocol/TLS
    selectors, and unconsumed operands deny.
22. Git branch operations use a complete finite subgrammar. Listing remains a
    read, literal creation and rename remain changes, and `-d`, `-D`,
    `--delete`, and supported `--force` combinations are all destructive.
23. Mutation evidence first runs every witness against pristine source. A
    mutant is killed only when its own witness exits `42` with the exact
    `WITNESS_ASSERTION:<id>` marker from a Node `AssertionError`; survival,
    timeout, crash, import/configuration failure, or a different marker fails
    the gate.
24. Curl headers are literal and structurally parsed. `Host`, `:authority`,
    dynamic expressions, file-backed headers, and malformed header fields deny
    before HTTP origin binding, so an approved credential cannot be rerouted
    by changing only a header.
25. Networked PostgreSQL/MySQL operations do not inherit an unaudited local or
    process environment domain. `psql` and `mysql` require explicit host, port,
    user, and database selectors; `mysqladmin` requires explicit host, port,
    and user. Socket paths and implicit `PG*` routing therefore deny.
26. Tilde-prefixed output operands deny because the native hook does not
    provide a trustworthy home expansion. Curl's `-` pseudo-sink is modeled as
    stdout rather than a file path.
27. Response headers exposed through include/head flags, header dumps, cookie
    jars, ETag saves, or traces to stdout contribute `SENSITIVE_OUTPUT` and
    `ALWAYS_ASK` in every permission mode.
28. Explicit PostgreSQL selectors do not override every libpq environment
    input. Route, service, password-file, option, TLS, GSS, channel-binding,
    and peer-trust variables deny before canonical domain construction so
    process state cannot change the peer or trust boundary behind the audit.
29. MySQL host values `localhost` and `.` deny. The client may select a Unix
    socket for these values despite an explicit port, while the supported
    grammar intentionally excludes an explicit TCP protocol selector.
30. Curl trace is a credential-disclosure sink derived from the closed curl
    parser. With a literal credential, trace to `-` or `%` denies as secret
    output and trace to a resolved file denies as secret persistence; neither
    can be downgraded to native confirmation by `bypassPermissions`.
31. Credential approval scope is projected from the exact stage carrying the
    literal credential, not from the composition's highest-risk or final
    stage. Composition preserves in-memory lexical source intervals and every
    sensitive span must resolve to one stage; unmapped or multi-stage literals
    deny. The resulting catalogued invocation must declare itself a credential
    consumer and accept the detected transport. Variable transports must also
    match the client's explicit non-secret selector set, so a GitHub token
    cannot be attributed to AWS or a database password to another client. An
    executable name alone is insufficient. Risk aggregation and a later
    catalogued consumer therefore cannot substitute another command family's
    domain.
32. `mongosh` accepts exactly one inline `--eval`; `ip` rejects every separated,
    equals-attached, or compact batch-file form. Extra scripts, shell mode, and
    opaque command files deny.
33. `scp` and `sftp` consume closed transport schemas and complete operand
    shapes. The canonical non-secret identity includes explicit user, host,
    default or selected port, address family, ProxyJump route, Kbit/s limit,
    and identity file. `-4`, `-6`, and `-o AddressFamily` form one singleton
    selector group whose accepted value is case-normalized; repetition or
    conflict denies. Other equivalent or repeated selectors and destinations
    without an explicit user deny. Local executors, arbitrary configuration,
    proxy commands, server programs, and SFTP batch files also deny.
34. Packet-capture schemas consume every supported option. A resolved `-w`
    sink is `LOW_RISK_CHANGE + FILE_WRITE + ALWAYS_ASK`; post-process executors,
    input file lists, dynamic sinks, and unknown options deny. `-w -` is
    `SAFE_READ_ONLY + SENSITIVE_OUTPUT + RESOURCE_INTENSIVE + ALWAYS_ASK` with
    target `stdout:pcap`, never a file named `-`; repeated semantic selector
    groups deny across short and long aliases.
35. `ctr` has a hierarchical image grammar: list is read-only, pull/import are
    changes, and remove aliases are destructive. Git read verbs have closed
    options; resolved diff output is a mandatory-confirmation file effect, and
    external diff/textconv execution denies.
36. `dmesg` consumes display and control options separately. Clear/read-clear
    are destructive and console controls are disruptive, including when a
    display-level selector is also present.
37. Git push uses a complete grammar rather than prefix recognition. Remote
    program, push-option, hook-bypass, unknown, repeated, conflicting, dynamic,
    external `*::` remote-helper, and unconsumed forms deny. The literal
    `scheme://` grammar accepts only exact-lowercase native `file`, `git`,
    `ssh`, `http`, and `https` transports because any other or case-altered
    scheme can invoke a distinct external `git-remote-<scheme>` helper. The effective repository is the audited
    environment, bounded refspecs form the target, and force, delete, mirror,
    prune, plus-prefixed, and deletion refspecs remain destructive.
38. Journal and container log reads consume closed finite schemas. Enabled
    follow aliases, duplicate semantic options, missing values, unknown
    controls, dynamic values, and absent container targets deny. Journal
    maintenance retains its destructive classification; an accepted container
    log read retains that container as its audit target.
39. Each supported GitHub CLI read noun/verb has its own operand and option
    schema. Watch forms and excessive limits deny; broad Actions log output is
    `SENSITIVE_OUTPUT + RESOURCE_INTENSIVE + ALWAYS_ASK`, so it requires native
    confirmation even in `bypassPermissions`. Every accepted read also requires
    an explicit repository selector; implicit current-directory selection
    cannot create a reusable `local` credential domain.
40. Kubernetes `cluster-info` accepts only its bounded summary form. The real
    positional `dump` subcommand, including through `k3s kubectl`, is outside
    the grammar and denies instead of inheriting narrow-read authorization.

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

The parser derives transport from the accepted client spelling rather than a
generic consumer label. `OPS_CREDENTIAL_IDENTITY` supplies only a bounded
non-secret principal and is excluded from credential spans, so Authorization,
Cookie, Basic Auth, flag, variable, and URI transports cannot share approval
state accidentally. A single command containing multiple distinct literal
transports is rejected rather than selecting one transport for binding.

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

- The remediated deterministic gate runs 220 active Node tests with zero
  skips, four recorded property seeds, a finite inventory orphan check, and
  exact mutation-site validation.
- Critical contract, lexer, composition, credential-flow, binding-state,
  policy, catalogue, redaction, response, audit, and both entrypoint modules achieve 100%
  line, function, and branch coverage with native Node test coverage.
- Fifty-three registered security mutations are baseline-proven and killed by
  their exact typed witnesses, including background and
  size bounds, dynamic syntax, unknown family, target binding, destructive
  precedence, risk aggregation, unsafe credential sink, authorization
  redaction, forbidden audit fields, fail-closed exit, Redis destructive TTL,
  literal operands, client termination, canonical environment, unknown
  options, mutable HTTP external-effect classification, curl remote-name
  arity, mandatory sink confirmation, database selector uniqueness and
  canonical domains, Git long-delete parity, the output-root allowlist, HTTP
  routing-header rejection, explicit database domains, sensitive stdout,
  tilde-output rejection, PostgreSQL environment rejection, MySQL socket-host
  rejection, credential-bearing trace disclosure, credential-consumer stage
  binding, credential source-stage ownership, effective consumer/transport
  matching, complete remote endpoint and address-family identity, packet stdout
  identity and selector uniqueness, and the MongoDB,
  IP batch, remote-transfer, packet-capture, nested `ctr`, Git output, and
  `dmesg` control closures.
- Installed validation byte-compares the launcher, entrypoints, and all guard
  modules with source, then executes the same 91-case stable-ID adversarial
  corpus against both forms.
- Each finite grammar, shell operator, command family, reason code, limit,
  credential transport, edge case, and review regression is bound to an
  executable semantic fixture. One ledger proves every declared fixture ran
  exactly once and fails on stale, missing, duplicate, or unexecuted evidence.
- A fresh Debian/WSL package gate passed with an observed capability-compatible
  Node.js `v24.17.0`. A temporary isolated Nori `0.31.0` install registered 12
  subagents, 24 skills, and 20 slash commands; installed semantic validation
  and all 91 installed fixtures passed. These observations are not requirements.
- A static safety contract constrains opt-in live Claude Code/Nori probes to a
  generated home, Bubblewrap, disposable local processes, loopback targets,
  retained-output scans, and redacted evidence.
- The explicitly acknowledged remediated live run passed on Debian WSL2 with
  observed Node.js `v20.19.2`, Nori `0.27.0`, and Claude Code `2.1.218`. It
  registered all 12 subagents, 24 skills, 20 slash commands, and both hook
  phases, then passed the installed corpus and `default` plus
  `bypassPermissions` probes. The harness emitted the mandatory open-egress
  warning. These observed identifiers are evidence, not requirements.
- The complete package gate passed on host and Debian WSL2 Node.js `v24.17.0`,
  whose native test runner exposes the required line, function, and branch
  threshold flags. WSL uses a SHA-256-verified official user-local binary; its
  Debian system Node `v20.19.2` remains unchanged. Capability probing, rather
  than a project version allowlist, determines which runtime executes the
  development gate.
- A fresh isolated Nori installation, without starting Claude or loading
  provider credentials, registered 12 subagents, 24 project skills, and 20
  slash commands; all 65 installed fixtures passed and every source script
  matched its installed counterpart byte for byte. Nori's generated helper
  skill is outside the 24-skill project inventory.

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
