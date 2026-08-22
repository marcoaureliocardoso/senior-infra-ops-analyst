# Validation Notes

`tests/validate-package.sh` performs local checks that do not require internet access:

- JSON syntax
- manifest-to-disk skill/reference integrity
- `AGENTS.md` required reference alignment
- shared risk-level reference usage across skills
- required skill metadata fields
- subagent skill preload presence, syntax, uniqueness, manifest registration, and primary-skill alignment
- negative subagent frontmatter regression fixtures for malformed, duplicate, empty, unknown, and unterminated skill lists
- subagent runtime limits, least-privilege tool policy, critical denials, rationales, and handoff contract
- source-to-installed Nori subagent semantic comparison fixtures
- non-skeletal templates
- slash command template references
- safety sections in command-heavy references
- Bash syntax and helper `--help` smoke tests
- basic permission hygiene
- PowerShell parser validation when `pwsh` or `powershell` is installed
- nori.json schema validation via `tests/validate-schema.py`
- CI workflow validation via `tests/validate-ci-workflows.sh`

`tests/validate-schema.py` performs structural validation of `nori.json`:

- required top-level fields (`name`, `version`, `type`, `description`, `author`, `license`, `skills`, `references`)
- root package type fixed to `skillset`
- semver version format (X.Y.Z)
- no TBD placeholders in `repository`, `homepage`, or `bugs.url`
- unique skills, references, and tags (no duplicates)
- every skill has a directory and `SKILL.md`
- every reference file exists on disk

`tests/validate-ci-workflows.sh` validates CI workflow quality:

- every workflow must declare top-level `permissions:`
- no `ubuntu-latest` floating tag (must pin to `ubuntu-24.04`)
- push/PR-triggered workflows must use `concurrency:` groups
- checkout actions must be pinned by commit hash, not just major version tag

`tests/validate-links.sh` is optional and requires internet access plus `curl`. It treats 2xx, 3xx, 401, and 403 as reachable because vendor documentation sometimes blocks anonymous HEAD requests.

PowerShell syntax was not validated in environments where no PowerShell runtime is present. Run:

```powershell
pwsh -NoProfile -File tests/validate-powershell-syntax.ps1
```

## Live validation note - 2026-07-08

External links were validated through web retrieval because local curl-based validation could not resolve external DNS in the packaging container. See `tests/reports/live-validation-2026-07-08.md`.

PowerShell parser validation with `pwsh`/`powershell` was not possible in this environment. The package still includes `tests/validate-powershell-syntax.ps1` for validation on a host with PowerShell installed.

## Live subagent runtime smoke test

Run only in an isolated Linux or WSL environment with Linux Node.js 22 or newer, Bubblewrap (`bwrap`), Claude Code, Nori, and operator-configured model credentials:

```bash
bash tests/live-subagent-runtime-smoke.sh
```

The test records observed versions but does not require fixed Claude Code, Nori, or model versions. It creates an isolated temporary Claude home, installs the local worktree through Nori, validates the installed subagents, and runs synthetic analytical, executor, handoff, and delegated hard-cutoff probes.

Every model process runs with a minimal environment inside a Bubblewrap mount namespace that exposes the temporary tree and required read-only system runtime paths, not the operator workspace or home. A temporary fail-closed `PreToolUse` hook allows only the exact synthetic `printf` commands; every other Bash input is denied.
The delegated cutoff requires one `SubagentStart` and exactly `maxTurns` guarded commands. An abrupt cutoff can omit `SubagentStop`; when that event is emitted, its assistant-turn count must also match `maxTurns`.
The handoff probe requires all eight field groups in the single final `result` event; prompt, hook, and tool-event strings cannot satisfy the assertion.
Model transport still requires network access, but the guarded Bash tool cannot issue a network command. The test never targets production
infrastructure.

Exit `2` means a prerequisite is blocked, not that validation passed. Transcripts contain model output and remain temporary and untracked unless the operator explicitly passes `--keep-artifacts`. Authentication values are imported from the existing Claude Code settings without being printed or copied into the retained artifacts.

