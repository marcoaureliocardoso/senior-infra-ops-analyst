# Senior Infrastructure Operations Analyst Skillset

Version: 0.13.0

[![CI](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/ci.yml/badge.svg)](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/ci.yml)
[![Security](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/security.yml/badge.svg)](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/security.yml)
[![Release](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/release.yml/badge.svg)](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/workflows/release.yml)

A command-driven skillset that personifies a Senior Infrastructure Operations Analyst for safe, evidence-based hybrid infrastructure operations.

## Core behavior

The agent should not merely suggest diagnostics when tool access exists. It should execute commands when the native guard returns `allow`, use Claude Code's exact prompt for `ask`, reformulate `deny`, summarize observed evidence, and interpret results.

## Included skills

This package includes 25 skills covering core operations, continuity, incident/change/RCA, on-prem infrastructure, cloud, Kubernetes, databases, containers, load balancers, PKI, CI/CD, monitoring stacks, message queues, web gateways, privileged access, ITSM/CMDB, DR drills, vendor escalation, and audit evidence.

## Context continuity and preventive compaction

Long work uses Claude Code's native task list and short Compact Instructions so
the objective, decisions, evidence locations, operational state, and next action
can be re-established after compaction. Auto-compaction stays enabled. The
package default is `72` percent and an existing operator value from `70` through
`75` is preserved; no absolute window size is pinned.

Check before applying project-local, operator-owned settings:

```bash
node skills/context-continuity/scripts/configure-context-continuity.mjs --check --scope project
node skills/context-continuity/scripts/configure-context-continuity.mjs --apply --scope project
node skills/context-continuity/scripts/configure-context-continuity.mjs --apply --scope project --status-line
node skills/context-continuity/scripts/configure-context-continuity.mjs --remove-owned --scope project
```

`--status-line` is opt-in and refuses to replace an existing status line.
When this package owns that status line, it keeps the normal `ctx N%` line. If
native `context_window.used_percentage` is strictly greater than the effective
`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` threshold, it adds a second line suggesting
the continuity-preserving `/compact` command. This is an advisory fallback
only: native automatic compaction stays enabled, and the package never submits
the command. An inherited operator or Nori status line remains untouched and
therefore does not receive this package-owned warning.

`--remove-owned` removes only values that remain package-owned and preserves
later operator changes. `CLAUDE_CODE_AUTO_COMPACT_WINDOW` is not normal
configuration. A disposable diagnostic may use it after either measured window
divergence or an exact match between the operator-confirmed value and Claude
Code's native status-line `context_window.context_window_size` field. The
confirmed-window form requires separate operator approval,
affects only the automatic-probe child, and never changes installed settings.

All 12 subagents receive non-blocking `PreCompact` and `PostCompact` hooks. They
retain no transcript, prompt, compact summary, model output, tool payload, raw
command, header, credential, or secret. Compaction invalidates credential reuse;
missing proof requires fresh native authorization. The optional inventory emits
only bytes, counts, percentages, booleans, bounded identifiers, and reason codes:

```bash
node skills/context-continuity/scripts/context-inventory.mjs --root .
bash tests/live-context-continuity-smoke.sh --self-test
```

The opt-in live gate requires an isolated Linux/WSL DeepSeek setup and reports
unavailable tool search or window metadata as capability results, not passes.
It detects native `--autocompact auto` support and always attempts the real
route without an absolute override first. An exceptional process-scoped run may
use `--confirmed-window-diagnostic <tokens>` only when that positive integer
equals the single consistent capacity observed through that runtime field and
the operator separately approves it. Missing, conflicting, or mismatched evidence
blocks before the exceptional automatic probe.
P0-04B browser automation remains outside this release.

## Subagents

This package includes 12 role-focused subagents under `subagents/` that provide domain-specific operating posture for AI agents:

