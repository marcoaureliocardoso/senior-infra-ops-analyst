# P0-04 Native Command Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install a native Claude Code `PreToolUse` guard on all eight
executor subagents that deterministically authorizes catalogued operational
commands, respects the effective permission mode, supports bounded credential
use, and fails closed without turning the skillset into a diagnostic-only
tool.

**Architecture:** Each executor agent declares the same native `Bash` hook,
installed by Nori with an absolute shared-script path. A dependency-free Node.js
entrypoint validates the hook event, lexes Bash-compatible syntax or an explicit
PowerShell payload, builds a bounded command/data-flow graph, applies a
versioned policy catalogue, redacts before fingerprinting or audit, and emits
one native `allow`, `ask`, or `deny` decision. Conversation-level credential
reuse remains an explicit model-facing invariant; the stateless hook validates
only the current call and never stores or derives a secret identifier.

**Tech Stack:** Claude Code Markdown/YAML agent frontmatter, Nori installation
templates, Node.js standard library and `node:test`, Python 3 standard library
repository validators, Bash/Git Bash, PowerShell 7, Markdown ADRs.

## Global Constraints

- Advance the package version from `0.10.0` to `0.11.0` only in the release
  task after implementation and installed-artifact validation pass.
- Do not pin Claude Code, Nori, Node.js, or any model identifier or version.
- Keep `model: inherit`, existing tool allowlists, `disallowedTools`,
  `maxTurns`, and skill preloads unchanged except for the new hook.
- Apply the hook only to the eight roles in `EXECUTOR_AGENTS`; the four
  analytical roles must not receive a `Bash` hook.
- Use native `PreToolUse`, `permission_mode`, `permissionDecision`,
  `permissionDecisionReason`, and `systemMessage`; do not create a daemon,
  approval service, model proxy, wrapper runtime, or model API integration.
- Treat `bypassPermissions` as deliberate session-level autonomy for
  catalogued non-destructive operations; re-evaluate every call.
- Keep `DESTRUCTIVE` at `ask` in every permission mode.
- Use `ask` only for fully understood authorizable operations and `deny` only
  for prohibited or inconclusive operations.
- Never execute the proposed command inside the validator or its deterministic
  tests.
- Never write raw commands, transcripts, tool output, credentials, cookies,
  authorization headers, connection strings, or private keys to guard output,
  audit, snapshots, coverage, mutation reports, or retained test artifacts.
- Redact credential spans before normalization, hashing, explanation, audit,
  exception serialization, and test reporting.
- The guard must never store, hash, fingerprint, compare, or derive an
  identifier from a credential value.
- `MODEL_VISIBLE_LITERAL` is a supported fallback already visible to the
  model/provider/transcript; it is not a masked secret channel.
- Session/domain/identity reuse is enforced by agent instructions and live
  behavioral scenarios. The stateless hook must not claim it proved
  conversation provenance, prior-domain equality, or secret equality.
- Support only the finite grammar, catalogue, transports, limits, and reason
  codes declared by this change. Unknown or ambiguous input fails closed.
- Use only synthetic credentials and disposable local targets in tests.
- Record observed runtime/installer/model versions in live evidence without
  turning them into allowlists or compatibility gates.
- Create and index `ADR-004`; every architecture claim must match the shipped
  implementation and validation evidence.

---

## File map

### Native installation boundary

- `tests/command_guard_install_policy.py`: canonical executor set, exact source
  hook shape, installed hook parser, and source/installed validation errors.
- `tests/test-command-guard-install-policy.py`: mutation tests for missing,
  broadened, malformed, or incorrectly installed hooks.
- `tests/validate-content.py`: invokes source hook validation.
- `tests/validate-installed-subagents.py`: compares installed hook semantics
  and resolved validator path in addition to the existing runtime controls.
- `tests/test-installed-subagents.py`: isolated installed-artifact mutations.
- `subagents/*.md`: native hook plus model-facing credential-reuse rules for
  the eight executors; analytical agents remain hook-free.

### Guard runtime

- `skills/command-driven-operations/scripts/validate-ops-command.mjs`: stdin,
  stdout, stderr, exit-code, deadline, audit, and fail-closed orchestration.
- `skills/command-driven-operations/scripts/command-guard/limits.mjs`: all
  numeric bounds and the finite permission-mode sets.
- `skills/command-driven-operations/scripts/command-guard/contract.mjs`: strict
  hook event validation and duplicate-key-safe JSON parsing.
- `skills/command-driven-operations/scripts/command-guard/redaction.mjs`:
  sensitive-span detection, redacted normalization, and safe fingerprinting.
- `skills/command-driven-operations/scripts/command-guard/response.mjs`: stable
  reason registry and native Claude Code response serialization.
- `skills/command-driven-operations/scripts/command-guard/audit.mjs`: minimal
  append-only JSONL audit with restrictive file creation and no secret fields.
- `skills/command-driven-operations/scripts/command-guard/bash-lexer.mjs`:
  bounded Bash-compatible lexical state machine.
- `skills/command-driven-operations/scripts/command-guard/powershell-lexer.mjs`:
  bounded lexer for explicit literal `pwsh`/`powershell -Command` payloads.
- `skills/command-driven-operations/scripts/command-guard/composition.mjs`:
  ordered stages, operators, redirections, shell-profile boundaries, and
  source-to-sink edges.
- `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`:
  immutable command families, verbs, targets, limits, risks, modifiers,
  credential positions, consumers, sources, and sinks.
- `skills/command-driven-operations/scripts/command-guard/credential-flow.mjs`:
  credential/reference classification and current-call sensitive data flow.
- `skills/command-driven-operations/scripts/command-guard/policy.mjs`:
  target binding, per-stage analysis, aggregate risk, mode-aware precedence,
  and final decision.

### Deterministic test contract

- `tests/command-guard/helpers.mjs`: subprocess runner, synthetic-secret scan,
  event builders, deterministic PRNG, and temporary audit helper.
- `tests/command-guard/contract.test.mjs`: event, output, exit, audit, timeout,
  and failure-path contract tests.
- `tests/command-guard/lexer.test.mjs`: Bash and PowerShell grammar matrix.
- `tests/command-guard/policy.test.mjs`: catalogue, risk, mode, target, scope,
  limit, modifier, and precedence matrix.
- `tests/command-guard/credentials.test.mjs`: all credential transports,
  encrypted-file direct flows, redaction, and exfiltration cases.
- `tests/command-guard/properties.test.mjs`: deterministic generators and
  monotonic safety properties.
- `tests/command-guard/coverage-manifest.mjs`: finite inventory of grammar
  productions, operators, policy IDs, reason codes, limits, and edge cases.
- `tests/command-guard/coverage.test.mjs`: orphan detection and complete finite
  matrix assertions.
- `tests/command-guard/mutations.mjs`: exact one-site mutation registry.
- `tests/command-guard/run-mutations.mjs`: temporary-copy mutation runner that
  requires every registered security mutation to be killed.
- `tests/run-command-guard-tests.mjs`: one reproducible command for unit,
  property, branch-coverage, leak-scan, and mutation gates.

### Installed/live validation and release