The parser can be validated without model/API consumption:

```bash
bash tests/live-subagent-runtime-smoke.sh --self-test
```

## Native command guard validation

The P0-04 release gate is deterministic and mandatory. It runs the unit,
finite-inventory, property/fuzz, 100% critical line/function/branch coverage,
mutation, synthetic-secret retention, and installed-layout checks:

```bash
node tests/run-command-guard-tests.mjs
python3 tests/test-command-guard-install-policy.py
python3 tests/test-load-claude-env.py
python3 tests/test-loopback-http-fixture.py
python3 tests/test-live-command-guard-safety.py
bash tests/live-command-guard-smoke.sh --self-test
```

The self-test creates a generated isolated Claude home, materializes an
installed-form fixture, validates both the installed agents and skills roots,
and directly exercises normal-mode `allow`/`ask`, bypass-mode `allow`, the
destructive `ask` boundary, detailed `deny`, Bash and PowerShell pipelines,
malformed input, audit failure, and permitted/forbidden synthetic credential
flows. It uses only local fixture data and loopback URL metadata; the direct
guard never executes a proposed command.

On Windows, run the Python tests with PowerShell and the shell harness through
Git Bash:

```powershell
python tests/test-load-claude-env.py
python tests/test-loopback-http-fixture.py
python tests/test-live-command-guard-safety.py
& 'C:\Program Files\Git\usr\bin\bash.exe' -lc 'bash tests/live-command-guard-smoke.sh --self-test'
```

From a configured WSL distribution, run the same Bash commands in the mounted
worktree. The opt-in live probe additionally requires Linux Bubblewrap, local
Claude Code and Nori CLIs, operator-configured model credentials, and network
access for the model transport:

```bash
bash tests/live-command-guard-smoke.sh --run-live
```

`--run-live` installs the current worktree with the discovered Nori CLI,
records the observed Node.js, Nori, Claude Code, platform, permission modes,
and model label, then confines model probes to a generated home and a
loopback-only disposable service. The harness imports only an explicit
Claude/Anthropic environment allowlist from the operator settings through a
NUL-delimited FIFO; it does not copy the settings file, and an already exported
value takes precedence. Bubblewrap preserves a non-root UID, handles usrmerge
links, and exposes only the read-only runtime, resolver, host, and certificate
paths needed by the model transport. The loopback fixture accepts only the
synthetic `/health` and `/reload` targets, allocates a free port, and records
only method and path. It checks both the native
`--permission-mode bypassPermissions` form and, only inside Bubblewrap, the
`--dangerously-skip-permissions` form. Observed versions are evidence, not
compatibility pins. Exit `2` means a prerequisite or capability is unavailable;
it is not a passing live result. Authentication values and raw model
transcripts are never retained by the harness.

An authorized live run on 2026-07-26 passed in Debian WSL2. It observed
Bubblewrap `0.11.0`, Node.js `v20.19.2`, Nori `0.27.0`, and Claude Code
`2.1.218`; the model route came from the operator configuration. The Nori
activation registered all 12 subagents, 24 skills, 20 slash commands, and the
project hooks. Both permissive forms completed, and the dangerous-mode probe
produced the expected synthetic `POST /reload` without retaining its token.
These identifiers document that run only and do not constrain future versions.
The observed hook envelope included `prompt_id` and `effort`; the contract has
regression coverage for a bounded prompt identifier and the documented effort
levels without relaxing unknown top-level or `tool_input` fields.

## Context continuity and preventive compaction validation

The deterministic P0-04A parser and safety checks do not use a model or provider:

```bash
node --test tests/context-continuity/inventory.test.mjs
python3 tests/test-live-context-continuity-safety.py
bash -n tests/live-context-continuity-smoke.sh
bash tests/live-context-continuity-smoke.sh --self-test
```