| Subagent | Domain | Max turns | Tools |
|---|---|---:|---|
| `incident-commander` | Incident coordination, severity, communication | 20 | `Read, Grep, Glob, TodoWrite, Skill` |
| `diagnostic-operator` | Evidence-first diagnostics across all domains | 16 | `Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill` |
| `change-manager` | Change planning, risk review, rollback | 10 | `Read, Grep, Glob, WebFetch, WebSearch, Skill` |
| `rca-facilitator` | Root cause analysis, evidence mapping | 12 | `Read, Grep, Glob, WebFetch, WebSearch, Skill` |
| `observability-sre` | SLO/SLI, error budgets, alert audit | 14 | `Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill` |
| `security-operations-reviewer` | Security review, credential exposure | 10 | `Read, Grep, Glob, WebFetch, WebSearch, Skill` |
| `cloud-platform-operator` | AWS, Azure, GCP diagnostics | 16 | `Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill` |
| `kubernetes-operator` | K8s/K3s workloads, services, RBAC | 16 | `Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill` |
| `database-operator` | DB availability, locks, replication | 16 | `Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill` |
| `network-edge-operator` | Firewall, LB, proxy, DNS, gateway | 16 | `Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill` |
| `release-cicd-operator` | CI/CD pipelines, deployments, artifacts | 14 | `Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill` |
| `audit-evidence-collector` | Audit evidence, redaction, compliance | 12 | `Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill` |

Each subagent inherits the project-wide safety model (`references/risk-levels.md`, `references/command-execution-protocol.md`) and preloads only its documented primary skills through the native Claude Code `skills` frontmatter. Native `tools` allowlists, `disallowedTools`, and `maxTurns` bound runtime capability; `Write` and `Edit` are denied to every role, while analytical roles also deny `Bash`.
Each source definition is a first-class Nori component at `subagents/<name>/SUBAGENT.md`, with an independently versioned `subagents/<name>/nori.json`. Nori flattens that source package into `.claude/agents/<name>.md` when installing for Claude Code.
Each definition ends with an explicit runtime-precedence block so a budget-exhausted handoff overrides the normal role output.
Other project skills remain available for on-demand discovery. See `subagents/` for full definitions.

## Native command guard

The eight executor roles with `Bash` carry native `PreToolUse` and
`PostToolUse` hooks. A fail-closed launcher invokes the shared deterministic
Node.js validator and approval recorder from the Nori-installed
`command-driven-operations` skill. Missing runtimes or artifacts, timeouts,
crashes, malformed output, and unexpected stdout block the call. The four
analytical roles remain shell-free.

Direct main-session Bash protection is an explicit project-local opt-in. Nori
installation alone does not modify operator settings. From the installed
`command-driven-operations` skill, inspect, add, or remove only package-owned
hooks with:

```bash
node "<installed-command-driven-operations>/scripts/configure-native-execution-boundary.mjs" --check
node "<installed-command-driven-operations>/scripts/configure-native-execution-boundary.mjs" --apply
node "<installed-command-driven-operations>/scripts/configure-native-execution-boundary.mjs" --remove-owned
```

The configurator rejects linked paths and target drift it observes before
replacement. It is not a security boundary against a malicious local process
running as the same account and racing filesystem syscalls; use managed
settings or an operating-system-protected manual change for that threat model.

Exact settings produce `CONFIGURED_UNPROVEN`, not runtime proof. Before direct
operational Bash, the current session must observe the expected structured
guard denial for `printf P005_GUARD_PROBE`; the probe proves coverage only and
does not authorize a later command. Otherwise delegate to a protected executor
or perform no execution. See `references/native-execution-boundary.md`.

The deterministic live-routing self-test uses disposable Nori and Claude Code
test doubles and makes no provider call:

```bash
bash tests/live-native-execution-boundary-smoke.sh --self-test
```

Real validation is separately opt-in, bounded to three harmless denied probes,
and imports only the allowlisted provider settings needed to start Claude Code:

```bash
P0_05_LIVE_PROVIDER_ACK=I_AUTHORIZE_BOUNDED_PROVIDER_USE \
  bash tests/live-native-execution-boundary-smoke.sh --run-live
```