- `tests/live-command-guard-smoke.sh`: opt-in Nori install plus Claude Code
  behavioral probes against synthetic/disposable commands only.
- `tests/test-live-command-guard-safety.py`: static proof that the live harness
  cannot reach real infrastructure or use non-synthetic credentials.
- `tests/validation-notes.md`: prerequisites, commands, coverage meaning,
  observed-version policy, and interpretation of skipped live probes.
- `tests/validate-package.sh`: includes the new deterministic guard gate.
- `AGENTS.md`, `references/command-execution-protocol.md`,
  `references/risk-levels.md`, and
  `skills/command-driven-operations/SKILL.md`: operator/model-facing semantics.
- `docs/architecture/ADR-004-native-command-guard.md` and
  `docs/architecture/README.md`: decision and index.
- `README.md`, `docs.md`, `CHANGELOG.md`, `nori.json`, `.nori-version`: release
  metadata and user-facing behavior.
- `C:\projects\senior-infra-ops-analyst\TODO-AI-FIRST.md`: external,
  intentionally unversioned final evidence and status.

---

### Task 1: Enforce the native hook installation contract test-first

**Files:**
- Create: `tests/command_guard_install_policy.py`
- Create: `tests/test-command-guard-install-policy.py`
- Modify: `tests/validate-content.py`
- Modify: `tests/validate-installed-subagents.py`
- Modify: `tests/test-installed-subagents.py`
- Modify: `tests/live-subagent-runtime-smoke.sh`
- Modify: the eight executor files under `subagents/`

**Interfaces:**
- Produces: `EXECUTOR_AGENTS: tuple[str, ...]` and
  `ANALYTICAL_AGENTS: tuple[str, ...]`.
- Produces: `source_command_guard_hook(text: str) -> dict[str, object] | None`.
- Produces: `installed_command_guard_hook(text: str) -> dict[str, object] | None`.
- Produces: `source_hook_errors(agent_id: str, text: str) -> list[str]`.
- Produces: `installed_hook_errors(agent_id: str, source: str, installed: str,
  installed_skills_dir: Path) -> list[str]`.
- Guarantees: only executors contain exactly one `PreToolUse` matcher for
  `Bash`, and its installed validator path resolves inside the installed
  `command-driven-operations` skill.

- [ ] **Step 1: Write source-hook mutation tests**

Create tests that load all 12 source agents and assert these mutations fail:

```python
def test_executor_without_hook_is_rejected(self) -> None:
    changed = remove_command_guard_hook(self.executor_text)
    self.assert_source_error(
        "diagnostic-operator", changed, "missing command guard hook"
    )

def test_analytical_agent_with_bash_hook_is_rejected(self) -> None:
    changed = insert_command_guard_hook(self.analyst_text)
    self.assert_source_error(
        "change-manager", changed, "analytical agent declares Bash hook"
    )

def test_broadened_matcher_is_rejected(self) -> None:
    changed = self.executor_text.replace("matcher: Bash", "matcher: *", 1)
    self.assert_source_error(
        "diagnostic-operator", changed, "matcher must be exactly Bash"
    )

def test_shell_string_hook_is_rejected(self) -> None:
    changed = self.executor_text.replace(
        "command: node\n          args:",
        "command: node {{skills_dir}}/command-driven-operations/scripts/validate-ops-command.mjs\n          args:",
        1,
    )
    self.assert_source_error(
        "diagnostic-operator", changed, "hook must use canonical exec form"
    )

def test_hook_timeout_drift_is_rejected(self) -> None:
    changed = self.executor_text.replace("timeout: 5", "timeout: 30", 1)
    self.assert_source_error(
        "diagnostic-operator", changed, "hook timeout must be 5 seconds"
    )
```

- [ ] **Step 2: Run the source-hook tests and verify red**

Run:

```bash
python3 tests/test-command-guard-install-policy.py
```

Expected: failures show that the policy module and hooks do not exist.

- [ ] **Step 3: Implement the exact source policy parser**

Use a line/indentation parser, not a permissive YAML dependency. The canonical
semantic object is:

```python
CANONICAL_SOURCE_HOOK = {
    "matcher": "Bash",
    "type": "command",
    "command": "node",
    "args": (
        "{{skills_dir}}/command-driven-operations/scripts/validate-ops-command.mjs",
    ),
    "timeout": 5,
}
```

Reject duplicate `hooks`, duplicate `PreToolUse`, multiple `Bash` matchers,
extra command arguments, scalar shell commands, unknown nested keys, aliases,
anchors, tags, tabs, and malformed indentation. Return all deterministic
errors rather than stopping at the first agent.

- [ ] **Step 4: Add the exact hook to all eight executors**

Insert this block after `skills` and before the closing frontmatter delimiter:

```yaml
hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: node
          args:
            - "{{skills_dir}}/command-driven-operations/scripts/validate-ops-command.mjs"
          timeout: 5
```

Apply it only to `diagnostic-operator`, `observability-sre`,
`cloud-platform-operator`, `kubernetes-operator`, `database-operator`,
`network-edge-operator`, `release-cicd-operator`, and
`audit-evidence-collector`.

- [ ] **Step 5: Integrate source validation and verify green**

Import `source_hook_errors` in `tests/validate-content.py`, call it beside
`runtime_control_errors`, and rerun:

```bash
python3 tests/test-command-guard-install-policy.py
python3 tests/validate-content.py
```

Expected: both commands exit `0`.

- [ ] **Step 6: Write installed-artifact mutation tests**

Extend the installed fixture to include an `installed_skills_dir`, replace
`{{skills_dir}}` in copied agents, and cover missing script, unresolved
placeholder, path outside the installed skill, changed matcher, added arg,
wrong timeout, and an analytical agent gaining the hook.

- [ ] **Step 7: Extend installed validation**

Add required CLI argument:

```python
parser.add_argument(
    "--installed-skills-dir",
    required=True,
    type=Path,
    help="Claude Code skills directory produced by Nori",
)
```

Require the installed arg to equal
`installed_skills_dir / "command-driven-operations" / "scripts" /
"validate-ops-command.mjs"`, require that file to exist, and compare every
other hook field semantically with the source.

Update the existing P0-03 live smoke call to pass its discovered installed
skills directory through `--installed-skills-dir`; its runtime-control smoke
must remain green after the validator contract expands.

- [ ] **Step 8: Run installed tests and commit**

Run:

```bash
python3 tests/test-installed-subagents.py
python3 tests/validate-content.py
```

Expected: all tests pass. Then commit:

```bash
git add tests/command_guard_install_policy.py \
  tests/test-command-guard-install-policy.py tests/validate-content.py \
  tests/validate-installed-subagents.py tests/test-installed-subagents.py \
  tests/live-subagent-runtime-smoke.sh subagents
git commit -m "feat: install native executor command guard hooks"
```

---

### Task 2: Build strict contract, redaction, response, and audit primitives

**Files:**
- Create: `skills/command-driven-operations/scripts/command-guard/limits.mjs`
- Create: `skills/command-driven-operations/scripts/command-guard/contract.mjs`
- Create: `skills/command-driven-operations/scripts/command-guard/redaction.mjs`
- Create: `skills/command-driven-operations/scripts/command-guard/response.mjs`
- Create: `skills/command-driven-operations/scripts/command-guard/audit.mjs`
- Create: `tests/command-guard/helpers.mjs`
- Create: `tests/command-guard/contract.test.mjs`