The self-test proves native `TaskCreate`/`TaskUpdate` and `TodoWrite` family
normalization, task-identifier survival across one synthetic compaction,
available/unavailable/not-observed tool-search reason codes, consistent and
divergent window metadata, and rejection of deliberately unsafe retained
evidence. The retained schema contains only numeric values, booleans, bounded
identifiers, and closed reason codes; prompts, responses, summaries,
transcripts, commands, tool payloads, headers, and credentials are forbidden.

The opt-in real-provider run requires a Linux or WSL environment with non-root
Bubblewrap, Node.js, Python, the `timeout` utility, Claude Code, Nori, network
access, and an operator-configured
DeepSeek route. It requires this exact temporary acknowledgment:

```bash
P0_04A_LIVE_NORMAL_CREDENTIALS_ACK=I_ACCEPT_PROVIDER_CREDENTIAL_EGRESS_RISK \
  bash tests/live-context-continuity-smoke.sh --run-live
```

Exit `0` means every requested deterministic or live invariant passed. Exit
`1` means a safety or behavioral invariant failed. Exit `2` means a
prerequisite or runtime capability is unavailable and must never be reported as
a pass. The harness creates a generated HOME and `CLAUDE_CONFIG_DIR`, installs
the current worktree through discovered Nori, validates the approved Claude
transport allowlist through a NUL-delimited FIFO, and passes those values to
Claude Code through a clean `execve` environment rather than process arguments.
It deletes content-bearing JSONL, PTY, transcript, and request captures. Explicit
`--keep-artifacts` retains them only inside the verified temporary directory
and prints a warning that they contain model content.

Production configuration remains percentage-based with default `72` and
preserves an operator value from 70 through 75. The automatic-compaction probe
uses process-scoped `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=5` solely to make the test
bounded; it does not change installed settings. It detects and explicitly uses
native `--autocompact auto` when the runtime exposes that option. The real
DeepSeek route always runs first with `CLAUDE_CODE_AUTO_COMPACT_WINDOW` unset.
The normal real route never derives or applies an absolute fallback. A separate
loopback mock enforces an observed numeric boundary, proves acceptance and
rejection around it, records `WINDOW_REPORTING_DIVERGENCE`, and only then uses
a process-scoped absolute override in the mock scenario. The operator may also
select `--confirmed-window-diagnostic <tokens>` for a disposable real-route
investigation. That form blocks unless the positive integer exactly equals the
single consistent capacity obtained from Claude Code's documented native
status-line `context_window.context_window_size` field and injects it only into
the automatic child; it never writes the value to installed settings. A generic
model or footer label in the PTY capture cannot satisfy the gate. The mock proves the
behavioral threshold change by observing automatic `PreCompact` only after the
override; it does not synthesize a completed compaction. The real runtime and
current official DeepSeek documentation both report a 1,000,000-token window,
so the divergence prerequisite is absent while the distinct exact-match gate
can still be used after explicit operator approval.

The interactive probe uses the standard-library PTY controller in
`tests/claude-pty-driver.py`. It sends terminal carriage-return keys and waits
for bounded evidence of task creation, `/context`, manual `/compact`, and the
post-compaction task list before advancing. This avoids treating a batch of
input piped into an event-driven TUI as completed interaction.

On 2026-08-09 the latest opt-in run reached every scenario except completed real
automatic compaction. It installed 25 skills and 12 subagents, preserved the
Nori status line and operator settings, measured `/context` for the main session
and all roles, invoked the continuity skill twice, exercised a bounded large
response, connected and listed the one-tool MCP fixture, and ran the explicit
ToolSearch probe. It observed two ordered real manual `PreCompact/PostCompact`
pairs, retained native tasks, invalidated the actual session's credential
binding, completed `/resume`, selected a real `/rewind`, verified post-rewind
tasks and context, proved the binding was not restored, and completed isolated
`/clear`.

