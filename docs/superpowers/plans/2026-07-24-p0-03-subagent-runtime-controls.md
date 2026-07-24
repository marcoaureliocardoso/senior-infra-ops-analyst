# P0-03 Subagent Runtime Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce bounded turns and least-privilege tools for all 12
subagents, verify the Nori-installed artifact and live Claude Code/DeepSeek
behavior, and document the decisions behind P0-01, P0-02, and P0-03.

**Architecture:** Native Claude Code frontmatter is the enforcement boundary:
`maxTurns` bounds the loop, `tools` is an exclusive allowlist,
`disallowedTools` records critical denials, and `model: inherit` preserves
runtime portability. A role-policy validator fails closed on drift, while
Nori installation and live smoke scripts verify translation and behavioral
invariants outside normal CI.

**Tech Stack:** Markdown/YAML frontmatter, Python 3 standard library,
PowerShell 7, Bash, Git, Nori Skillsets CLI, Claude Code CLI, WSL2.

## Global Constraints

- Package version advances from `0.9.1` to `0.10.0`.
- Do not pin Claude Code, Nori, or a DeepSeek model/version in project
  requirements or scripts.
- Keep `model: inherit` in all 12 subagents.
- Record observed runtime and installer versions during live tests.
- Use Nori as the installation and translation layer.
- Use native Claude Code `maxTurns`, `tools`, and `disallowedTools`.
- Treat `maxTurns` as a turn limit, not a wall-clock timeout.
- Reserve two cooperative turns for closing or handoff.
- Never test commands against real infrastructure.
- Do not implement P0-04 command-semantic enforcement in this change.
- Every implemented solution requires a versioned ADR indexed by
  `docs/architecture/README.md`.

---

## File map

- `tests/subagent_runtime_policy.py`: canonical validation policy and
  frontmatter/runtime-section parsing used by repository validators.
- `tests/test-subagent-frontmatter.py`: mutation tests proving invalid runtime
  controls are rejected before agent files are changed.
- `tests/validate-content.py`: integrates role-policy errors into package
  validation.
- `subagents/*.md`: native enforcement fields and role-specific runtime
  instructions consumed by Claude Code.
- `tests/validate-installed-subagents.py`: semantic source-versus-installed
  comparison for Nori output.
- `tests/test-installed-subagents.py`: isolated fixtures for the installed
  artifact validator.
- `tests/validate-schema.py`: requires the Nori skillset manifest type.
- `tests/live-subagent-runtime-smoke.sh`: opt-in WSL/Linux orchestration of
  Nori install and Claude Code/DeepSeek behavioral probes.
- `tests/validation-notes.md`: prerequisites, commands, and interpretation of
  static, installed, and live validation.
- `tests/test-architecture-docs.py`: isolated mutation tests for the ADR index
  and required decision records.
- `docs/architecture/*.md`: ADR index plus P0-01, P0-02, and P0-03 decisions.
- `README.md`, `docs.md`, `CHANGELOG.md`, `nori.json`, `.nori-version`: release
  and architecture documentation.

---

### Task 1: Enforce the runtime-control contract test-first

**Files:**
- Create: `tests/subagent_runtime_policy.py`
- Modify: `tests/test-subagent-frontmatter.py`
- Modify: `tests/validate-content.py`
- Modify: `subagents/audit-evidence-collector.md`
- Modify: `subagents/change-manager.md`
- Modify: `subagents/cloud-platform-operator.md`
- Modify: `subagents/database-operator.md`
- Modify: `subagents/diagnostic-operator.md`
- Modify: `subagents/incident-commander.md`
- Modify: `subagents/kubernetes-operator.md`
- Modify: `subagents/network-edge-operator.md`
- Modify: `subagents/observability-sre.md`
- Modify: `subagents/rca-facilitator.md`
- Modify: `subagents/release-cicd-operator.md`
- Modify: `subagents/security-operations-reviewer.md`

**Interfaces:**
- Produces: `runtime_control_errors(agent_id: str, text: str) -> list[str]`.
- Produces: `frontmatter_fields(text: str) -> dict[str, object]`.
- Consumes: subagent IDs registered in `nori.json`.
- Guarantees: every agent has a bounded role policy and a complete handoff
  contract before `validate-content.py` can pass.

- [ ] **Step 1: Add mutation tests before changing production agents**

Extend `SubagentFrontmatterValidationTests` with helpers that restore and
mutate `diagnostic-operator.md`, `change-manager.md`, and
`incident-commander.md`. Add these tests:

```python
def test_missing_max_turns_is_rejected(self) -> None:
    content = self.original_agent.replace("maxTurns: 16\n", "", 1)
    self.assert_rejected(content, "missing maxTurns")

def test_zero_max_turns_is_rejected(self) -> None:
    content = self.original_agent.replace("maxTurns: 16", "maxTurns: 0", 1)
    self.assert_rejected(content, "invalid maxTurns")

def test_non_numeric_max_turns_is_rejected(self) -> None:
    content = self.original_agent.replace(
        "maxTurns: 16", "maxTurns: sixteen", 1
    )
    self.assert_rejected(content, "invalid maxTurns")

def test_duplicate_max_turns_is_rejected(self) -> None:
    content = self.original_agent.replace(
        "maxTurns: 16", "maxTurns: 16\nmaxTurns: 16", 1
    )
    self.assert_rejected(content, "duplicate maxTurns")

def test_out_of_role_range_is_rejected(self) -> None:
    content = self.original_agent.replace("maxTurns: 16", "maxTurns: 20", 1)
    self.assert_rejected(content, "maxTurns outside role range")

def test_unknown_tool_is_rejected(self) -> None:
    content = self.original_agent.replace(
        "tools: Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill",
        "tools: Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill, FutureTool",
        1,
    )
    self.assert_rejected(content, "unknown tools")

def test_role_tool_drift_is_rejected(self) -> None:
    content = self.original_agent.replace(", WebSearch", "", 1)
    self.assert_rejected(content, "tools differ from role policy")

def test_missing_critical_denial_is_rejected(self) -> None:
    content = self.original_agent.replace(
        "disallowedTools: Write, Edit", "disallowedTools: Write", 1
    )
    self.assert_rejected(content, "disallowedTools differ from role policy")

def test_missing_tool_rationale_is_rejected(self) -> None:
    content = self.original_agent.replace(
        "- `Bash`:", "- Shell evidence collection:", 1
    )
    self.assert_rejected(content, "missing tool rationale for Bash")

def test_missing_handoff_field_is_rejected(self) -> None:
    content = self.original_agent.replace(
        "- Next safest action", "- Suggested continuation", 1
    )
    self.assert_rejected(content, "missing handoff field: Next safest action")
```

Add an analytical-role mutation using `change-manager.md`:

```python
def test_analytical_role_cannot_gain_bash(self) -> None:
    content = self.change_manager_text.replace(
        "tools: Read, Grep, Glob, WebFetch, WebSearch, Skill",
        "tools: Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill",
        1,
    )
    self.assert_agent_rejected(
        "subagents/change-manager.md",
        content,
        "tools differ from role policy",
    )
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```powershell
python tests/test-subagent-frontmatter.py
```

Expected: new tests fail because `maxTurns`, `disallowedTools`, runtime
rationales, and the role-policy validator do not exist.

- [ ] **Step 3: Implement the role-policy module**

Create `tests/subagent_runtime_policy.py` with:

```python
from __future__ import annotations

import re

COMMON = ("Read", "Grep", "Glob")
WEB = ("WebFetch", "WebSearch")
EXECUTOR = (*COMMON, "Bash", *WEB, "Skill")
ANALYST = (*COMMON, *WEB, "Skill")

ROLE_POLICY = {
    "incident-commander": {
        "turn_range": (12, 20),
        "tools": (*COMMON, "TodoWrite", "Skill"),
        "denied": ("Write", "Edit", "Bash"),
    },
    "diagnostic-operator": {
        "turn_range": (12, 16),
        "tools": EXECUTOR,
        "denied": ("Write", "Edit"),
    },
    "change-manager": {
        "turn_range": (8, 12),
        "tools": ANALYST,
        "denied": ("Write", "Edit", "Bash"),
    },
    "rca-facilitator": {
        "turn_range": (8, 12),
        "tools": ANALYST,
        "denied": ("Write", "Edit", "Bash"),
    },
    "observability-sre": {
        "turn_range": (12, 16),
        "tools": EXECUTOR,
        "denied": ("Write", "Edit"),
    },
    "security-operations-reviewer": {
        "turn_range": (8, 12),
        "tools": ANALYST,
        "denied": ("Write", "Edit", "Bash"),
    },
    "cloud-platform-operator": {
        "turn_range": (12, 16),
        "tools": EXECUTOR,
        "denied": ("Write", "Edit"),
    },
    "kubernetes-operator": {
        "turn_range": (12, 16),
        "tools": EXECUTOR,
        "denied": ("Write", "Edit"),
    },
    "database-operator": {
        "turn_range": (12, 16),
        "tools": EXECUTOR,
        "denied": ("Write", "Edit"),
    },
    "network-edge-operator": {
        "turn_range": (12, 16),
        "tools": EXECUTOR,
        "denied": ("Write", "Edit"),
    },
    "release-cicd-operator": {
        "turn_range": (12, 16),
        "tools": EXECUTOR,
        "denied": ("Write", "Edit"),
    },
    "audit-evidence-collector": {
        "turn_range": (8, 12),
        "tools": EXECUTOR,
        "denied": ("Write", "Edit"),
    },
}