**Interfaces:**
- Produces: `parseHookEvent(raw: string) -> HookEvent`.
- Produces: `readBoundedStdin(stream, maxBytes) -> Promise<string>` using a
  fatal UTF-8 decoder.
- Produces: `detectSensitiveSpans(command: string) -> SensitiveSpan[]`.
- Produces: `redactText(text: string, spans?: SensitiveSpan[]) -> string`.
- Produces: `normalizeAndFingerprint(command: string, spans: SensitiveSpan[])
  -> { normalized: string, fingerprint: string }`.
- Produces: `decisionResponse(result: PolicyResult) -> object`.
- Produces: `appendAudit(result: PolicyResult, event: HookEvent, env?: object)
  -> void`.

Use these exact JSDoc data shapes:

```javascript
/** @typedef {{sessionId:string, agentType:string, permissionMode:string,
 * command:string, timeoutMs:number|null, runInBackground:false}} HookEvent */
/** @typedef {{start:number, end:number, kind:string}} SensitiveSpan */
/** @typedef {'SAFE_READ_ONLY'|'LOW_RISK_CHANGE'|'DISRUPTIVE_CHANGE'|'DESTRUCTIVE'} Risk */
/** @typedef {'allow'|'ask'|'deny'} Decision */
```

- [ ] **Step 1: Write boundary and malformed-input tests**

Test empty input, whitespace, BOM, invalid UTF-8 through subprocess fixtures,
trailing JSON, duplicate `hook_event_name`, duplicate `tool_input`, non-object
roots, excessive nesting, arrays where objects are required, prototype-like
keys, missing fields, wrong scalar types, empty strings, negative/non-finite
timeouts, unknown tool fields, background execution, and every `n-1`, `n`,
`n+1` limit.

The valid event builder is:

```javascript
export function validEvent(overrides = {}) {
  return {
    session_id: 'session-synthetic-001',
    hook_event_name: 'PreToolUse',
    agent_type: 'diagnostic-operator',
    permission_mode: 'default',
    tool_name: 'Bash',
    tool_input: { command: 'uname -a' },
    ...overrides,
  };
}
```

- [ ] **Step 2: Run contract tests and verify red**

Run:

```bash
node --test tests/command-guard/contract.test.mjs
```

Expected: module-not-found failures.

- [ ] **Step 3: Define all bounds in one module**

Export exactly:

```javascript
export const LIMITS = Object.freeze({
  inputBytes: 131072,
  jsonDepth: 16,
  commandChars: 32768,
  timeoutMs: 120000,
  stages: 8,
  redirects: 8,
  tokens: 512,
  tokenChars: 8192,
  outputRows: 1000,
  fanOut: 20,
  auditFieldChars: 512,
});
export const EXECUTOR_AGENTS = Object.freeze([
  'audit-evidence-collector', 'cloud-platform-operator',
  'database-operator', 'diagnostic-operator', 'kubernetes-operator',
  'network-edge-operator', 'observability-sre', 'release-cicd-operator',
]);
export const NORMAL_MODES = Object.freeze([
  'default', 'plan', 'acceptEdits', 'auto', 'dontAsk',
]);
```

- [ ] **Step 4: Implement duplicate-key-safe parsing and strict validation**

Read stdin as bounded bytes and decode with
`new TextDecoder('utf-8', {fatal: true})`. Before `JSON.parse`, scan JSON
tokens with string/escape awareness and reject duplicate security-sensitive
keys at any object depth. Reject keys not in the exact event/tool-input
allowlists. Enforce bounded depth and byte/character limits before constructing
the returned frozen `HookEvent`.

- [ ] **Step 5: Implement redaction before normalization and hashing**

Recognize current-call literal shapes for authorization headers, cookies, URI
userinfo, connection strings, known secret environment variables, password or
token flags, private-key blocks, and PowerShell secure-string literals. Merge
overlapping spans, replace each with `<redacted:KIND>`, normalize whitespace
only after replacement, and SHA-256 only the redacted normalized command.

Add tests proving a marker such as `SYNTH_SECRET_4f0a7c` never appears in
normalized text, fingerprints, thrown errors, JSON decisions, audit, stdout,
or stderr.

- [ ] **Step 6: Implement stable response semantics**

Export a frozen reason registry containing at least:

```javascript
export const REASONS = Object.freeze({
  ALLOW_NARROW_READ: 'ALLOW_NARROW_READ',
  ALLOW_BYPASS_CATALOGUED_CHANGE: 'ALLOW_BYPASS_CATALOGUED_CHANGE',
  ASK_NORMAL_MODE_CHANGE: 'ASK_NORMAL_MODE_CHANGE',
  ASK_DESTRUCTIVE: 'ASK_DESTRUCTIVE',
  ASK_LITERAL_CREDENTIAL_NORMAL: 'ASK_LITERAL_CREDENTIAL_NORMAL',
  DENY_SCHEMA: 'DENY_SCHEMA',
  DENY_BACKGROUND: 'DENY_BACKGROUND',
  DENY_UNKNOWN_COMMAND: 'DENY_UNKNOWN_COMMAND',
  DENY_UNSUPPORTED_SYNTAX: 'DENY_UNSUPPORTED_SYNTAX',
  DENY_AMBIGUOUS_TARGET: 'DENY_AMBIGUOUS_TARGET',
  DENY_LIMIT: 'DENY_LIMIT',
  DENY_SECRET_OUTPUT: 'DENY_SECRET_OUTPUT',
  DENY_SECRET_EXFILTRATION: 'DENY_SECRET_EXFILTRATION',
  DENY_SECRET_PERSISTENCE: 'DENY_SECRET_PERSISTENCE',
  DENY_UNKNOWN_CREDENTIAL_CONSUMER: 'DENY_UNKNOWN_CREDENTIAL_CONSUMER',
  DENY_AUTH_REDIRECT: 'DENY_AUTH_REDIRECT',
  DENY_INTERNAL: 'DENY_INTERNAL',
  UNKNOWN_MODE_CONSERVATIVE: 'UNKNOWN_MODE_CONSERVATIVE',
});
```

`deny` includes the same redacted summary in `systemMessage` and
`permissionDecisionReason`; `ask` uses only the native reason field; `allow`
has no operator warning. Serialization must produce exactly one JSON object.

- [ ] **Step 7: Implement minimal append-only audit**

Resolve the audit file from absolute `OPS_COMMAND_GUARD_AUDIT_PATH` when set,
otherwise from
`path.join(os.homedir(), '.claude', 'senior-infra-ops-analyst',
'command-guard-audit.jsonl')`. Create directories and file with mode `0o700`
and `0o600` where supported. Append only timestamp, session ID, agent, mode,
risk, modifiers, policy ID, non-sensitive target/environment/scope,
credential classification metadata, redacted fingerprint, decision, reason,
and stage. Reject oversize fields and any object key named `command`, `secret`,
`password`, `token`, `cookie`, `authorization`, or `transcript`.

- [ ] **Step 8: Verify primitives and commit**