The real automatic probe used 70,000 bounded synthetic units, reached a native
`/context` reading of 8% with the isolated threshold set to 5%, and still did
not produce a completed ordered automatic `PreCompact/PostCompact` cycle before
the ten-minute limit. The run therefore exited blocked, emitted no passing final
report, applied no absolute override to the DeepSeek route, and deleted all
content-bearing artifacts. A real-route absolute diagnostic is not eligible on
the current evidence because the reported 1,000,000-token window agrees with
the provider's official current model documentation.

On 2026-08-10 a second opt-in run used a dedicated temporary provider key and
again completed isolated Nori installation and preservation. It stopped before
the automatic scenario when the structural observer recorded the second manual
compaction as `PreCompact` without `PostCompact`. A deterministic delayed-hook
fixture reproduced that the PTY driver could accept terminal text and exit
before the late structural event. The repaired driver now requires the exact
ordered manual sequence, rejects orphaned or duplicated phases, and fails
immediately when the manual evidence path is omitted; a missing event otherwise
waits only within the configured bound. Focused tests and the complete
deterministic gate pass after the repair. That run did not reach the automatic
scenario, so it did not close the automatic live gate.

On 2026-08-12 the post-repair opt-in run completed every prerequisite and
reached the real automatic stage with the exact manual pair checks enabled.
The automatic probe again reached 8% native context usage under the isolated
5% threshold but emitted no completed ordered automatic `PreCompact`/
`PostCompact` pair before its bound. The harness exited `BLOCKED`, emitted no
passing report, applied no absolute real-route override, and deleted its
content-bearing captures. This confirms the PTY race repair without satisfying
the mandatory automatic live gate.

Later on 2026-08-12, three operator-approved confirmed-window runs supplied
`1000000`. The initial implementation matched a generic native `[1m]` footer
label before the exceptional automatic child began. Independent review later
showed that label was insufficient structural capacity evidence. The first
observed 3% and exposed that
pressure sizing reused the percentage of a different manual session. The
second also observed 3% and exposed that one large PTY write could be partial.
Deterministic regressions now size every new automatic session independently
and retry bounded PTY writes until every byte is accepted; all 13 PTY tests pass
on POSIX. The final run, with 420,000 bytes delivered completely, still observed
3% and no completed ordered automatic `PreCompact`/`PostCompact` pair before
the ten-minute automatic bound. All three runs removed content-bearing captures
and used a dedicated temporary provider key through process environment only.
The repaired design rejects generic PTY labels and permits the technique only
after the disposable runtime emits one consistent capacity through the
documented native status-line `context_window.context_window_size` field and
the operator separately approves it. That stricter route has not been used to
claim live acceptance; the historical evidence remains inconclusive and does
not close the live automatic acceptance gate.

A fourth operator-approved run on 2026-08-12 exercised that repaired stricter
route with Claude Code 2.1.228 and Nori 0.27.0. The disposable runtime emitted
one consistent native capacity of `1000000`, exactly matching the confirmed
operator value, so the harness injected `CLAUDE_CODE_AUTO_COMPACT_WINDOW` only
into the automatic child. That child selected native `--autocompact auto`,
reached 10% native context usage under the isolated 5% threshold, and then
waited 600 seconds without completing the required ordered
`PreCompact(auto)`/`PostCompact(auto)` pair. The harness exited `BLOCKED` after
approximately 855 seconds overall and deleted the temporary directory and all
content-bearing captures. Because cleanup also removes the content-free hook
event file, the terminal evidence proves `complete_pair=false` but cannot
honestly distinguish `pre_only` from `no_pre`. This classification limitation
does not weaken the acceptance criterion or close the automatic live gate.

### Remaining P0-04A acceptance and merge gates

1. **Real automatic acceptance remains open.** The fourth run confirmed native
   capacity `1000000`, reached 10% under the isolated 5% threshold, selected
   `--autocompact auto`, and waited 600 seconds, approximately 855 seconds
   overall, before exiting `BLOCKED`. It did not prove the required ordered
   `PreCompact(auto)`/`PostCompact(auto)` pair.