The real route creates a disposable home and project, observes only fresh
content-free hook audit records bound to an exact random child nonce, never
retains terminal output, and removes the
main-session hooks before exercising the protected executor fallback through a
real `Agent` delegation. The fallback starts a disposable coordinator whose
only tool is `Agent(diagnostic-operator)`; it does not use the global `--tools`
availability restriction, so the protected executor can resolve Bash only from
its own definition. On 2026-08-22, a separately authorized provider run proved
this structure with three exact nonce-bound denials, including both the
`SubagentStart` marker and executor `PreToolUse` audit. That ephemeral proof
authorizes no later call and establishes no durable `ACTIVE` state. A marker
alone remains diagnostic and cannot satisfy acceptance. A timeout or incomplete
sequence is `INCONCLUSIVE`; it never establishes `ACTIVE`.

The guard uses separate Bash and PowerShell lexers, builds the complete stage,
operator, redirect, and data-flow graph, and validates every stage against a
finite operational catalogue. Pipes are therefore analyzed rather than
blanket-blocked. Normal modes allow narrow reads and ask for bounded sensitive
reads and catalogued changes. `bypassPermissions` allows catalogued
non-destructive work unless the catalogue adds `ALWAYS_ASK`; destructive work
still asks. Unknown, ambiguous,
dynamic, unbounded, or exfiltrating calls deny with a redacted explanation.
Verbs must occupy their family-defined position, filters cannot add independent
file inputs, and log, scan, query, packet, and cloud-list bounds are checked
before authorization.

An outer `pwsh` or `powershell` wrapper must contain exactly one canonical
case-insensitive `-NoProfile` before one `-Command` payload. Unknown,
abbreviated, duplicated, conflicting, or unconsumed wrapper options deny, so
profile startup code cannot run before the analyzed payload.

Git push, GitHub CLI reads, journal reads, and container logs use closed
verb-specific grammars: every accepted option and operand is consumed, the
explicit requested Git repository address is bound to the audit environment, external Git
remote-helper transports containing `::` deny, and URL schemes are limited to Git's native
exact-lowercase `file`, `git`, `ssh`, `http`, and `https` transports because
Git preserves scheme case when selecting remote helpers. Named Git remotes
such as `origin` also deny because repository configuration can rewrite them
to an unaudited URL or helper; use an explicit native URL, SCP-like address, or
local path. Git can also rewrite explicit addresses through persistent
`url.*.pushInsteadOf` or `url.*.insteadOf` configuration, so every parsed
`git push` carries `ALWAYS_ASK`, including in `bypassPermissions`. The audit
records the requested address and does not claim it is the effective
destination or helper. Implicit GitHub repository selection denies.
Local `git add`, `git commit`, and `git tag` also use closed grammars with
canonical targets; amend, forced tag replacement, and tag deletion are
destructive. Git hooks, clean/process filters, configured signers, and other
indirect local subprocesses remain an approved out-of-scope residual risk and
are not claimed as enforced by the current-call guard.
Streaming follow/watch forms and excessive output limits deny; broad GitHub
Actions logs require native confirmation, and container log reads retain the
container as audit target. Plain `kubectl cluster-info` remains a narrow read,
while `cluster-info dump` denies as an unbounded sensitive collection. Enabled
`kubectl apply --prune` and `k3s kubectl apply --prune` are destructive and
therefore always require native confirmation; explicit `--prune=false` retains
ordinary disruptive-apply treatment.

Profiles, agents, keychains, cached sessions, credential helpers, runtime
variables, and protected-file direct flows configured outside the generated
command are preferred. In-command overrides that select configuration files,
helpers, agents, loaders, plugins, executable resolution, network route, or TLS
trust deny when their effective destination cannot be proven statically. AWS
endpoint/trust controls and Docker host/external-config controls deny, while a
named AWS profile and one literal Docker context remain bound and usable.
Kubernetes accepts only a closed set of context-preserving options; duplicate
singleton selectors deny. Repeated allowlisted assignments and Redis singleton
selectors also deny, and every Docker `-H`/host spelling is treated as a remote
route override. Curl cannot override proxy, name resolution, or peer
verification, repeat method selectors, or use a dynamic origin. A literal supplied
in conversation is already model/provider/transcript-visible. The guard
prevents additional disclosure. First literal use always asks. Only a matching,
successful `PostToolUse` event activates bounded, non-secret state for
same-session, same-domain, same-identity, same-transport reuse in
`bypassPermissions`, while every command is independently re-evaluated. A call
that mixes distinct literal credential transports denies, and lexer-aligned
redaction removes complete raw credential values even across concatenated quote
segments. The
state contains no value, hash, raw command, or secret-derived identifier.
Successful Bash calls without a pending binding leave `PostToolUse` as a silent
no-op.