Run:

```bash
node --test tests/command-guard/contract.test.mjs
```

Expected: all tests pass. Commit:

```bash
git add skills/command-driven-operations/scripts/command-guard \
  tests/command-guard/helpers.mjs tests/command-guard/contract.test.mjs
git commit -m "feat: add command guard contract and redaction primitives"
```

---

### Task 3: Implement bounded Bash and explicit PowerShell lexers

**Files:**
- Create: `skills/command-driven-operations/scripts/command-guard/bash-lexer.mjs`
- Create: `skills/command-driven-operations/scripts/command-guard/powershell-lexer.mjs`
- Create: `tests/command-guard/lexer.test.mjs`

**Interfaces:**
- Produces: `lexBash(command: string, limits = LIMITS) -> LexResult`.
- Produces: `lexPowerShell(command: string, limits = LIMITS) -> LexResult`.
- Produces `Token` objects with `{kind, raw, cooked, quote, start, end}`.
- Produces `LexResult` with `{profile, tokens, unsupported, sensitiveHints}`.
- Guarantees: lexers never expand variables, globs, aliases, substitutions,
  paths, or execute any input.

- [ ] **Step 1: Write the complete operator/quoting matrix**

Cover Bash `|`, `|&`, `&&`, `||`, `;`, newline, `<`, `>`, `>>`, `2>`,
`2>&1`, and `&`; PowerShell `|`, `&&`, `||`, `;`, newline, `>`, `>>`, `2>`,
and `*>`. For every operator, test unquoted, single-quoted, double-quoted,
escaped, adjacent to words, repeated, missing left/right stage, CRLF, and LF.

Explicitly reject `$()`, backticks, process substitution, here-documents,
here-strings, functions, aliases, dot sourcing, Bash arithmetic/brace
expansion, PowerShell subexpressions, call operator, splatting, script blocks,
stop-parsing token, encoded commands, `eval`, `Invoke-Expression`, dynamic
`sh -c`, `cmd /c`, Python/Node command strings, command-building `xargs`,
null/control characters, bidi controls, zero-width characters, homoglyphs,
operator lookalikes, base64/hex/percent-encoded command payloads, and escaped
or non-normalized Unicode.

Also cover path traversal, symlink-sensitive paths, globs, relative/absolute/
UNC/drive-qualified/spaced/dashed/reserved/case-variant paths, authenticated
redirects, downloads, remote scripts, packet-capture bounds, fan-out, broad
logs, and resource-intensive queries. Lexer tests only establish syntax;
policy tests must prove the corresponding unsupported or bounded decision.

- [ ] **Step 2: Run lexer tests and verify red**

Run:

```bash
node --test tests/command-guard/lexer.test.mjs
```

Expected: missing lexer modules.

- [ ] **Step 3: Implement the Bash state machine**

Use explicit states `UNQUOTED`, `SINGLE_QUOTED`, `DOUBLE_QUOTED`, and
`ESCAPED`. Preserve offsets and both raw/cooked token forms. Stop at the first
unsupported construct with a stable syntax code; do not attempt recovery that
could merge stages. Enforce token count/size during scanning.

- [ ] **Step 4: Implement the PowerShell state machine**

Use explicit states for unquoted, single-quoted, expandable double-quoted, and
backtick-escaped text. Permit PowerShell parsing only for a literal payload
bound to `pwsh|powershell -NoProfile -Command <literal>` by the outer Bash
analysis. Dynamic `-Command`, `-EncodedCommand`, `Invoke-Expression`, and
subexpressions remain unsupported.

- [ ] **Step 5: Add deterministic equivalence and non-execution tests**

Assert repeated parsing is byte-for-byte identical, quoted separators remain
arguments, real separators remain operators, and fixture strings containing
`touch`, `Remove-Item`, or network URLs produce no filesystem/network effect.

- [ ] **Step 6: Verify and commit**

Run the lexer and contract suites, then commit:

```bash
node --test tests/command-guard/contract.test.mjs \
  tests/command-guard/lexer.test.mjs
git add skills/command-driven-operations/scripts/command-guard \
  tests/command-guard/lexer.test.mjs
git commit -m "feat: add bounded shell lexers"
```

---

### Task 4: Build the command graph and finite operational catalogue

**Files:**
- Create: `skills/command-driven-operations/scripts/command-guard/composition.mjs`
- Create: `skills/command-driven-operations/scripts/command-guard/catalogue.mjs`
- Create: `tests/command-guard/policy.test.mjs`

**Interfaces:**
- Produces: `buildComposition(lexed: LexResult) -> Composition`.
- Produces: `lookupFamily(stage: CommandStage) -> FamilyMatch | null`.
- Produces: frozen `COMMAND_FAMILIES`, `FILTER_FAMILIES`, `POLICY_IDS`, and
  `GRAMMAR_PRODUCTIONS`.
- `Composition` contains `{stages, operators, redirects, edges}` and never raw
  secret values after sensitive spans are attached.

- [ ] **Step 1: Write composition tests before implementation**

Cover one stage, exact eight stages, nine stages, each supported operator,
stage reordering, conditional branches, mixed risk, input/output redirects,
descriptor duplication, separately safe source/sink becoming unsafe, explicit
PowerShell wrapper payload, unknown stages, and aggregate target conflicts.

- [ ] **Step 2: Define the complete initial catalogue table**

Encode these family IDs and aliases; unlisted verbs/options deny:

