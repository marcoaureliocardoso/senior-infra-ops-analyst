"""Canonical local native-artifact projection, NOT Nori installation acceptance."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=(Path("/work/source") if Path(__file__).resolve().parent==Path("/opt/probe")
      else Path(__file__).resolve().parents[1])
sys.path.insert(0,str(ROOT))
from scripts.nori_package import build_staging, discover_subagent_ids, is_link_or_reparse


def validator():
    spec=importlib.util.spec_from_file_location("installed_context_validator",ROOT/"tests/validate-installed-subagents.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def validate_projection(project):
    root=project["project"]/".claude"
    for directory in (root/"agents",root/"skills"):
        if is_link_or_reparse(directory):return ["unsafe installed root"]
        if any(is_link_or_reparse(p) for p in directory.rglob("*")):return ["unsafe installed artifact"]
    return validator().installed_subagent_errors(root/"agents",root/"skills")


def prepare_project(source: Path, owned_root: Path, *, node_path: Path) -> dict:
    if is_link_or_reparse(owned_root) or not owned_root.is_dir() or any(owned_root.iterdir()):
        raise ValueError("STATE_UNPROVEN")
    source=source.resolve(strict=True);root=owned_root.resolve(strict=True);node=node_path.resolve(strict=True)
    staging=root/"canonical";build_staging(source,staging)
    project=root/"project";project.mkdir(mode=0o700)
    home=root/"home";home.mkdir(mode=0o700);(home/".claude").mkdir(mode=0o700)
    native=project/".claude";native.mkdir(mode=0o700)
    shutil.copyfile(staging/"AGENTS.md",project/"CLAUDE.md")
    shutil.copytree(staging/"references",project/"references")
    skills=native/"skills";shutil.copytree(staging/"skills",skills)
    agents=native/"agents";agents.mkdir()
    for role in discover_subagent_ids(staging):
        content=(staging/"subagents"/role/"SUBAGENT.md").read_text(encoding="utf-8")
        (agents/(role+".md")).write_text(content.replace("{{skills_dir}}",skills.as_posix()),encoding="utf-8")
    for original,name in (("browser-measurement-guard.py","measurement-guard.py"),("mcp-context-fixture.py","context-fixture.py")):
        shutil.copyfile(ROOT/"tests"/original,native/name);(native/name).chmod(0o500)
    result=dict(project=project,config=native/"settings.local.json",home=home,
                claim=root/"subagent.claim",signal=root/"mcp-signal.json")
    if validate_projection(result):raise ValueError("POLICY_UNPROVEN")
    env={"HOME":str(home),"CLAUDE_CONFIG_DIR":str(home/".claude"),"PATH":str(node.parent)+":/usr/bin:/bin"}
    for relative in ("browser-operations/scripts/configure-browser-operations.mjs",
                     "command-driven-operations/scripts/configure-native-execution-boundary.mjs"):
        for operation in ("--apply","--check"):
            completed=subprocess.run([str(node),str(skills/relative),operation,"--root",str(project)],
                                     env=env,cwd=project,capture_output=True,timeout=25)
            if len(completed.stdout)>131072 or len(completed.stderr)>131072:raise ValueError("POLICY_UNPROVEN")
            try:value=json.loads(completed.stdout)
            except (ValueError,UnicodeError):raise ValueError("POLICY_UNPROVEN") from None
            if completed.returncode!=2 or value.get("state")!="CONFIGURED_UNPROVEN":raise ValueError("POLICY_UNPROVEN")
    shutil.rmtree(staging)
    return result