2. **Sanitized structural classification remains a diagnostic improvement.**
   Cleanup removed the content-free event file with the temporary directory.
   The retained terminal evidence proves only `complete_pair=false`, not
   `pre_only` or `no_pre`. A future run may preserve only one closed
   classification while still deleting every content-bearing artifact; that
   classification cannot replace the required real pair.
3. **Alternative acceptance remains conditional.** If direct observation stays
   infeasible, a revised criterion requires a new explicit operator decision.
4. **The exact final head still needs final gates.** Any subsequent change must
   receive independent review without release-blocking findings and green CI
   and Security results on that exact commit.
5. **Merge and roadmap completion remain pending.** PR #32 stays draft until the
   prior gates are satisfied. P0-04A remains pending until the approved final
   head is merged into `main`.

### Operator-approved release decision and future validation

On 2026-08-12 the operator explicitly authorized merging PR #32 with the real
ordered `PreCompact(auto)`/`PostCompact(auto)` observation deferred to a future
non-blocking validation attempt. This satisfies the conditional alternative
acceptance path without converting `complete_pair=false` into `pre_only`,
`no_pre`, or a passing automatic-compaction result.

The future attempt remains recorded as an open follow-up: obtain one real
ordered pair and retain only the sanitized closed structural classification
`complete_pair`, `pre_only`, or `no_pre` after cleanup. It must retain no
transcript, prompt, summary, raw hook input, provider content, credential, or
secret. Final independent review, CI/Security on the exact head, and merge into
`main` remain required before the definitive roadmap can mark P0-04A complete.

Deterministic evidence includes strict settings merge and rollback, inherited
status-line refusal, compact-hook concurrency and failure paths, authorization
invalidation, 100% critical command-guard coverage, 82 security mutations,
canonical source/installed hook validation for 12 subagents, inventory tests for
25 skills and 12 subagents, and content-free parser self-tests.

The 2026-08-12 status-line fallback extension adds deterministic coverage for
equality without warning, unrounded fractional comparison, every effective
threshold from 70 through 75, fallback to 72 for missing or invalid values,
remaining-only input without warning, the real executable's exact two-line
output, malformed and oversized neutral input, empty stderr, and absence of
local artifacts. The warning is advisory and does not submit `/compact` or
disable native automatic compaction. This deterministic result does not prove
that automatic compaction fired or failed and does not change the `BLOCKED` /
inconclusive status of the required real ordered automatic
`PreCompact(auto)`/`PostCompact(auto)` acceptance gate.

## Isolated Nori package installation (2026-08-13)

The canonical package staging was linked and switched with the locally
detected Nori Skillsets CLI 0.31.0 in a disposable Debian WSL environment. The
smoke used temporary `HOME`, XDG configuration, install, staging, and local
profile paths; selected `claude-code` explicitly; ran non-interactively; and
performed no login, download, upload, or registry mutation.

The observed result was `canonicalContent=true`, `managedBlockCount=1`,
`skillsSectionCount=1`, `unmanagedSentinel=true`, all 25 packaged skills
present among 26 installed skills, exact 12-subagent and 20-command identity,
and no unexpected skill outside the declared dependency or Nori-owned helper
boundary. Cleanup also reported `passed`. The bare name accepted by
`link --name` resolved to a temporary
`personal/` identity, as detected from the current CLI contract rather than a
version pin. The sentinel was placed outside an existing empty Nori-managed
block, which exercises the CLI's supported preservation boundary; a wholly
unmanaged initial `CLAUDE.md` is an import/capture scenario, not the switching
scenario covered by this package smoke.

## Canonical external staging (2026-08-13)

The exact operator-approved destination `C:\projects\ops-analyst-upload` was
first confirmed as a regular directory and then replaced through the hardened
move-aside/revalidate/restore path. The final read-only check reported 199
files, 638325 logical bytes, eight allowlisted root entries, `AGENTS.md`
present, and zero sibling recovery or temporary artifacts. No inventory file
was written into staging. This evidence describes local package construction;
it is not a registry dry-run or upload result.