| Family ID | Aliases | Read | Low-risk change | Disruptive | Destructive |
|---|---|---|---|---|---|
| `POSIX_HOST_READ` | `uname`,`uptime`,`free`,`df`,`ps`,`ss`,`ip`,`lsblk`,`mount`,`findmnt` | bounded documented read flags | — | — | — |
| `LOG_READ` | `journalctl`,`dmesg` | bounded time/unit/line queries | — | — | — |
| `SERVICE_CONTROL` | `systemctl`,`service` | `status`,`show`,`is-active`,`is-enabled` | `enable`,`disable` | `start`,`stop`,`restart`,`reload`,`daemon-reload`,`mask`,`unmask` | — |
| `KUBERNETES` | `kubectl`,`k3s kubectl` | `get`,`describe`,`logs`,`events`,`auth can-i`,`version`,`cluster-info` | `label`,`annotate`,`set image` | `apply`,`patch`,`scale`,`rollout restart`,`cordon`,`uncordon` | `delete`,`drain`,`replace --force` |
| `CONTAINER` | `docker`,`podman`,`nerdctl`,`ctr`,`crictl` | `ps`,`inspect`,`logs`,`stats --no-stream`,`images`,`info` | `pull`,`tag`,`rename` | `start`,`stop`,`restart`,`pause`,`unpause` | `rm`,`rmi`,`prune`,`system reset` |
| `AWS` | `aws` | `describe-*`,`get-*`,`list-*`,`head-*` | `ec2 create-tags`,`ec2 delete-tags` | explicit `start-*`,`stop-*`,`reboot-*`,`update-*` | explicit `delete-*`,`terminate-*`,`deregister-*` |
| `AZURE` | `az` | `show`,`list` using provider-managed authentication | `tag create`,`tag update`,`tag delete` | explicit `start`,`stop`,`restart`,`update` | explicit `delete`,`purge` |
| `GCP` | `gcloud`,`gsutil` | `describe`,`list`,`get-iam-policy` | `add-labels`,`remove-labels` | explicit `start`,`stop`,`reset`,`update` | explicit `delete` and bucket removal |
| `POSTGRES` | `psql`,`pg_isready` | connection/status and SQL beginning `SELECT`,`SHOW`,`EXPLAIN` without `ANALYZE` | catalogued `SET` session-only | `VACUUM`,`ANALYZE`,`REINDEX` | DDL/DML, `DROP`,`TRUNCATE`,`DELETE`,`UPDATE`,`INSERT` |
| `MYSQL` | `mysql`,`mysqladmin` | `SELECT`,`SHOW`,`EXPLAIN`,`STATUS`,`PING` | session-only `SET` | `FLUSH`,`OPTIMIZE`,`ANALYZE`,`REPAIR` | DDL/DML and shutdown |
| `MONGODB` | `mongosh` | `find`,`findOne`,`explain`,`serverStatus`,`replSetGetStatus` | — | reconfiguration and maintenance | writes, drops, shutdown |
| `REDIS` | `redis-cli` | `PING`,`INFO`,`GET`,`MGET`,`SCAN` with count bound | `EXPIRE`,`PERSIST` | `CLIENT KILL`,`REPLICAOF` | `DEL`,`FLUSH*`,`SHUTDOWN`,`CONFIG SET` |
| `NETWORK_READ` | `ping`,`traceroute`,`tracepath`,`dig`,`nslookup`,`host`,`curl` | bounded probes and HTTP `GET`,`HEAD` | — | — | authenticated mutation follows `HTTP` |
| `PACKET_CAPTURE` | `tcpdump`,`tshark` | explicit interface, host/port filter, packet count, duration, and snap length | — | — | — |
| `HTTP` | `curl`,`Invoke-RestMethod`,`Invoke-WebRequest` | explicit-origin `GET`,`HEAD` | `PUT`,`PATCH`,`POST` when catalogued by exact origin policy | service-affecting endpoint action | `DELETE` or destructive endpoint action |
| `REMOTE` | `ssh`,`scp`,`sftp` | explicit host plus a catalogued literal remote read command | explicit file transfer to known target | catalogued remote control command | remote destructive command |
| `PRIVILEGE` | `sudo`,`runas` | wraps one catalogued command | inherits wrapped command | inherits wrapped command | inherits wrapped command |
| `GIT_CI` | `git`,`gh` | status/log/diff/show/branch-list and read-only PR/check/run views | local branch/tag metadata changes | workflow rerun/cancel and deployment actions | force push, branch/tag deletion, destructive cleanup |
| `POWERSHELL_READ` | `Get-*`,`Test-*`,`Resolve-DnsName`,`Get-CimInstance` | bounded object reads | — | — | — |
| `WINDOWS_CONTROL` | `Restart-Service`,`Start-Service`,`Stop-Service`,`Set-Service` | — | `Set-Service` metadata/startup change | start/stop/restart | destructive OS/storage/account actions |

Require explicit target selectors for every mutating or remote family. Encode
family-specific bounds for namespace, region/account/profile, project,
subscription, host, database endpoint, service unit, URL origin, rows, logs,
fan-out, and timeout. Treat current context as acceptable only for narrow local
reads.

Classify packet capture and broad-but-bounded logs with
`SENSITIVE_OUTPUT`/`RESOURCE_INTENSIVE`, and active network probes with
`ACTIVE_PROBE`; these become bounded reads that require `ask` in normal modes
and may `allow` in `bypassPermissions`. Parse an SSH literal remote command
recursively with the Bash lexer, require one catalogued foreground stage, and
deny dynamic or composed remote payloads.

- [ ] **Step 3: Define the bounded filter catalogue**

Permit only `grep`, `rg`, `head`, `tail`, `cut`, `sort`, `uniq`, `wc`,
`sed -n`, `awk` without system/pipe functions, `jq` without file/network
modules, and PowerShell `Where-Object`, `Select-Object`, `Sort-Object`,
`Group-Object`, `Measure-Object`, and `Format-Table`. Every filter must have a
finite input edge and may not become a command constructor or file/network
sink.

- [ ] **Step 4: Implement command graph construction**

Bind ordered `stdout -> stdin`, conditional, sequence, and redirect edges.
Represent `/dev/null` and `NUL` as discard sinks. Treat all other output files
as state-changing sinks whose path must be literal and explicitly permitted by
the matched family; do not authorize generic arbitrary-file output.

- [ ] **Step 5: Verify the catalogue and commit**

Run:

```bash
node --test tests/command-guard/lexer.test.mjs \
  tests/command-guard/policy.test.mjs
```

Expected: catalogue and composition cases pass. Commit:

```bash
git add skills/command-driven-operations/scripts/command-guard \
  tests/command-guard/policy.test.mjs
git commit -m "feat: add operational command catalogue and graph"
```

---

### Task 5: Enforce credential transports and sensitive data flow

**Files:**
- Create: `skills/command-driven-operations/scripts/command-guard/credential-flow.mjs`
- Create: `tests/command-guard/credentials.test.mjs`

**Interfaces:**
- Produces: `classifyCredentials(composition: Composition, command: string,
  spans: SensitiveSpan[]) -> CredentialAnalysis`.
- Produces: `credentialFlowErrors(composition: Composition,
  analysis: CredentialAnalysis) -> PolicyFinding[]`.
- `CredentialAnalysis` contains only non-secret `{source, type, domain,
  identity, transport, stage, literal}` metadata.

- [ ] **Step 1: Write synthetic tests for every supported transport**

Cover SSH agent/askpass/`sshpass`, sudo timestamp/askpass/`sudo -S`, database
environment/flag/URI/file, HTTP Basic/Bearer/cookie/client certificate/header,
PowerShell `PSCredential`/secure string/credential/header, AWS/Azure/GCP
profiles and cached sessions, kubeconfig/exec plugins, Git helpers, and generic
`PASSWORD|PASS|TOKEN|SECRET|KEY|CREDENTIAL` variables.

For each transport test reference and literal variants with empty, repeated,
quoted, escaped, Unicode, percent-encoded, spaces, delimiters, and shell
operators. Add benign lookalikes such as `monkey`, `keyspace`, and
`tokenization` to control false positives.

- [ ] **Step 2: Run credential tests and verify red**

Run:

```bash
node --test tests/command-guard/credentials.test.mjs
```

Expected: missing credential analyzer.

- [ ] **Step 3: Classify references separately from literals**

Use `REFERENCE`, `PROVIDER_CACHE`, `RUNTIME_VARIABLE`, `STDIN_DIRECT`,
`PROTECTED_FILE`, and `MODEL_VISIBLE_LITERAL`. A literal classification is a
current-tool-call handling class, not proof of conversational origin. Store no
value or derivative in `CredentialAnalysis`.

- [ ] **Step 4: Enforce direct consumers and deny unsafe sinks**