Redis accepts a closed operational schema for literal host, port, database,
user, password, and system-trust `--tls`. Its approval domain includes
transport, host, port, database, and user with explicit defaults. Insecure TLS,
alternate trust/client files, SNI, URI/socket routing, cluster redirects,
special modes, stdin argument sources, and unknown options deny.
Redis verbs also use complete literal grammars: positive `EXPIRE` and exact
`PERSIST` are catalogued changes, non-positive `EXPIRE` is destructive, and
`CLIENT KILL` accepts only a bounded address or positive numeric client ID.
Malformed, dynamic, incomplete, or trailing Redis operands deny.

Generic HTTP `POST`, `PUT`, and `PATCH` remain available as disruptive external
effects, but always require native operator confirmation even in
`bypassPermissions`. `GET` and `HEAD` retain read semantics, while `DELETE`
remains destructive.

Curl and PowerShell HTTP clients use closed option grammars with complete
arity consumption. Every accepted local output sink is normalized against the
hook `cwd` or an explicitly configured non-secret root, contributes
`FILE_WRITE + ALWAYS_ASK`, and is represented as
`METHOD /remote/path -> file:/normalized/local/path`. Configure at most eight
approved roots by listing their variable names in
`OPS_COMMAND_GUARD_OUTPUT_VARIABLES` (for example,
`OPS_OUTPUT_DIR,OPS_EXPORT_DIR`) and assigning each an absolute path. Dynamic,
unlisted, credential-like, relative, nested, defaulted, or escaping roots deny;
the guard reads only the listed names and never enumerates the environment.
Tilde-prefixed destinations deny because their shell-resolved home cannot be
derived from the hook contract. Curl routing headers (`Host` and
`:authority`) and dynamic header expressions deny. Response headers sent to
stdout, including `--include`, `--head`, header dumps, cookie jars, and traces,
contribute `SENSITIVE_OUTPUT + ALWAYS_ASK`; the `-` pseudo-sink is never
misreported as a local file. A curl trace produced while a literal credential
is present denies outright: stdout traces use `DENY_SECRET_OUTPUT`, while file
traces use `DENY_SECRET_PERSISTENCE`.
Redirect following denies because the requested literal origin cannot prove an
effective redirect target. Curl location flags are rejected, and PowerShell
HTTP clients require exactly `-MaximumRedirection 0`. Literal secret-bearing
header names such as token, credential, password, and API-key variants enter
the same redaction and approval path as Authorization.
Every curl invocation accepted by the guard must place exactly one `-q` or
`--disable` first, preventing implicit curl configuration from changing the
audited request. Missing, late, repeated, negated, or compact disable controls
deny with actionable guidance. Azure Functions `X-Functions-Key` and Azure API
Management `Ocp-Apim-Subscription-Key` are treated as credential-bearing
headers; nearby ordinary header names remain available.

PostgreSQL and MySQL consume closed singleton connection selectors and bind
credential approval to scheme, user, host, port, and database. Networked
`psql` and `mysql` calls require all four selectors explicitly; `mysqladmin`
requires explicit host, port, and user. Repeated aliases, implicit environment
selectors, config/service/login/socket/protocol/TLS overrides, dynamic
selectors, invalid ports, and trailing operands deny. PostgreSQL routing,
service, password-file, and trust environment variables deny even when the
network selectors are explicit; MySQL `localhost` and `.` hosts deny because
the client can reinterpret them as local socket transport. Git branch
creation, listing, rename, and deletion use one closed subgrammar; short and
long deletion aliases are uniformly destructive.