## Authenticated public-registry dry-run (2026-08-13)

The locally detected Nori Skillsets CLI 0.31.0 accepted an operator-provided
public API token through process-only `NORI_API_TOKEN`. The token was entered
through a no-echo prompt, was never placed in argv or a file, and was unset
when the process exited. Raw CLI output lived only in an owner-only temporary
directory that cleanup removed.

The authenticated public version query completed with exit 0 and returned no
published versions for `senior-infra-ops-analyst`; therefore `0.12.0` was not
present. An initial dry-run using the plan's namespaced temporary identity
returned exit 1 because the detected CLI interprets `personal/...` as a
registry namespace. That attempt left the staging hash, active profile, and
development link unchanged and removed its temporary link.

The successful route used a disposable `HOME` and XDG configuration, linked
the final staging under the real bare package name only inside that isolated
home, and selected the public registry explicitly. The dry-run completed with
exit 0 for package `senior-infra-ops-analyst`, version `0.12.0`, and public
registry class. The sorted staging-inventory SHA-256 was
`b0641ed282c0851d12314d6f48f7d9dee41d84f318e939c88298e9d0fb05fc6b`
both before and after. The real active profile and development link were
unchanged, the isolated link was removed, and cleanup retained no token, raw
response, configuration content, header, or credential. `--dry-run` performed
no registry upload; a real publication remains separately gated.

## First-class subagent package validation (2026-08-13)

All 12 subagents now use the canonical source layout
`subagents/<id>/SUBAGENT.md` plus an adjacent `nori.json` with component
version `1.0.0` and type `subagent`. Focused contract tests exercised missing,
malformed, mismatched, legacy-flat, and linked/reparse component cases. The
final Debian WSL contract run passed 24 tests, including rejection of linked
subagent directories and required definition/manifest files before reading.

A fresh temporary staging build from this source contained 211 regular files
and 642409 logical bytes: 12 `SUBAGENT.md` definitions, 12 adjacent component
manifests, and zero legacy flat definitions. The builder's independent check
accepted the same inventory, and the temporary staging was removed after the
read-only count.

An isolated Nori Skillsets CLI 0.31.0 installation under Node.js 24.18 proved
that all 12 directory components install as the expected flat Claude Code
agent files. The installed definitions were semantically identical after
normalizing Nori's documented `{{skills_dir}}` resolution. The isolated test
used disposable home, configuration, link, profile, staging, and installation
paths; it performed no login, dry-run, upload, or registry mutation, and its
cleanup passed.

The earlier external staging and authenticated dry-run sections above describe
the prior 199-file flat-subagent package. That staging is stale for this source
head and must not be uploaded or reused as publication evidence. A final
external staging must be regenerated from the reviewed commit before any
operator-authorized registry upload. No subagent component or root dependency
was published by this validation.

## Native execution boundary live-routing self-test (2026-08-21)

The P0-05 deterministic self-test completed in Debian WSL without a provider
call. It used generated Nori and Claude Code test doubles, a disposable home,
project, local settings scope, synthetic target, audit directory, and three
separate PTY processes. The observed exact sequence was
`main-default:PreToolUse:deny`, `main-bypass:PreToolUse:deny`, then
`executor-fallback:PreToolUse:deny`; all three records carried
`DENY_UNKNOWN_COMMAND`, matched their expected current-session actor and mode,
and the final bounded report contained three observations in exact order.

The driver ignores all terminal text, retains only its bounded byte count, and
accepts exactly one fresh audit record in a nonce-specific file for each stage.
Deterministic tests reject missing, repeated, orphaned, reordered, echoed-only,
stale-session, malformed, oversized, and timed-out evidence. The main hooks were
applied only to the disposable project and removed before the installed
`diagnostic-operator` fallback was exercised through a simulated native `Agent`
delegation. The exact self-test result has `delegationObserved: true` only for
that fallback. Cleanup removed the generated home, settings, audit and lifecycle
events, stage results, synthetic target, and fake tools.