Allow sensitive input only when the destination stage declares the exact
transport it consumes. Deny display (`echo`, `printf`, `Write-Output`,
`Out-Host`), logs, generic files, clipboard, ticket/CLI messaging, unrelated
processes, unknown URLs, authenticated redirect to a different origin,
background jobs, dynamic destinations, and unsupported command families.

- [ ] **Step 5: Implement encrypted-file direct flow**

Catalogue `gpg --decrypt`, `gpg -d`, and `age --decrypt` as sensitive sources
only when their output flows directly to `sudo -S`, `sshpass -d 0`, or another
consumer whose family explicitly declares stdin credential consumption. Deny
display, `tee`, intermediate files, multiple consumers, background execution,
and any filter between decryptor and consumer.

- [ ] **Step 6: Test mode and reuse boundaries without false claims**

Deterministic tests repeat literal-bearing calls and prove every call is
independently analyzed. They cover normal-mode escalation, bypass operation
policy, destructive `ask`, changed effective mode, ambiguous current binding,
and exfiltration `deny`. They must explicitly assert that the hook output/audit
does not claim prior-secret equality, transcript provenance, or context
retention.

- [ ] **Step 7: Verify secret absence and commit**

Run credential, contract, and policy tests, scan all captured artifacts for
every synthetic marker, then commit:

```bash
node --test tests/command-guard/contract.test.mjs \
  tests/command-guard/policy.test.mjs \
  tests/command-guard/credentials.test.mjs
git add skills/command-driven-operations/scripts/command-guard/credential-flow.mjs \
  tests/command-guard/credentials.test.mjs
git commit -m "feat: enforce credential data flow"
```

---

### Task 6: Implement mode-aware policy and the fail-closed entrypoint

**Files:**
- Create: `skills/command-driven-operations/scripts/command-guard/policy.mjs`
- Create: `skills/command-driven-operations/scripts/validate-ops-command.mjs`
- Modify: `tests/command-guard/policy.test.mjs`
- Modify: `tests/command-guard/contract.test.mjs`

**Interfaces:**
- Produces: `analyzeCommand(event: HookEvent) -> PolicyResult`.
- Produces: `decide(findings: PolicyFinding[], event: HookEvent) -> PolicyResult`.
- Entry point consumes exactly one stdin JSON event, appends one audit record,
  prints one decision JSON object for understood policy paths, and exits `2`
  without `allow` on contract, internal, timeout, serialization, or audit
  failure.

- [ ] **Step 1: Write the complete permission/risk decision matrix**

Encode this expected table for every normal mode separately, unknown future
mode, and `bypassPermissions`:

```javascript
const EXPECTED = {
  SAFE_READ_ONLY: { normal: 'allow', bypassPermissions: 'allow' },
  BOUNDED_READ_WITH_APPROVAL_MODIFIER: {
    normal: 'ask', bypassPermissions: 'allow',
  },
  LOW_RISK_CHANGE: { normal: 'ask', bypassPermissions: 'allow' },
  DISRUPTIVE_CHANGE: { normal: 'ask', bypassPermissions: 'allow' },
  DESTRUCTIVE: { normal: 'ask', bypassPermissions: 'ask' },
  FORBIDDEN_OR_INCONCLUSIVE: { normal: 'deny', bypassPermissions: 'deny' },
  CREDENTIAL_EXFILTRATION: { normal: 'deny', bypassPermissions: 'deny' },
};
```

Literal credentials raise a normal-mode decision to at least `ask` but do not
change the operational risk. Unknown modes use normal-mode semantics and add
`UNKNOWN_MODE_CONSERVATIVE`.

- [ ] **Step 2: Write precedence and target tests**

Assert `deny > ask > allow`; credential exfiltration cannot become
destructive `ask`; a fully analyzed destructive command cannot become `deny`
solely because it is destructive; any mutating/remote command with implicit,
variable-derived, conflicting, or over-broad target denies; changing any
argument, stage, operator, redirect, target, environment, scope, transport,
timeout, or background flag yields a fresh fingerprint and evaluation.

- [ ] **Step 3: Run policy tests and verify red**

Run:

```bash
node --test tests/command-guard/policy.test.mjs
```

Expected: missing policy engine.

- [ ] **Step 4: Implement per-stage and aggregate policy**

Analyze each matched stage, bind explicit target/environment/scope, apply
family bounds, merge risk modifiers, evaluate data-flow edges, and then apply
decision precedence. Use stable policy IDs from the catalogue in every result.
Never use substring or regex matching alone to authorize an executable or
verb.

- [ ] **Step 5: Implement the entrypoint orchestration**

The exact order is:

```javascript
const event = parseHookEvent(await readBoundedStdin(LIMITS.inputBytes));
const sensitive = detectSensitiveSpans(event.command);
const result = analyzeCommand(event, sensitive);
const safe = attachRedactedFingerprint(result, event.command, sensitive);
appendAudit(safe, event, process.env);
process.stdout.write(`${JSON.stringify(decisionResponse(safe))}\n`);
```

Wrap the entire path so exceptions produce one redacted stderr line and exit
`2`; never emit an `allow` object from a catch/finally path. Reject stdout
pollution by keeping all modules silent.

- [ ] **Step 6: Test forced failures at every stage**

Inject test-only dependencies through an exported `runGuard({read,
parse,analyze,fingerprint,audit,serialize,write})` function and force failure in
each dependency. Assert exit `2`, no `allow`, no synthetic marker, and no
partial second JSON object. The production CLI passes only real dependencies
and exposes no environment variable that disables a policy predicate.

- [ ] **Step 7: Verify entrypoint behavior and commit**

Run:

```bash
node --test tests/command-guard/contract.test.mjs \
  tests/command-guard/lexer.test.mjs \
  tests/command-guard/policy.test.mjs \
  tests/command-guard/credentials.test.mjs
```

Expected: all tests pass. Commit:

```bash
git add skills/command-driven-operations/scripts \
  tests/command-guard/contract.test.mjs \
  tests/command-guard/policy.test.mjs
git commit -m "feat: enforce mode-aware command decisions"
```

---

### Task 7: Make finite coverage, property, fuzz, and mutation gates exhaustive

**Files:**
- Create: `tests/command-guard/coverage-manifest.mjs`
- Create: `tests/command-guard/coverage.test.mjs`
- Create: `tests/command-guard/properties.test.mjs`
- Create: `tests/command-guard/mutations.mjs`
- Create: `tests/command-guard/run-mutations.mjs`
- Create: `tests/run-command-guard-tests.mjs`
- Modify: `tests/validate-package.sh`

**Interfaces:**
- Produces: `COVERAGE_MANIFEST` mapping every finite production item to
  positive, boundary, and negative case IDs.
- Produces: recorded deterministic seeds and minimized regression fixtures.
- Produces: `MUTATIONS` whose IDs match all exported security predicate IDs.
- Produces one command, `node tests/run-command-guard-tests.mjs`, that blocks
  release on test, coverage, artifact leak, orphan, seed, or surviving mutation.

- [ ] **Step 1: Write orphan tests first**

Mutate a copied manifest by adding one grammar production, operator, command
family, policy ID, reason code, limit, credential transport, or edge-case ID
without cases. Each mutation must fail with the exact orphan ID.

- [ ] **Step 2: Build the finite coverage manifest**