HANDOFF_FIELDS = (
    "Objective and current status",
    "Completed actions",
    "Observed evidence",
    "Leading hypotheses and uncertainty",
    "Pending work",
    "Required tools, access, approvals, or owner",
    "Next safest action",
    "Risk classification and modifiers",
)


def _frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    parts = text.split("---", 2)
    return parts[1] if len(parts) == 3 else ""


def _csv_field(frontmatter: str, field: str) -> tuple[str, ...] | None:
    match = re.search(
        rf"^{re.escape(field)}:\s*(.*?)\s*$", frontmatter, re.MULTILINE
    )
    if not match:
        return None
    return tuple(part.strip() for part in match.group(1).split(",") if part.strip())


def runtime_section(text: str) -> str:
    match = re.search(
        r"^## Runtime controls\s*\n(.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1) if match else ""


def frontmatter_fields(text: str) -> dict[str, object]:
    frontmatter = _frontmatter(text)
    max_matches = re.findall(
        r"^maxTurns:\s*(.*?)\s*$", frontmatter, re.MULTILINE
    )
    max_value = max_matches[0] if len(max_matches) == 1 else None
    return {
        "maxTurns": max_value,
        "maxTurnsCount": len(max_matches),
        "tools": _csv_field(frontmatter, "tools"),
        "disallowedTools": _csv_field(frontmatter, "disallowedTools"),
    }


def runtime_control_errors(agent_id: str, text: str) -> list[str]:
    policy = ROLE_POLICY[agent_id]
    fields = frontmatter_fields(text)
    errors: list[str] = []
    raw_turns = fields["maxTurns"]
    if fields["maxTurnsCount"] > 1:
        errors.append(f"subagent has duplicate maxTurns: {agent_id}")
        turns = None
    elif raw_turns is None:
        errors.append(f"subagent missing maxTurns: {agent_id}")
        turns = None
    elif not re.fullmatch(r"[1-9]\d*", str(raw_turns)):
        errors.append(f"subagent has invalid maxTurns: {agent_id}")
        turns = None
    else:
        turns = int(str(raw_turns))
        minimum, maximum = policy["turn_range"]
        if not minimum <= turns <= maximum:
            errors.append(f"subagent maxTurns outside role range: {agent_id}")

    tools = fields["tools"]
    if tools is not None:
        unknown = sorted(set(tools) - {
            "Read", "Grep", "Glob", "Bash", "TodoWrite",
            "WebFetch", "WebSearch", "Skill",
        })
        if unknown:
            errors.append(f"subagent declares unknown tools: {unknown} — {agent_id}")
        if tools != policy["tools"]:
            errors.append(f"subagent tools differ from role policy: {agent_id}")

    denied = fields["disallowedTools"]
    if denied != policy["denied"]:
        errors.append(
            f"subagent disallowedTools differ from role policy: {agent_id}"
        )

    section = runtime_section(text)
    if not section:
        errors.append(f"subagent lacks Runtime controls section: {agent_id}")
        return errors
    for tool in policy["tools"]:
        if f"`{tool}`" not in section:
            errors.append(f"subagent missing tool rationale for {tool}: {agent_id}")
    for field in HANDOFF_FIELDS:
        if field not in section:
            errors.append(f"subagent missing handoff field: {field} — {agent_id}")
    if turns is not None and f"Operational budget: {turns - 2} turns" not in section:
        errors.append(f"subagent runtime budget does not match maxTurns: {agent_id}")
    return errors
```

Import `runtime_control_errors` into `tests/validate-content.py` and append
its results inside the existing subagent loop:

```python
from subagent_runtime_policy import runtime_control_errors

# Inside the manifest subagent loop, after reading t:
for runtime_error in runtime_control_errors(sa_id, t):
    err(runtime_error)
```

- [ ] **Step 4: Add native controls to every subagent**

Use the exact `maxTurns`, `tools`, and `disallowedTools` values from the
approved role-policy table. Keep `model: inherit` and existing `skills`
unchanged. Example executor frontmatter:

```yaml
tools: Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill
disallowedTools: Write, Edit
maxTurns: 16
model: inherit
```

Example analytical frontmatter:

```yaml
tools: Read, Grep, Glob, WebFetch, WebSearch, Skill
disallowedTools: Write, Edit, Bash
maxTurns: 10
model: inherit
```

Add `## Runtime controls` immediately after `## Primary skills` in every
agent. Use role-specific tool rationales followed by this exact handoff list:

```markdown
Operational budget: 14 turns. Reserve the final 2 turns for closure or handoff.
Do not start another diagnostic branch when the operational budget is exhausted.

Tool rationale:
- `Read`, `Grep`, `Glob`: inspect local instructions and supplied evidence.
- `Bash`: collect narrowly scoped operational evidence required by this role.
- `WebFetch`, `WebSearch`: consult current official documentation without
  placing internal data, secrets, identifiers, or topology in external queries.
- `Skill`: load additional project procedures on demand.

If the task cannot be completed inside the operational budget, stop
voluntarily and return:

- Objective and current status
- Completed actions
- Observed evidence
- Leading hypotheses and uncertainty
- Pending work
- Required tools, access, approvals, or owner
- Next safest action
- Risk classification and modifiers
```

For the incident commander, replace Bash/web rationales with a `TodoWrite`
rationale. For change manager, RCA facilitator, and security reviewer, omit
Bash and explain that evidence collection or execution is delegated to an
operator. Update change-manager wording that currently claims direct execution
so the role plans, reviews, coordinates, and validates rather than executes.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run:

```powershell
python tests/test-subagent-frontmatter.py
python tests/validate-content.py
```

Expected: all frontmatter tests pass and content validation prints
`content validation passed`.

- [ ] **Step 6: Commit the runtime contract**

```powershell
git add tests/subagent_runtime_policy.py tests/test-subagent-frontmatter.py `
  tests/validate-content.py subagents
git commit -m "feat: bound subagent runtime capabilities"
```

---

### Task 2: Validate the Nori-installed artifact

**Files:**
- Create: `tests/validate-installed-subagents.py`
- Create: `tests/test-installed-subagents.py`
- Modify: `tests/validate-package.sh`
- Modify: `tests/validate-schema.py`
- Modify: `nori.json`

**Interfaces:**
- Produces CLI:
  `python tests/validate-installed-subagents.py --installed-agents-dir PATH`.
- Exit `0`: all 12 installed definitions preserve source semantics.
- Exit `1`: missing agent or mismatch in native runtime fields/instructions.
- Consumes: `frontmatter_fields()` and `ROLE_POLICY` from Task 1.

- [ ] **Step 1: Write installed-artifact validator tests**

Create `tests/test-installed-subagents.py` using `tempfile.TemporaryDirectory`
and `shutil.copytree`. Cover:

```python
def test_identical_installed_agents_pass(self) -> None:
    result = self.run_validator()
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

def test_missing_installed_agent_fails(self) -> None:
    (self.installed / "change-manager.md").unlink()
    result = self.run_validator()
    self.assertNotEqual(result.returncode, 0)
    self.assertIn("missing installed subagent", result.stdout + result.stderr)

def test_broadened_installed_tools_fail(self) -> None:
    path = self.installed / "change-manager.md"
    text = path.read_text(encoding="utf-8").replace(
        "tools: Read, Grep, Glob, WebFetch, WebSearch, Skill",
        "tools: Read, Grep, Glob, Bash, WebFetch, WebSearch, Skill",
        1,
    )
    path.write_text(text, encoding="utf-8")
    result = self.run_validator()
    self.assertNotEqual(result.returncode, 0)
    self.assertIn("installed tools differ", result.stdout + result.stderr)

def test_missing_installed_runtime_section_fails(self) -> None:
    path = self.installed / "diagnostic-operator.md"
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"^## Runtime controls\n.*?(?=^## )",
        "",
        text,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
    path.write_text(text, encoding="utf-8")
    result = self.run_validator()
    self.assertNotEqual(result.returncode, 0)
    self.assertIn("installed runtime controls differ", result.stdout + result.stderr)
```

- [ ] **Step 2: Run installed-artifact tests and verify RED**

Run:

```powershell
python tests/test-installed-subagents.py
```

Expected: FAIL because `validate-installed-subagents.py` does not exist.

- [ ] **Step 3: Implement semantic installed-artifact comparison**

Create `tests/validate-installed-subagents.py`. Parse arguments with
`argparse`, enumerate the 12 IDs in `ROLE_POLICY`, and compare source versus
installed:

```python
FIELDS = ("maxTurns", "tools", "disallowedTools")

for agent_id in sorted(ROLE_POLICY):
    source_path = ROOT / "subagents" / f"{agent_id}.md"
    installed_path = installed_dir / f"{agent_id}.md"
    if not installed_path.exists():
        errors.append(f"missing installed subagent: {agent_id}")
        continue
    source = source_path.read_text(encoding="utf-8")
    installed = installed_path.read_text(encoding="utf-8")
    source_fields = frontmatter_fields(source)
    installed_fields = frontmatter_fields(installed)
    for field in FIELDS:
        if installed_fields[field] != source_fields[field]:
            errors.append(f"installed {field} differs: {agent_id}")
    for scalar in ("model: inherit", "skills:"):
        if scalar not in installed:
            errors.append(f"installed subagent omits {scalar}: {agent_id}")
    if runtime_section(installed) != runtime_section(source):
        errors.append(f"installed runtime controls differ: {agent_id}")
```

Reuse the public `runtime_section(text: str) -> str` from
`tests/subagent_runtime_policy.py`.

- [ ] **Step 4: Make the Nori manifest explicit**

Add the required top-level field to `nori.json`:

```json
"type": "skillset",
```

Extend `tests/validate-schema.py` or the existing schema assertions so a
missing or non-`skillset` value fails. This is necessary for current Nori
local/Git-backed activation and is format metadata, not a Nori version pin.

- [ ] **Step 5: Run tests and integrate into package validation**

Add `python3 tests/test-installed-subagents.py` to
`tests/validate-package.sh`. Run:

```powershell
python tests/test-installed-subagents.py
python tests/validate-schema.py
& 'C:\Program Files\Git\bin\bash.exe' --noprofile --norc -c `
  'export PATH=/usr/bin:/mingw64/bin:$PATH; exec bash tests/validate-package.sh'
```

Expected: installed-artifact tests pass, schema validation passes, and package
validation passes.

- [ ] **Step 6: Commit installed-artifact validation**

```powershell
git add nori.json tests/validate-schema.py `
  tests/validate-installed-subagents.py tests/test-installed-subagents.py `
  tests/validate-package.sh tests/subagent_runtime_policy.py
git commit -m "test: verify Nori-installed subagent controls"
```

---

### Task 3: Add opt-in live Nori and Claude Code smoke validation

**Files:**
- Create: `tests/live-subagent-runtime-smoke.sh`
- Modify: `tests/validation-notes.md`
- Modify: `.gitignore`

**Interfaces:**
- CLI:
  `bash tests/live-subagent-runtime-smoke.sh [--keep-artifacts]`.
- Environment:
  `CLAUDE_BIN` and `NORI_BIN` optional; discovered when omitted.
- Exit `0`: Nori fields preserved and all behavioral invariants pass.
- Exit `2`: a prerequisite is unavailable and the test is explicitly blocked.
- Exit `1`: installation or behavioral invariant failed.
- Output redacts configured authentication values and reports only observed
  command versions, model identifier, test names, and pass/fail state.

- [ ] **Step 1: Write shell-level fixture tests first**

Add a `--self-test` mode to the planned script contract. Before implementing
the main body, create assertions that call missing helper functions:

```bash
if [[ "${1:-}" == "--self-test" ]]; then
  assert_json_has_no_tool "fixtures/analyst.jsonl" "Bash"
  assert_json_has_tool "fixtures/executor.jsonl" "Bash"
  assert_handoff "fixtures/handoff.jsonl"
  assert_max_turns "fixtures/cutoff.jsonl" 2
  echo "live smoke parser self-test passed"
  exit 0
fi
```

Place generated fixtures under a temporary directory inside the self-test;
do not commit model transcripts.

- [ ] **Step 2: Run self-test and verify RED**

Run inside Debian WSL:

```powershell
wsl -d Debian -- bash -lc `
  'cd /mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-03-runtime-controls && bash tests/live-subagent-runtime-smoke.sh --self-test'
```

Expected: FAIL because the smoke script/helper functions do not exist.

- [ ] **Step 3: Implement prerequisite discovery and secure isolation**

The script must:

```bash
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
KEEP_ARTIFACTS=false
cleanup() {
  if [[ "$KEEP_ARTIFACTS" == false ]]; then rm -rf -- "$WORK"; fi
}
trap cleanup EXIT
```

Discover a Linux Node runtime of version 22 or newer. If absent, return exit
`2` with an exact preparation command; do not silently use Windows-mounted
Node. Discover `claude` and Nori without constraining versions:

```bash
CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
NORI_BIN="${NORI_BIN:-$(command -v nori-skillsets || command -v sks || true)}"
[[ -n "$CLAUDE_BIN" ]] || blocked "Claude Code CLI not found"
[[ -n "$NORI_BIN" ]] || blocked "Nori CLI not found"
```

Create an isolated home and install directory:

```bash
REAL_HOME="$HOME"
export HOME="$WORK/home"
mkdir -p "$HOME/.claude"
INSTALL_DIR="$HOME/.claude"
```

Read only the approved `ANTHROPIC_*`, `CLAUDE_CODE_EFFORT_LEVEL`, and
`CLAUDE_CODE_SUBAGENT_MODEL` keys from
`$REAL_HOME/.claude/settings.json`, export their values without printing
them, and never copy the token-bearing settings file into artifacts.

- [ ] **Step 4: Install the local worktree through Nori**

Use Nori's local link and activation flow:

```bash
"$NORI_BIN" --install-dir "$INSTALL_DIR" --agent claude-code \
  link "$ROOT" --name senior-infra-ops-analyst
"$NORI_BIN" --install-dir "$INSTALL_DIR" --agent claude-code \
  switch senior-infra-ops-analyst --agent claude-code
python3 "$ROOT/tests/validate-installed-subagents.py" \
  --installed-agents-dir "$INSTALL_DIR/agents"
```

If Windows filesystem symlink restrictions affect `link`, create a temporary
Git-backed source with the exact branch
`refs/heads/skillsets/senior-infra-ops-analyst` and use Nori's local
Git-backed install flow. Do not activate into the operator's real
`~/.claude`.

- [ ] **Step 5: Implement invariant-based Claude probes**

Run Claude with the installed agent as the main agent and
`--output-format stream-json --verbose`. Prompts are synthetic:

1. `change-manager`: ask it to execute a shell command and require it to
   delegate because Bash is unavailable. Assert no Bash tool-use event.
2. `diagnostic-operator`: ask for exactly one benign
   `printf 'p0-03-smoke\n'` call. Assert one Bash event and no mutating tools.
3. `rca-facilitator`: provide an intentionally incomplete synthetic incident
   and ask it to stop at its cooperative budget. Assert the final result
   contains at least six of the eight handoff invariants and includes risk.
4. Temporary `turn-cutoff-probe`: `maxTurns: 2`, only benign Bash, and a prompt
   that would continue tool calls. Wrap execution in `timeout 120`; assert
   termination and at most two agentic turns.

Parse JSONL with Python standard library. Tool assertions inspect structured
tool names, not natural-language claims. Handoff assertions use case-insensitive
semantic keyword groups rather than exact paragraphs.

- [ ] **Step 6: Document execution and artifact policy**

Update `tests/validation-notes.md` with:

```markdown
## Live subagent runtime smoke test

Run only in an isolated Linux/WSL environment with Claude Code, Nori, and
operator-configured model credentials:

`bash tests/live-subagent-runtime-smoke.sh`

The test records observed versions but does not require fixed Claude Code,
Nori, or model versions. It uses synthetic prompts and benign local commands,
never production infrastructure. Exit 2 means blocked prerequisites, not pass.
Transcripts contain model output and remain temporary and untracked.
```

Add only the script's local artifact directory, if any, to `.gitignore`;
temporary directories outside the repository need no ignore rule.

- [ ] **Step 7: Run parser self-test**

Run:

```powershell
wsl -d Debian -- bash -lc `
  'cd /mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-03-runtime-controls && bash tests/live-subagent-runtime-smoke.sh --self-test'
```

Expected: `live smoke parser self-test passed`.

- [ ] **Step 8: Commit live validation harness**

```powershell
git add tests/live-subagent-runtime-smoke.sh tests/validation-notes.md .gitignore
git commit -m "test: add live subagent runtime smoke"
```

---

### Task 4: Record P0 architecture and release metadata

**Files:**
- Create: `docs/architecture/README.md`
- Create: `docs/architecture/ADR-001-risk-taxonomy.md`
- Create: `docs/architecture/ADR-002-subagent-skill-preload.md`
- Create: `docs/architecture/ADR-003-subagent-runtime-controls.md`
- Create: `tests/test-architecture-docs.py`
- Modify: `README.md`
- Modify: `docs.md`
- Modify: `CHANGELOG.md`
- Modify: `nori.json`
- Modify: `.nori-version`

**Interfaces:**
- Produces: indexed architectural history for P0-01, P0-02, and P0-03.
- Consumes: commits `41d9e86`, `7dca0e0`, `0e72213`, current implementation
  commits, tests, and the approved P0-03 specification.
- Guarantees: package version and architecture links are consistent.

- [ ] **Step 1: Add documentation validation before ADRs**

Extend `tests/validate-content.py` with:

```python
architecture_index = root / "docs/architecture/README.md"
required_adrs = [
    "ADR-001-risk-taxonomy.md",
    "ADR-002-subagent-skill-preload.md",
    "ADR-003-subagent-runtime-controls.md",
]
if not architecture_index.exists():
    err("missing architecture decision index")
else:
    index_text = architecture_index.read_text(encoding="utf-8")
    for adr in required_adrs:
        if adr not in index_text:
            err(f"architecture index missing ADR: {adr}")
        if not (architecture_index.parent / adr).exists():
            err(f"missing architecture decision record: {adr}")
```

Create `tests/test-architecture-docs.py` by copying the package into a
`TemporaryDirectory`, running `tests/validate-content.py` there, and adding:

```python
def test_missing_architecture_index_is_rejected(self) -> None:
    self.index_path.unlink()
    result = self.run_validator()
    self.assertNotEqual(result.returncode, 0)
    self.assertIn("missing architecture decision index", result.stdout)

def test_missing_index_entry_is_rejected(self) -> None:
    text = self.index_path.read_text(encoding="utf-8").replace(
        "ADR-002-subagent-skill-preload.md", "ADR-002-omitted.md", 1
    )
    self.index_path.write_text(text, encoding="utf-8")
    result = self.run_validator()
    self.assertNotEqual(result.returncode, 0)
    self.assertIn("architecture index missing ADR", result.stdout)

def test_missing_adr_file_is_rejected(self) -> None:
    (self.index_path.parent / "ADR-003-subagent-runtime-controls.md").unlink()
    result = self.run_validator()
    self.assertNotEqual(result.returncode, 0)
    self.assertIn("missing architecture decision record", result.stdout)
```

- [ ] **Step 2: Run documentation tests and verify RED**

Run:

```powershell
python tests/test-subagent-frontmatter.py
python tests/test-architecture-docs.py
python tests/validate-content.py
```

Expected: FAIL with `missing architecture decision index`.

- [ ] **Step 3: Write the ADR index and three ADRs**

Every ADR uses:

```markdown
# ADR-NNN — Decision title

**Status:** Accepted
**Date:** YYYY-MM-DD
**Decision owners:** Project maintainers

## Context
## Decision
## Implemented architecture
## Enforcement points
## Alternatives rejected
## Validation evidence
## Consequences and limitations
## Forward compatibility
```

ADR-001 records canonical base levels, orthogonal modifiers, highest plausible
impact, control matrix, context-aware validator, mutation tests, and the
independent retroactive review.

ADR-002 records native `skills` preload, `Skill` on-demand access, exact match
between frontmatter and documented primary skills, Nori artifact inspection,
and why full-catalog preload was rejected.

ADR-003 records the approved role matrix, allowlist-first design,
`disallowedTools`, cooperative handoff, Nori/live validation, and residual
Bash risk deferred to P0-04.

- [ ] **Step 4: Update user-facing documentation**

Add an Architecture Decisions section to `README.md` and `docs.md` linking
`docs/architecture/README.md`. Update the subagent table to include
`maxTurns` and current tool allowlists. Explain that observed runtime versions
are evidence, not compatibility constraints.

- [ ] **Step 5: Update release metadata to 0.10.0**

Set:

```json
"version": "0.10.0"
```

in root `nori.json` and `.nori-version`, and update README/docs version text.
Add a `0.10.0` CHANGELOG entry covering P0-03 controls, installed/live
validation, ADRs, and the manifest `type: skillset` correction.

- [ ] **Step 6: Verify documentation and metadata**

Run:

```powershell
python tests/validate-content.py
python tests/validate-schema.py
git diff --check
```

Expected: content and schema validation pass; no whitespace errors.

- [ ] **Step 7: Commit architecture and release metadata**

```powershell
git add docs/architecture README.md docs.md CHANGELOG.md nori.json `
  .nori-version tests/validate-content.py tests/test-architecture-docs.py `
  tests/validate-package.sh
git commit -m "docs: record P0 control architecture"
```

---

### Task 5: Execute real validation and close the delivery

**Files:**
- Modify only if validation reveals a reproducible defect:
  `tests/live-subagent-runtime-smoke.sh`,
  `tests/validate-installed-subagents.py`, or affected `subagents/*.md`.
- Update external, unversioned:
  `C:\projects\senior-infra-ops-analyst\TODO-AI-FIRST.md`.

**Interfaces:**
- Consumes all prior task outputs.
- Produces fresh local, installed-artifact, and live behavioral evidence.
- Produces an independently reviewed branch ready for publication.

- [ ] **Step 1: Run the complete static package validation**

```powershell
& 'C:\Program Files\Git\bin\bash.exe' --noprofile --norc -c `
  'export PATH=/usr/bin:/mingw64/bin:$PATH; exec bash tests/validate-package.sh'
```

Expected: package validation passes, including runtime-control and
installed-artifact fixture tests.

- [ ] **Step 2: Prepare an ephemeral supported Node runtime in WSL if needed**

Nori requires Node 22 or newer. If the Debian `node` major is below 22,
download the current Linux x64 LTS archive into a temporary directory, verify
its published SHA-256 checksum, prepend its `bin` directory to `PATH`, and
record the observed version. Do not install or change the distribution's
system packages.

- [ ] **Step 3: Make current Nori available ephemerally**

Use the unversioned package name so the project does not pin Nori:

```bash
npm exec --yes --package=nori-skillsets -- sks --version
```

Expose the resulting `sks` command to the smoke script through `NORI_BIN`.
Record the observed version in the test report.

- [ ] **Step 4: Run the real WSL smoke test**

```powershell
wsl -d Debian -- bash -lc `
  'cd /mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-03-runtime-controls && bash tests/live-subagent-runtime-smoke.sh'
```

Expected: Nori installation comparison passes; analytical, executor, handoff,
and cutoff probes pass; observed Claude Code, Nori, and model identifiers are
reported without credentials.

- [ ] **Step 5: Apply test-first fixes only if a probe fails**

For every failure:

1. preserve the red transcript privately in the temporary test directory;
2. reduce it to a deterministic fixture test;
3. confirm the fixture test fails;
4. make the smallest source or parser change;
5. rerun the fixture, package, and real probe.

Do not weaken an invariant merely to accept the observed output.

- [ ] **Step 6: Request independent review**

Review the complete range from `0e72213` to branch HEAD against:

- the approved specification;
- P0-03 TODO acceptance criteria;
- actual Claude Code/Nori capabilities;
- least privilege and separation of duties;
- test validity and live-test evidence;
- ADR accuracy for P0-01, P0-02, and P0-03.

Fix all Critical and Important findings, add regression tests first where
behavior changes, and repeat review until none remain.

- [ ] **Step 7: Re-run full verification after review**

Run:

```powershell
& 'C:\Program Files\Git\bin\bash.exe' --noprofile --norc -c `
  'export PATH=/usr/bin:/mingw64/bin:$PATH; exec bash tests/validate-package.sh'
git status -sb
git log --oneline 0e72213..HEAD
```

Expected: validation passes, worktree is clean, and only P0-03 commits are
present.

- [ ] **Step 8: Update the external TODO with final evidence**

Mark P0-03 `CONCLUÍDO` only after integration to `main`. Record:

- package version `0.10.0`;
- branch, PR, and merge SHA;
- static test counts;
- installed artifact result;
- live observed runtime/installer/model identifiers;
- independent review conclusion;
- CI and Security status;
- ADR index and ADR-003 path.

- [ ] **Step 9: Publish and integrate only when requested**

Use the repository's established flow: push the feature branch, create a
ready-for-review PR, wait for required checks, record review evidence, and
squash merge guarded by the reviewed head SHA. Do not delete the worktree or
branch without explicit instruction.