Credential reuse is scoped from the exact credential-bearing stage rather
than the composition's highest-risk or final stage: lexical source intervals
must map every sensitive span to one consumer, the catalogued invocation must
explicitly consume that exact transport and variable selector, and multi-stage
literals deny.
Closed grammars also cover a single `mongosh --eval`, all `ip` batch aliases,
and `scp`/`sftp` transport overrides. Remote-transfer identities contain the
explicit user, host, port, address family, jump route, bandwidth limit, and
identity file; address-family values are case-normalized, while duplicate
aliases, conflicting `-4`/`-6`/`AddressFamily`, or implicit users deny.
Packet-capture `-w -` is always-ask
sensitive stdout rather than a file effect, while resolved capture files always
ask and duplicate selector aliases deny. Hierarchical `ctr images`, Git read
sinks/external executors, and `dmesg` control actions remain fully classified;
opaque loaders, local executors, dynamic sinks, and unconsumed options deny.

Mandatory static and installed-form validation:

```bash
node tests/run-command-guard-tests.mjs
python3 tests/test-command-guard-install-policy.py
python3 tests/test-ci-workflows.py
bash tests/validate-ci-workflows.sh
bash tests/live-command-guard-smoke.sh --self-test
```

The real Claude Code/Nori harness is opt-in because it requires a configured
Linux/WSL environment with Bubblewrap and operator credentials:

```bash
P0_04_LIVE_NORMAL_CREDENTIALS_ACK=I_ACCEPT_PROVIDER_CREDENTIAL_EGRESS_RISK \
  bash tests/live-command-guard-smoke.sh --run-live
```

The live harness currently imports the operator's normal provider credentials
into the Claude process and leaves provider egress available. The explicit
acknowledgement records this temporary accepted exception. A generated Claude
home, non-root Bubblewrap isolation, minimal read-only DNS/TLS mounts,
provider-control-variable denials, retained-output scans, and disposable
loopback targets reduce but do not eliminate credential-exfiltration risk.
Disposable provider credentials or egress allowlisting remain the required
future replacement.

Observed runtime/model versions are recorded as evidence and are not package
requirements. See `docs/architecture/ADR-004-native-command-guard.md`.

## Version history

See [CHANGELOG.md](CHANGELOG.md) for unpublished package states, tagged
versions, and release notes.

## Slash commands

- `/ops-diagnose` — evidence-driven diagnostics using the canonical diagnostic order.
- `/incident-triage` — incident worksheet using `skills/incident-response/templates/incident-worksheet.md` and SEV model.
- `/change-plan` — change plan using `skills/change-management/templates/change-plan.md`.
- `/rca` — RCA using `skills/root-cause-analysis/templates/`.
- `/cloud-check` — scoped AWS/Azure/GCP read-only checks.
- `/runbook` — runbook/playbook drafting using `skills/runbook-authoring/templates/`.
- `/db-triage` — database availability, sessions, locks, replication, storage, and backups.
- `/container-runtime-triage` — Docker/Podman/containerd/CRI runtime issues outside Kubernetes control plane.
- `/k8s-triage` — Kubernetes workload, service, ingress, storage, RBAC, and scheduling triage.
- `/cert-check` — TLS certificate chain, expiry, SAN, trust, and renewal validation.
- `/queue-triage` — queue depth, consumer lag, broker alarms, and message flow.
- `/dr-drill` — disaster recovery drill planning/evidence.
- `/audit-evidence` — audit/compliance evidence collection.
- `/vendor-escalate` — vendor support escalation package.
- `/ssh-triage` — SSH, bastion, PAM, sudo, key, and privileged-access triage.
- `/lb-triage` — load balancer and reverse proxy health/routing/TLS triage.
- `/monitoring-stack-triage` — Prometheus/Grafana/Zabbix/ELK/OpenSearch triage.
- `/web-gateway-triage` — web server, application gateway, WAF, and upstream triage.
- `/cicd-triage` — CI/CD pipeline, runner, artifact, and deployment-gate triage.
- `/itsm-update` — ITSM/CMDB factual update and impact-analysis drafting.