Import exported inventories from production modules and map every member to
case IDs. Require at least one positive, `n-1/n/n+1` boundary where numeric,
and one negative case per applicable item. Require every test case ID to map
back to an inventory member so stale cases also fail.

- [ ] **Step 3: Add deterministic property/fuzz generators**

Use a local xorshift32 generator with recorded seeds
`0x04c0ffee`, `0x51a7e001`, `0x7f00aa55`, and `0xd15ea5ed`. Generate bounded
valid and invalid token streams for both lexers. Assert:

- malformed, unknown, ambiguous, or over-limit input never allows;
- parsing and normalization are deterministic and side-effect free;
- redaction is idempotent and synthetic markers never survive output;
- adding an unknown stage or unsafe source-to-sink edge never weakens a
  decision;
- moving a bound from inside to outside policy never preserves `allow`;
- real separators remain operators and quoted separators remain arguments;
- any exception/failure prevents execution and an `allow` result.

Minimize every discovered failure into a named static case before changing
the implementation.

- [ ] **Step 4: Register exact security mutations**

Cover every decision-precedence comparison, risk escalation, target-required
predicate, bound comparison, unknown-family rejection, background rejection,
credential source/sink rejection, redaction rule, audit forbidden-field rule,
and catch-path exit. Each mutation specifies one file, one exact source string,
one replacement, and requires exactly one replacement in a temporary copy.

- [ ] **Step 5: Implement the mutation runner**

For each registered mutation, copy only guard modules to a temporary
directory, apply the one-site change, point a dedicated invariant test at the
temporary module root, and require a non-zero test exit. A mutation that cannot
be applied exactly once or whose tests still pass blocks the gate. Delete only
the runner-created verified temporary directory.

- [ ] **Step 6: Enforce 100% critical branch coverage**

Run Node's native test coverage with branch, function, and line thresholds of
100 for `contract.mjs`, `redaction.mjs`, `response.mjs`, `bash-lexer.mjs`,
`powershell-lexer.mjs`, `composition.mjs`, `credential-flow.mjs`, `policy.mjs`,
`audit.mjs`, and the entrypoint orchestration. Fail with an explicit capability
message if the observed Node runtime lacks the native coverage flags; record
the version as evidence, never as a compatibility allowlist.

- [ ] **Step 7: Integrate the complete deterministic gate**

Add this before package schema validation:

```bash
node tests/run-command-guard-tests.mjs
python3 tests/test-command-guard-install-policy.py
```

The runner executes unit, finite matrix, property/fuzz, coverage, mutation,
and retained-artifact leak scans.

- [ ] **Step 8: Run the gate and commit**

Run:

```bash
node tests/run-command-guard-tests.mjs
bash tests/validate-package.sh
```

Expected: zero failures, 100% critical branch/function/line coverage, no
orphans, all four seeds pass, every mutation is killed, and no synthetic
secret is retained. Commit:

```bash
git add tests/command-guard tests/run-command-guard-tests.mjs \
  tests/validate-package.sh
git commit -m "test: enforce exhaustive command guard coverage"
```

---

### Task 8: Validate Nori installation and live Claude Code behavior

**Files:**
- Create: `tests/live-command-guard-smoke.sh`
- Create: `tests/test-live-command-guard-safety.py`
- Modify: `tests/validation-notes.md`
- Modify: `tests/validate-package.sh`

**Interfaces:**
- Static safety test proves the live harness uses a generated isolated config,
  synthetic secrets, local disposable files/processes, and no real endpoints.
- Live harness records observed `node`, Nori, Claude Code, permission mode,
  platform, and model label when exposed, without gating on exact versions.
- Live harness writes a redacted report and scans all retained artifacts for
  synthetic markers before success.

- [ ] **Step 1: Write live-harness safety tests**

Require literal guards for a temporary HOME/config, loopback-only URLs,
generated local fixture commands, synthetic marker prefix, forbidden real
cloud/kube/SSH/database environment variables, no repository credential files,
no `--dangerously-skip-permissions` against a non-disposable target, and
cleanup restricted to a resolved runner-created directory.

- [ ] **Step 2: Run safety tests and verify red**

Run:

```bash
python3 tests/test-live-command-guard-safety.py
```

Expected: live harness missing.

- [ ] **Step 3: Implement isolated Nori installation validation**

The harness creates a temporary home, activates the current worktree through
the Nori CLI discovered on `PATH`, records versions, locates installed
`.claude/agents` and `.claude/skills`, calls
`validate-installed-subagents.py --installed-agents-dir ...
--installed-skills-dir ...`, and executes the installed validator directly
with synthetic JSON events.

- [ ] **Step 4: Add installed direct guard probes**

Cover normal narrow read `allow`, normal controlled change `ask`, bypass
controlled change `allow`, destructive `ask`, unknown command `deny`, bounded
Bash pipeline, explicit PowerShell pipeline, detailed redacted denial,
malformed event exit `2`, forced unwritable audit exit `2`, and synthetic
credential direct/denied flows.

- [ ] **Step 5: Add opt-in Claude Code behavioral probes**

Against only local disposable commands, verify one normal-mode read/change,
one bypass read/change, destructive prompt/prevention, denial visibility,
same-session `MODEL_VISIBLE_LITERAL` reuse across two catalogued loopback
targets, changed domain/identity refusal, simulated missing-context reprompt,
and no claim that the hook proved secret equality. Treat inability to complete
an interactive `ask` as non-execution, never as permission downgrade.

Exercise both `--dangerously-skip-permissions` and the native
`--permission-mode bypassPermissions` form when the discovered CLI advertises
them, plus an in-session effective-mode change when supported. Set
`HISTFILE=/dev/null` in the isolated shell and assert the harness creates no
project-managed command history containing the synthetic credential.

- [ ] **Step 6: Document capability versus compatibility**

In `tests/validation-notes.md`, provide exact static, installed, and live
commands; explain that static and installed gates are mandatory, live is
opt-in because it needs local Nori/Claude configuration, and observed versions
are evidence rather than pins. Document Git Bash and WSL invocation variants.

- [ ] **Step 7: Verify and commit**

Run:

```bash
python3 tests/test-live-command-guard-safety.py
bash tests/live-command-guard-smoke.sh --self-test
bash tests/validate-package.sh
```

If configured credentials and a disposable runtime are available, also run:

```bash
bash tests/live-command-guard-smoke.sh --run-live
```

Commit static/self-test support and any redacted live report separately from
runtime credentials:

```bash
git add tests/live-command-guard-smoke.sh \
  tests/test-live-command-guard-safety.py tests/validation-notes.md \
  tests/validate-package.sh
git commit -m "test: validate installed command guard behavior"
```

---

### Task 9: Align model-facing operational and credential instructions

**Files:**
- Modify: `AGENTS.md`
- Modify: `references/command-execution-protocol.md`
- Modify: `references/risk-levels.md`
- Modify: `skills/command-driven-operations/SKILL.md`
- Modify: the eight executor files under `subagents/`
- Modify: `tests/validate-content.py`
- Modify: `tests/test-subagent-frontmatter.py`

