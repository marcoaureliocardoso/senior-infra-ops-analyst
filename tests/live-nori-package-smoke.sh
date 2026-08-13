#!/usr/bin/env bash
set -euo pipefail
umask 077

usage() {
  printf '%s\n' \
    'Usage: live-nori-package-smoke.sh --self-test' \
    '       live-nori-package-smoke.sh --run-live --nori-bin ABSOLUTE_PATH' >&2
}

die_usage() {
  printf 'error: %s\n' "$1" >&2
  usage
  exit 2
}

SELF_TEST=0
RUN_LIVE=0
NORI_BIN=''

while (($#)); do
  case "$1" in
    --self-test)
      SELF_TEST=$((SELF_TEST + 1))
      shift
      ;;
    --run-live)
      RUN_LIVE=$((RUN_LIVE + 1))
      shift
      ;;
    --nori-bin)
      (($# >= 2)) || die_usage '--nori-bin requires a value'
      NORI_BIN="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die_usage "unknown option: $1"
      ;;
  esac
done

((SELF_TEST + RUN_LIVE == 1)) || die_usage 'choose exactly one mode'
((SELF_TEST <= 1 && RUN_LIVE <= 1)) || die_usage 'choose exactly one mode'

if ((RUN_LIVE)); then
  [[ -n "$NORI_BIN" ]] || die_usage '--nori-bin is required with --run-live'
  [[ "$NORI_BIN" = /* ]] || die_usage '--nori-bin must be an absolute path'
  [[ -f "$NORI_BIN" && -x "$NORI_BIN" ]] || \
    die_usage '--nori-bin must name an executable file'
elif [[ -n "$NORI_BIN" ]]; then
  die_usage '--nori-bin is valid only with --run-live'
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
  printf 'error: python3 is required\n' >&2
  exit 1
}

TEMP_ROOT_REAL="$(readlink -f "${TMPDIR:-/tmp}")"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/nori-package-smoke.XXXXXX")"
WORK_REAL="$(readlink -f "$WORK")"
REPORT_CLEANUP=0

cleanup() {
  case "$WORK_REAL" in
    "$TEMP_ROOT_REAL"/nori-package-smoke.*)
      rm -rf -- "$WORK_REAL"
      if ((REPORT_CLEANUP)); then
        printf 'cleanup=passed\n'
      fi
      ;;
    *)
      printf 'error: refusing unsafe cleanup\n' >&2
      ;;
  esac
}
trap cleanup EXIT

HOME="$WORK/home"
XDG_CONFIG_HOME="$WORK/xdg"
INSTALL_ROOT="$WORK/install"
STAGING="$WORK/staging"
LINK_NAME="senior-infra-ops-analyst-package-smoke"
PROFILE_NAME="personal/senior-infra-ops-analyst-package-smoke"
export HOME XDG_CONFIG_HOME
mkdir -p "$HOME" "$XDG_CONFIG_HOME" "$INSTALL_ROOT/.claude"
printf '%s\n' \
  'operator-content-sentinel' \
  '# BEGIN NORI-AI MANAGED BLOCK' \
  '' \
  '# END NORI-AI MANAGED BLOCK' \
  >"$INSTALL_ROOT/.claude/CLAUDE.md"

create_fake_nori() {
  local fake="$WORK/fake-nori"
  cat >"$fake" <<'FAKE_NORI'
#!/usr/bin/env bash
set -euo pipefail
if [[ "$*" == '--version' ]]; then
  printf 'nori-skillsets test-double\n'
  exit 0
fi
if [[ "$*" == '--help' ]]; then
  printf '%s\n' '--install-dir PATH' '--non-interactive' '--agent NAME' 'link' 'switch' 'claude-code'
  exit 0
fi
if [[ "$*" == 'link --help' ]]; then
  printf '%s\n' 'link PATH --name NAME'
  exit 0
fi
if [[ "$*" == 'switch --help' ]]; then
  printf '%s\n' 'switch --agent NAME'
  exit 0
fi

install_dir=''
agent=''
positionals=()
while (($#)); do
  case "$1" in
    --non-interactive|-n)
      shift
      ;;
    --install-dir|-d)
      install_dir="$2"
      shift 2
      ;;
    --agent|-a)
      agent="$2"
      shift 2
      ;;
    *)
      positionals+=("$1")
      shift
      ;;
  esac
done

case "${positionals[0]:-}" in
  link)
    source_path="${positionals[1]:-}"
    [[ "${positionals[2]:-}" == '--name' ]]
    profile_name="${positionals[3]:-}"
    profile_path="$HOME/.nori/profiles/personal/$profile_name"
    mkdir -p "$(dirname "$profile_path")"
    ln -s "$source_path" "$profile_path"
    ;;
  switch)
    profile_name="${positionals[1]:-}"
    [[ "$agent" == 'claude-code' ]]
    source_path="$(readlink -f "$HOME/.nori/profiles/$profile_name")"
    destination="$install_dir/.claude/CLAUDE.md"
    mkdir -p "$(dirname "$destination")"
    mkdir -p "$install_dir/.claude/skills" "$install_dir/.claude/agents" \
      "$install_dir/.claude/commands"
    cp -R "$source_path/skills/." "$install_dir/.claude/skills/"
    mkdir -p "$install_dir/.claude/skills/read-the-damn-docs"
    printf '%s\n' '---' 'description: Test dependency' '---' \
      >"$install_dir/.claude/skills/read-the-damn-docs/SKILL.md"
    cp "$source_path"/subagents/*.md "$install_dir/.claude/agents/"
    cp "$source_path"/slashcommands/*.md "$install_dir/.claude/commands/"
    existing=''
    if [[ -f "$destination" ]]; then
      existing="$(sed '/# BEGIN NORI-AI MANAGED BLOCK/,/# END NORI-AI MANAGED BLOCK/d' "$destination")"
    fi
    {
      printf '%s\n' "$existing"
      printf '# BEGIN NORI-AI MANAGED BLOCK\n'
      cat "$source_path/AGENTS.md"
      printf '\n# Nori Skills System\n\n## Available Skills\n\nFound packaged skills.\n'
      printf '# END NORI-AI MANAGED BLOCK\n'
    } >"$destination.tmp"
    mv "$destination.tmp" "$destination"
    ;;
  *)
    exit 64
    ;;
esac
FAKE_NORI
  chmod 0700 "$fake"
  NORI_BIN="$fake"
}

if ((SELF_TEST)); then
  create_fake_nori
else
  NORI_BIN="$(readlink -f "$NORI_BIN")"
fi
export PATH="$(dirname "$NORI_BIN"):$PATH"

version_output="$("$NORI_BIN" --version 2>/dev/null)" || {
  printf 'error: Nori version detection failed\n' >&2
  exit 1
}
top_help="$("$NORI_BIN" --help 2>/dev/null)" || {
  printf 'error: Nori help detection failed\n' >&2
  exit 1
}
link_help="$("$NORI_BIN" link --help 2>/dev/null)" || {
  printf 'error: Nori link capability detection failed\n' >&2
  exit 1
}
switch_help="$("$NORI_BIN" switch --help 2>/dev/null)" || {
  printf 'error: Nori switch capability detection failed\n' >&2
  exit 1
}

grep -q -- '--install-dir' <<<"$top_help" || {
  printf 'error: Nori lacks --install-dir\n' >&2
  exit 1
}
grep -q -- '--non-interactive' <<<"$top_help" || {
  printf 'error: Nori lacks --non-interactive\n' >&2
  exit 1
}
grep -q -- 'claude-code' <<<"$top_help" || {
  printf 'error: Nori lacks claude-code support\n' >&2
  exit 1
}
grep -q -- '--name' <<<"$link_help" || {
  printf 'error: Nori link lacks --name\n' >&2
  exit 1
}
grep -q -- '--agent' <<<"$switch_help" || {
  printf 'error: Nori switch lacks --agent\n' >&2
  exit 1
}

"$PYTHON_BIN" "$ROOT/scripts/build_nori_staging.py" \
  --source "$ROOT" \
  --destination "$STAGING" \
  >"$WORK/staging.log" 2>&1 || {
    printf 'error: staging construction failed\n' >&2
    exit 1
  }

"$NORI_BIN" --non-interactive link "$STAGING" --name "$LINK_NAME" \
  >"$WORK/link.log" 2>&1 || {
    printf 'error: isolated Nori link failed\n' >&2
    exit 1
  }
"$NORI_BIN" --non-interactive --install-dir "$INSTALL_ROOT" --agent claude-code \
  switch "$PROFILE_NAME" >"$WORK/switch.log" 2>&1 || {
    printf 'error: isolated Nori switch failed\n' >&2
    exit 1
  }

mapfile -d '' installed_files < <(
  find "$INSTALL_ROOT" -type f -name CLAUDE.md -print0
)
if ((${#installed_files[@]} != 1)); then
  printf 'error: expected exactly one installed CLAUDE.md\n' >&2
  exit 1
fi

verification="$("$PYTHON_BIN" - \
  "$STAGING" "${installed_files[0]}" "$INSTALL_ROOT" <<'PY'
import json
import re
import sys
from pathlib import Path

staging = Path(sys.argv[1])
source = (staging / "AGENTS.md").read_text(encoding="utf-8").replace("\r\n", "\n")
installed = Path(sys.argv[2]).read_text(encoding="utf-8").replace("\r\n", "\n")
install_root = Path(sys.argv[3]) / ".claude"
pattern = re.compile(
    r"# BEGIN NORI-AI MANAGED BLOCK\n([\s\S]*?)\n"
    r"# END NORI-AI MANAGED BLOCK\n?"
)
matches = list(pattern.finditer(installed))
managed = matches[0].group(1) if len(matches) == 1 else ""
outside = pattern.sub("", installed)
source_skills = sorted(
    path.name for path in (staging / "skills").iterdir()
    if path.is_dir() and (path / "SKILL.md").is_file()
)
manifest = json.loads((staging / "nori.json").read_text(encoding="utf-8"))
dependency_skills = sorted(manifest["dependencies"]["skills"])
installed_skills = sorted(
    path.name for path in (install_root / "skills").iterdir()
    if path.is_dir() and (path / "SKILL.md").is_file()
)
source_subagents = sorted(path.stem for path in (staging / "subagents").glob("*.md"))
installed_subagents = sorted(path.stem for path in (install_root / "agents").glob("*.md"))
source_commands = sorted(path.stem for path in (staging / "slashcommands").glob("*.md"))
installed_commands = sorted(path.stem for path in (install_root / "commands").glob("*.md"))
evidence = {
    "managedBlockCount": len(matches),
    "canonicalContent": managed.startswith(source),
    "skillsSectionCount": managed.count("# Nori Skills System"),
    "unmanagedSentinel": "operator-content-sentinel" in outside,
    "sourceSkillCount": len(source_skills),
    "installedSkillCount": len(installed_skills),
    "packagedSkillsComplete": set(source_skills).issubset(installed_skills),
    "unexpectedSkillsAbsent": not (
        set(installed_skills) - set(source_skills)
        - set(dependency_skills) - {"nori-info"}
    ),
    "subagentCount": len(installed_subagents),
    "subagentsExact": installed_subagents == source_subagents,
    "commandCount": len(installed_commands),
    "commandsExact": installed_commands == source_commands,
}
print(json.dumps(evidence, separators=(",", ":"), sort_keys=True))
if evidence != {
    "managedBlockCount": 1,
    "canonicalContent": True,
    "skillsSectionCount": 1,
    "unmanagedSentinel": True,
    "sourceSkillCount": 25,
    "installedSkillCount": 26,
    "packagedSkillsComplete": True,
    "unexpectedSkillsAbsent": True,
    "subagentCount": 12,
    "subagentsExact": True,
    "commandCount": 20,
    "commandsExact": True,
}:
    raise SystemExit(1)
PY
)" || {
  printf 'error: installed instruction verification failed\n' >&2
  printf '%s\n' "$verification" >&2
  exit 1
}

version_line="$(printf '%s\n' "$version_output" | head -n 1 | tr -cd 'A-Za-z0-9._ -')"
version_line="${version_line:0:80}"
printf 'noriVersion=%s\n' "$version_line"
printf '%s\n' "$verification"
REPORT_CLEANUP=1
