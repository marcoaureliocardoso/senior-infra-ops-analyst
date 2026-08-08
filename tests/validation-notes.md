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
Bubblewrap, Node.js, Python, the `timeout` and pseudo-terminal `script`
utilities, Claude Code, Nori, network access, and an operator-configured
DeepSeek route. It requires this exact temporary acknowledgment:

```bash
P0_04A_LIVE_NORMAL_CREDENTIALS_ACK=I_ACCEPT_PROVIDER_CREDENTIAL_EGRESS_RISK \
  bash tests/live-context-continuity-smoke.sh --run-live
```

Exit `0` means every requested deterministic or live invariant passed. Exit
`1` means a safety or behavioral invariant failed. Exit `2` means a
prerequisite or runtime capability is unavailable and must never be reported as
a pass. The harness creates a generated HOME and `CLAUDE_CONFIG_DIR`, installs
the current worktree through discovered Nori, imports only the approved Claude
transport environment allowlist through a NUL-delimited FIFO, and deletes
content-bearing JSONL, PTY, transcript, and request captures. Explicit
`--keep-artifacts` retains them only inside the verified temporary directory
and prints a warning that they contain model content.

Production configuration remains percentage-based with default `72` and
preserves an operator value from 70 through 75. The automatic-compaction probe
uses process-scoped `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=5` solely to make the test
bounded; it does not change installed settings. The real DeepSeek route runs
with `CLAUDE_CODE_AUTO_COMPACT_WINDOW` unset. An absolute override is
diagnostic-only and may be exercised against a disposable divergent-window
fixture only after normalized evidence reports `WINDOW_REPORTING_DIVERGENCE`;
the evidence then records `absoluteOverrideEvidenceGated` without retaining a
prompt, response, or raw gateway request.