## Template convention

All reusable templates are owned by skills:

```text
skills/<skill>/templates/<artifact>.md
```

There is intentionally no root `templates/` directory from v0.4.1 onward. This avoids duplicate artifacts with unclear ownership.

## Safety model

Commands are classified as:

- `SAFE_READ_ONLY`
- `LOW_RISK_CHANGE`
- `DISRUPTIVE_CHANGE`
- `DESTRUCTIVE`

Operational modifiers include:

- `SENSITIVE_OUTPUT`
- `RESOURCE_INTENSIVE`
- `ACTIVE_PROBE`
- `PRIVILEGED`
- `REMOTE_SESSION_RISK`
- `EXTERNAL_SIDE_EFFECT`

Assign exactly one risk level based on the highest plausible impact, then add all applicable modifiers. SAFE_READ_ONLY commands may be executed automatically only when scoped, non-sensitive, and low load.
Sensitive or broad diagnostics require minimization, redaction, and sometimes approval. LOW_RISK_CHANGE, DISRUPTIVE_CHANGE, DESTRUCTIVE, and EXTERNAL_SIDE_EFFECT actions require explicit approval.

## Assets

Examples and templates are included under specific skills. Templates are guided artifacts, not empty placeholders. Helper scripts live under:

```text
skills/command-driven-operations/scripts/
```

Use:

```bash
./skills/command-driven-operations/scripts/linux-baseline-readonly.sh --help
./skills/command-driven-operations/scripts/network-target-readonly.sh --help
```

For PowerShell:

```powershell
./skills/command-driven-operations/scripts/windows-baseline-readonly.ps1 -Help
```

These scripts are helpers, not permission grants.

## Building Nori upload staging

Build a disposable, allowlisted upload tree from the validated repository:

```bash
python3 scripts/build_nori_staging.py \
  --source . \
  --destination /absolute/path/to/staging
python3 scripts/build_nori_staging.py \
  --source . \
  --destination /absolute/path/to/staging \
  --check
```

The staging root contains only `AGENTS.md`, `LICENSE`, `nori.json`,
`skills.json`, `references/`, `skills/`, `slashcommands/`, and `subagents/`.
The `subagents/` tree contains 12 first-class packages, each with
`SUBAGENT.md` and a `type: "subagent"` manifest.
Root `AGENTS.md` is the canonical source; `CLAUDE.md` is generated by Nori at
installation time and is not a source artifact. `--replace` accepts only a
staging tree whose complete path/size/SHA-256 inventory still matches the
current canonical source. It moves that exact directory aside atomically,
revalidates it, restores it on any race or failure, and refuses drift,
unexpected content, links, reparse points, and special files. The builder does
not log in, upload, publish, or change the active Nori profile. `make package`
creates and verifies a fresh archive, so entries from an older ZIP cannot
survive. Archive output must also remain outside source and staging and cannot
use a symlink, junction, reparse point, or linked ancestor.

## Validation

```bash
# Full local validation (content + schema + CI workflows)
bash tests/validate-package.sh

# Schema-only check
python3 tests/validate-schema.py

# CI workflow quality check
bash tests/validate-ci-workflows.sh

# Live-smoke parser only (no model/API consumption)
bash tests/live-subagent-runtime-smoke.sh --self-test

# Opt-in isolated Nori + Claude Code behavioral smoke
bash tests/live-subagent-runtime-smoke.sh

# Link validation (human-readable)
bash tests/validate-links.sh

# Link validation (machine-readable, for CI)
bash tests/validate-links.sh --json
```

CI runs all validators on every PR and push to main. See `.github/workflows/ci.yml`.

PowerShell parser validation requires a host with `pwsh` or Windows PowerShell installed.

## Docs

- [CHANGELOG](CHANGELOG.md)
- [Architecture decisions](docs/architecture/README.md)
- [Independent review records](docs/reviews/README.md)
- [ROADMAP](ROADMAP.md)
- [CONTRIBUTING](CONTRIBUTING.md)
- [SECURITY](SECURITY.md)