This self-test proves harness structure, not provider-backed Claude Code hook
behavior, and therefore does not establish `ACTIVE` or complete P0-05. The
later provider-backed result below also remained inconclusive. The `--run-live`
route requires the explicit
`P0_05_LIVE_PROVIDER_ACK=I_AUTHORIZE_BOUNDED_PROVIDER_USE` acknowledgement; a
missing record, invalid exact sequence, output bound, or timeout is reported as
`INCONCLUSIVE` and cannot satisfy acceptance.

Independent-review remediation now requires every accepted audit record to
carry the exact 32-character random stage nonce supplied only to that launched
child process. Missing, malformed, or mismatched nonce evidence is rejected.
The main-session event contract also rejects either partial identity shape:
`agent_type` without `agent_id` and `agent_id` without `agent_type`.

The denied coverage probe ends at `PreToolUse` by design and therefore cannot
exercise `PostToolUse`. Both phases must still be exact in installed settings;
successful authorization reuse remains unavailable unless its real call later
produces matching successful Post evidence. The settings configurator detects
and preserves a target changed before its guarded raw-byte recheck. Its
cross-platform path operations are not represented as protection against a
malicious same-principal local actor swapping paths between syscalls; managed
settings or an operating-system-protected manual change is required for that
threat model.

The first operator-authorized `--run-live` attempt stopped before Claude Code
or any provider request because the detected Nori Skillsets CLI 0.27.0 linked
the disposable package with a bare identity while the harness still assumed
the newer `personal/` namespace. A second authorized attempt also stopped
before Claude Code or the provider because that CLI decorates linked entries
from `list` with the literal ` (linked)` suffix. Cleanup removed both
disposable trees. The harness now removes only that exact structural suffix,
requires exactly one identity, and accepts only the requested bare identity or
its exact `personal/` form; missing, ambiguous, or unrelated identities fail
closed. Neither aborted attempt is provider-backed evidence, and together they
consumed none of the three authorized requests.

After the strict Nori-output repair passed the complete package gate and an
independent review, the authorized provider route ran with Claude Code 2.1.236,
Nori 0.27.0, and the configured `deepseek-v4-pro[1m]` model. The bounded public
report observed exact nonce-bound `PreToolUse` denials with
`DENY_UNKNOWN_COMMAND` for `main-default` and `main-bypass`.
`executor-fallback` produced no auditable record and returned
`TIMEOUT_OR_NO_AUDIT`, so the exact three-stage sequence was incomplete and the
overall result was `INCONCLUSIVE`. It does not establish `ACTIVE` or satisfy
P0-05 acceptance.

All three bounded Claude stages were launched, so the operator authorization
budget is treated as exhausted even though the content-free evidence cannot
prove whether the third process reached the provider. No additional provider
request was made. The harness retained no prompt, transcript, terminal text,
or credential value, and cleanup removed the disposable tree.

Post-run comparison with the current official Claude Code hook contract found
a deterministic mismatch in the previous fallback route. A session started
with `--agent` supplies `agent_type`, while `agent_id` is present only inside a
real subagent call. The command guard intentionally rejects either partial
identity shape, so the old `--agent diagnostic-operator` harness could not
represent a protected delegated executor.

The corrected no-provider harness leaves the guard unchanged and instead
restricts the parent to the native `Agent` tool, delegates the exact synthetic
probe to `diagnostic-operator`, and observes the executor's existing
nonce-bound audit. A disposable `SubagentStart` hook records only fixed
booleans, event type, schema version, and nonce. It distinguishes
`DELEGATION_NOT_OBSERVED`, `EXECUTOR_GUARD_NOT_OBSERVED`, and malformed
lifecycle evidence, but cannot establish acceptance by itself. Focused tests
cover valid, missing, duplicate, malformed, oversized, pre-existing, and
content-bearing inputs without retaining session, agent, transcript, cwd,
prompt, terminal text, or credentials. No provider request was made after this
repair; the prior live result remains `INCONCLUSIVE`.