**Interfaces:**
- Produces one canonical model-facing rule set for permission modes,
  `allow`/`ask`/`deny`, credential reuse, current-call re-evaluation, and
  transcript limitations.
- Guarantees agent prose does not contradict the deterministic policy or
  reintroduce unconditional approval requirements in `bypassPermissions`.

- [ ] **Step 1: Add failing content mutation tests**

Require every executor to state that it must obey hook output; may reuse an
operator-supplied credential only in the same `bypassPermissions` session,
domain, identity, and transport; may use different explicit catalogued targets
in that domain; must re-evaluate each command; must not treat credential reuse
as command approval; must reprompt after mode/session/context loss; and must
never reconstruct, persist, echo, hash, or search the transcript for a secret.

- [ ] **Step 2: Update the canonical execution protocol**

Replace unconditional change-approval prose with the exact mode-aware matrix.
Document `MODEL_VISIBLE_LITERAL`, the two-layer reuse contract, direct
decryptor-to-consumer flow, preferred helper/cache mechanisms, and the fact
that prompt entry is already model/provider/transcript-visible.

- [ ] **Step 3: Update all executor instructions**

Add the same concise `## Native command guard` section to each executor. It
must direct the agent to reformulate a `deny`, use the native prompt for `ask`,
proceed only on `allow`, never claim a rejected call was approved, and preserve
the credential invariants above. Do not add the section to analytical agents
that lack `Bash`.

- [ ] **Step 4: Verify prose/guard consistency and commit**

Run:

```bash
python3 tests/test-subagent-frontmatter.py
python3 tests/validate-content.py
node tests/run-command-guard-tests.mjs
```

Commit:

```bash
git add AGENTS.md references/command-execution-protocol.md \
  references/risk-levels.md skills/command-driven-operations/SKILL.md \
  subagents tests/validate-content.py tests/test-subagent-frontmatter.py
git commit -m "docs: align agents with native command authorization"
```

---

### Task 10: Record ADR-004 and release version 0.11.0

**Files:**
- Create: `docs/architecture/ADR-004-native-command-guard.md`
- Modify: `docs/architecture/README.md`
- Modify: `tests/test-architecture-docs.py`
- Modify: `tests/validate-content.py`
- Modify: `README.md`
- Modify: `docs.md`
- Modify: `CHANGELOG.md`
- Modify: `nori.json`
- Modify: `.nori-version`
- Modify: `C:\projects\senior-infra-ops-analyst\TODO-AI-FIRST.md` outside Git

**Interfaces:**
- ADR records the implemented architecture, enforcement points, alternatives,
  evidence, consequences, forward compatibility, and credential-reuse
  limitation.
- Package metadata exposes `0.11.0`; individual skill `nori.json` versions
  remain their independent versions.

- [ ] **Step 1: Add failing ADR index/record tests**

Require `ADR-004-native-command-guard.md` in the architecture index and
validate these headings: Context, Decision, Implemented architecture,
Enforcement points, Credential handling, Alternatives rejected, Validation
evidence, Consequences and limitations, Forward compatibility.

- [ ] **Step 2: Write ADR-004 from shipped evidence**

Record native executor hooks, shared Node validator, separate lexers,
composition graph, finite catalogue, permission-mode matrix, exact
destructive boundary, redacted audit, fail-closed behavior, Nori-installed
path validation, two-layer model-visible credential reuse, and why the guard
cannot prove secret equality without forbidden secret-derived state.
Record the executor-scoped limitation: the main Claude Code session remains
outside this guard if it can invoke `Bash` directly and no supported global
hook path is present in the installed artifact.

- [ ] **Step 3: Update README and Noridoc**

Document what the guard protects, which eight roles receive it, how normal and
bypass modes differ, why pipes are analyzed rather than blanket-blocked, what
credential mechanisms are supported, what the transcript boundary means, and
how to run static/installed/live validation. Do not advertise a version floor
for Claude Code, Nori, Node.js, or the model.

- [ ] **Step 4: Update release metadata**

Set `nori.json` and `.nori-version` to `0.11.0`, update root descriptions, add
`CHANGELOG.md` entry dated `2026-07-26`, and update the visible version in
`README.md` and `docs.md`. Do not change the 24 skill component versions.

- [ ] **Step 5: Update the external TODO without staging it**

Mark only completed P0-04 actions supported by evidence, attach commit/test
references, record residual live gaps honestly, and update dependent wording
only if the shipped implementation differs from the approved design. Verify
the file remains outside the worktree and `git status`.

- [ ] **Step 6: Run release validation and commit**

Run:

```bash
python3 tests/test-architecture-docs.py
bash tests/validate-package.sh
git diff --check
```

Expected: all static/package gates pass and metadata agrees on `0.11.0`.
Commit only repository files:

```bash
git add docs/architecture README.md docs.md CHANGELOG.md nori.json \
  .nori-version tests/test-architecture-docs.py tests/validate-content.py
git commit -m "docs: release native command guard architecture"
```

---

### Task 11: Execute final independent review, validation, PR, and integration

**Files:**
- Inspect: all files changed since the P0-04 branch point
- Update only when evidence requires: implementation, tests, docs, metadata,
  or the external TODO

**Interfaces:**
- Produces a review record mapped to the approved specification and this plan.
- Produces fresh static, package, installed, and optional live evidence.
- Produces a PR whose commits are reviewable and whose merge preserves every
  required gate.

- [ ] **Step 1: Perform specification coverage review**

Map every heading and bullet in
`docs/superpowers/specs/2026-07-25-p0-04-native-command-guard-design.md` to a
production file, deterministic test, installed test, live scenario, ADR
section, or explicitly retained residual risk. Any unmapped requirement blocks
the PR.

- [ ] **Step 2: Perform security-focused code review**

Inspect parser ambiguity, unsupported syntax, decision precedence, target
binding, permission-mode fallback, audit failure, redaction order, stdout
pollution, path substitution, secret leakage, credential consumer binding,
test-only injection reachability, time/size bounds, and all generated error
paths. Record findings by severity and fix every actionable finding before
continuing.

- [ ] **Step 3: Run the full gate in a clean copy**

Exclude only `.git`, `.worktrees`, and generated `.tmp` caches. Run:

```bash
bash tests/validate-package.sh
git diff --check
git status --short
```

Expected: package gate exits `0`, diff check is clean, and only intentional
files are present. If the local environment supports installation/live
prerequisites, run the documented installed and live commands and retain only
redacted reports.

- [ ] **Step 4: Request independent review**

Provide the reviewer the approved spec, plan, branch diff, complete test
output, coverage manifest, mutation report, installed evidence, live evidence
or explicit skip reason, and the credential-reuse residual limitation. Do not
merge with unresolved Critical, Important, or Minor findings.

- [ ] **Step 5: Push and open the PR**

Use a branch/PR title describing P0-04, include risk and rollback, link
ADR-004, list exact validation commands/results, and state that runtime
versions were observed but not pinned.

- [ ] **Step 6: Review CI and merge only after green evidence**

Inspect every failing or skipped check, address review threads, rerun affected
local gates, and merge through the repository's accepted strategy only when CI
and independent review are clean. Confirm remote `main` contains the merge and
update the external TODO with final PR/merge evidence without adding it to Git.
