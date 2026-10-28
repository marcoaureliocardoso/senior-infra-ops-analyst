#!/usr/bin/env python3
"""One-shot MAIN-only offline qualification. Default mode is pure and non-native."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import uuid

from browser_context_contract import (REASONS, STAGES, exact, finish_stage, integer,
    label, public_main, stage_policy, validate_main)
from browser_context_gateway import Gateway, strict_json
from browser_context_sdk import build_options, detect_sdk, is_sdk_client, recognized_shutdown_protocol, run_stage
from terminal_cancellation import TerminalCancellation

ROOT=Path(__file__).resolve().parents[1]
HELPERS=("browser_context_contract.py","browser_context_sdk.py","browser_context_gateway.py",
         "browser_context_project.py","offline-browser-context-smoke.py","terminal_cancellation.py")
OUTER_REASONS=REASONS|{"ARTIFACT_CHANGED","ISOLATION_UNPROVEN"}


def _private_claim(path):
    try:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            info=os.fstat(fd)
            return (stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode)==0o600 and info.st_uid==os.getuid()
                    and info.st_size==8 and os.read(fd,9)==b"claimed\n")
        finally:os.close(fd)
    except OSError:return False


def _mcp_signal(path,stage,nonce):
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size>4096:return False
        value=strict_json(path.read_bytes())
        if type(value) is not dict or not set(value)<={"connected","toolsListed","visibleToolCount","called","callCount","runNonce"}:return False
        if value.get("connected") is not True or value.get("toolsListed") is not True or value.get("visibleToolCount")!=1:return False
        if stage=="use":return value.get("called") is True and type(value.get("callCount")) is int and value["callCount"]==1 and value.get("runNonce")==nonce
        return not value.get("called") and value.get("callCount",0)==0
    except (OSError,ValueError):return False


def bind_project(project,nonce,session):
    """Only owned local settings. No key confirmation or operator preferences."""
    config=project["config"];value=strict_json(config.read_bytes())
    value.setdefault("hooks",{}).setdefault("PreToolUse",[]).append({"matcher":"Agent","hooks":[{
        "type":"command","command":"python3","args":[str(project["project"]/".claude/measurement-guard.py"),
        str(project["claim"]),session],"timeout":5}]})
    config.write_text(json.dumps(value,separators=(",",":"))+"\n",encoding="utf-8")
    owned=project["project"].parent
    (owned/"empty-mcp.json").write_text('{"mcpServers":{}}\n')
    (owned/"fixture-mcp.json").write_text(json.dumps({"mcpServers":{"p004b-context":{
        "command":"python3","args":[str(project["project"]/".claude/context-fixture.py"),str(project["signal"]),nonce]}}})+"\n")


def policy_signature(project):
    root=project["project"]
    paths=[root/"CLAUDE.md",root.parent/"empty-mcp.json",root.parent/"fixture-mcp.json"]
    for directory in (root/".claude",root/"references"):
        paths.extend(p for p in directory.rglob("*") if not p.is_dir())
    return tuple((str(p.relative_to(root.parent)),file_hash(p)) for p in sorted(paths))


def dispose_owned(root,identity,prefix):
    current=root.lstat()
    if (root.parent!=Path("/tmp") or not root.name.startswith(prefix) or stat.S_ISLNK(current.st_mode) or
        (current.st_dev,current.st_ino)!=(identity.st_dev,identity.st_ino) or not shutil.rmtree.avoids_symlink_attacks):
        raise ValueError("CLEANUP_INCONCLUSIVE")
    shutil.rmtree(root)
    return not root.exists()


async def run_main(client_factory,gateway,project,*,nonce,requested_session,deadline):
    """Four sequential owned connections; retain private identity only until reduction."""
    label(nonce);label(requested_session)
    records=[];session=requested_session;closed=True;cleanup=False
    gateway.user_queries=0;gateway.context_calls=0
    try:
        bind_project(project,nonce,session)
        with gateway:
            for index,stage in enumerate(STAGES):
                if time.monotonic()>=deadline:raise TimeoutError()
                gateway.begin_stage(stage);policy=stage_policy(stage,nonce)
                fixed_policy=policy_signature(project)
                client=client_factory(policy,session,index>0)
                class Counted:
                    async def connect(self):return await client.connect()
                    async def receive_messages(self):
                        async for message in client.receive_messages():yield message
                    async def get_context_usage(self):
                        gateway.context_calls+=1;return await client.get_context_usage()
                    async def query(self,prompt):
                        gateway.user_queries+=1;return await client.query(prompt)
                    async def disconnect(self):return await client.disconnect()
                stage_client=client if is_sdk_client(client) and not recognized_shutdown_protocol() else Counted()
                result=await run_stage(stage_client,policy,session,resume=index>0,before_query=gateway.arm,
                    history_check=lambda:gateway.snapshot()["historyLinked"].get(stage) is True,
                    claim_check=lambda:_private_claim(project["claim"]),stage_deadline=min(deadline,time.monotonic()+120))
                closed=closed and result["clientsClosed"]
                record=result["record"]
                if policy_signature(project)!=fixed_policy:
                    record=finish_stage(stage,record["before"],record["after"],{**record["witness"],"policyFixed":False})
                fault=gateway.snapshot()["fault"]
                if fault!="NONE":record=finish_stage(stage,record["before"],record["after"],{**record["witness"],"fault":fault})
                if stage in ("discovery","use") and not _mcp_signal(project["signal"],stage,nonce):
                    record=finish_stage(stage,record["before"],record["after"],{**record["witness"],"fault":"STATE_UNPROVEN"})
                records.append(record)
                if record["outcome"]!="QUALIFIED" or not closed:break
                if result["sessionId"]!=session:raise ValueError("SESSION_UNPROVEN")
                session=result["sessionId"]  # actual init/result identity, not a replacement for missing evidence
    except (Exception,asyncio.CancelledError):
        if not records:
            from browser_context_sdk import StageEvents
            w=StageEvents(stage_policy("skill",nonce),requested_session).snapshot()
            w["fault"]="OPERATION_TIMEOUT" if time.monotonic()>=deadline else "STATE_UNPROVEN"
            records.append(finish_stage("skill",None,None,w))
        elif all(r["outcome"]=="QUALIFIED" for r in records):
            r=records[-1];records[-1]=finish_stage(r["stage"],r["before"],r["after"],{**r["witness"],"fault":"STATE_UNPROVEN"})
    finally:
        # No client can use this history after close. Parent independently removes the entire inode-owned root.
        try:
            for name in ("project","home"):
                path=project[name]
                if path.is_symlink() or not path.is_dir():raise ValueError()
                shutil.rmtree(path)
            for name in ("claim","signal"):
                path=project[name]
                if path.is_symlink():raise ValueError()
                if path.exists():path.unlink()
            cleanup=closed and gateway.stopped and time.monotonic()<deadline
        except Exception:cleanup=False
    final=gateway.snapshot()
    if final["fault"]!="NONE" and records:
        r=records[-1];records[-1]=finish_stage(r["stage"],r["before"],r["after"],{**r["witness"],"fault":final["fault"]})
    success=len(records)==4 and all(r["outcome"]=="QUALIFIED" for r in records) and cleanup
    reason="CLEANUP_INCONCLUSIVE" if not cleanup else next((r["reason"] for r in records if r["outcome"]!="QUALIFIED"),"NONE" if success else "STATE_UNPROVEN")
    return validate_main(dict(schema="MAIN_STAGE_CONTEXT_V2",schemaVersion=2,runNonce=nonce,sessionId=requested_session,
        stages=records,outcome="MAIN_STAGE_QUALIFIED" if success else "INCONCLUSIVE",reason=reason,cleanupVerified=cleanup),nonce,requested_session)


def file_hash(path):
    if path.is_symlink() or not path.is_file():raise ValueError("ARTIFACT_CHANGED")
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def _mapped_path(value):
    if os.name=="posix" and re.match(r"^[A-Za-z]:[/\\]",value):
        return Path("/mnt/"+value[0].lower()+"/"+value[3:].replace("\\","/"))
    return Path(value)


def source_snapshot(source,*,clean=True):
    """Explicit git-dir handles Windows linked-worktree pointers without editing metadata."""
    gitfile=source/".git"
    if gitfile.is_file():
        value=gitfile.read_text().strip()
        if not value.startswith("gitdir: "):raise ValueError("ARTIFACT_CHANGED")
        gitdir=_mapped_path(value[8:]);gitdir=gitdir if gitdir.is_absolute() else (source/gitdir).resolve()
    else:gitdir=gitfile
    base=["git","-c","safe.directory="+str(source),"--git-dir="+str(gitdir),"--work-tree="+str(source)]
    def read(args):
        p=subprocess.run(base+args,capture_output=True,env={"PATH":os.environ.get("PATH","/usr/bin:/bin")},timeout=25)
        if p.returncode or len(p.stdout)>4*1024*1024:raise ValueError("ARTIFACT_CHANGED")
        return p.stdout
    commit=read(["rev-parse","HEAD"]).decode().strip()
    if not re.fullmatch("[0-9a-f]{40}",commit):raise ValueError("ARTIFACT_CHANGED")
    if clean and read(["status","--porcelain","--untracked-files=normal"]):raise ValueError("ARTIFACT_CHANGED")
    paths=[Path(p.decode()) for p in read(["ls-files","-z"]).split(b"\0") if p]
    if any(p.is_absolute() or ".." in p.parts for p in paths):raise ValueError("ARTIFACT_CHANGED")
    return commit,paths


def fingerprint(source,cli_path,sdk_root,node_path):
    source=source.resolve(strict=True);commit,paths=source_snapshot(source)
    sdk=sdk_root.resolve(strict=True);dependencies={}
    if not (sdk/"claude_agent_sdk").is_dir():raise ValueError("CAPABILITY_UNAVAILABLE")
    for path in sorted(sdk.rglob("*")):
        if "__pycache__" in path.parts:continue
        if path.is_symlink():raise ValueError("ARTIFACT_CHANGED")
        if path.is_file():dependencies[path.relative_to(sdk).as_posix()]=file_hash(path)
    payload=dict(sourceCommit=commit,files={p.as_posix():file_hash(source/p) for p in paths},
                 dependencies=dependencies,cli=file_hash(cli_path.resolve(strict=True)),node=file_hash(node_path.resolve(strict=True)),
                 python=file_hash(Path(sys.executable).resolve(strict=True)))
    sha=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return sha,commit


def reserve(path,expected,supplied,commit):
    if not re.fullmatch("[0-9a-f]{64}",str(supplied)) or supplied!=expected:raise ValueError("ARTIFACT_CHANGED")
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    value=dict(artifactSHA256=expected,sourceCommit=commit,status="GRANT_CONSUMED",reservedAtUtc=datetime.now(timezone.utc).isoformat(),
               userQueries=4,contextCalls=8,generationAttempts=40,countAttempts=192,countPerStage=48,
               operationSeconds=25,stageSeconds=120,totalSeconds=600,mainClients=4,auxiliaryProbesPerClient=1,
               providerAllowed=False,operatorStateAllowed=False,automaticRetries=0)
    with os.fdopen(fd,"w") as stream:json.dump(value,stream);stream.flush();os.fsync(stream.fileno())


def empty_report(sha,commit):
    return dict(artifactSHA256=sha,sourceCommit=commit,outcome="INCONCLUSIVE",reason="STATE_UNPROVEN",main=None,
        traffic=dict(userQueries=0,contextCalls=0,generationAttempts=0,countAttempts=0,stageCounts=dict.fromkeys(STAGES,0)),
        elapsedSeconds=0,cleanupVerified=False)


def validate_outer(value):
    exact(value,{"artifactSHA256","sourceCommit","outcome","reason","main","traffic","elapsedSeconds","cleanupVerified"})
    if not re.fullmatch("[0-9a-f]{64}",value["artifactSHA256"]) or not re.fullmatch("[0-9a-f]{40}",value["sourceCommit"]):raise ValueError("invalid artifact")
    t=exact(value["traffic"],{"userQueries","contextCalls","generationAttempts","countAttempts","stageCounts"})
    for key,maximum in (("userQueries",4),("contextCalls",8),("generationAttempts",41),("countAttempts",193)):integer(t[key],maximum)
    exact(t["stageCounts"],STAGES)
    for n in t["stageCounts"].values():integer(n,49)
    if sum(t["stageCounts"].values())!=t["countAttempts"]:raise ValueError("invalid counting facts")
    if type(value["cleanupVerified"]) is not bool or value["reason"] not in OUTER_REASONS:raise ValueError("invalid result")
    elapsed=value["elapsedSeconds"]
    if type(elapsed) not in (int,float) or not 0<=elapsed<=600:raise ValueError("invalid deadline")
    main=value["main"]
    if main is not None:
        exact(main,{"schema","schemaVersion","stages","outcome","reason","cleanupVerified"})
        validate_main({**main,"runNonce":"public-validation","sessionId":"public-validation"},"public-validation","public-validation")
    success=(main is not None and main["outcome"]=="MAIN_STAGE_QUALIFIED" and value["cleanupVerified"] and
             t["userQueries"]==4 and t["contextCalls"]==8 and 4<=t["generationAttempts"]<=40 and
             t["countAttempts"]<=192 and all(x<=48 for x in t["stageCounts"].values()))
    if value["outcome"] not in ("MAIN_STAGE_QUALIFIED","INCONCLUSIVE") or (value["outcome"]=="MAIN_STAGE_QUALIFIED") != (success and value["reason"]=="NONE"):
        raise ValueError("unverified outer success")
    return value


def decode_report(raw):
    if len(raw)>65536:raise ValueError("oversize aggregate")
    return strict_json(raw)


def namespace_command(root,sdk_root,cli_path,node_path,*,audit,parent_net,deadline=None):
    command=[shutil.which("bwrap") or "bwrap","--die-with-parent","--new-session","--unshare-user","--unshare-pid",
        "--unshare-ipc","--unshare-uts","--unshare-net","--cap-drop","ALL","--ro-bind","/usr","/usr",
        "--tmpfs","/usr/local","--symlink","usr/bin","/bin","--symlink","usr/sbin","/sbin",
        "--symlink","usr/lib","/lib","--symlink","usr/lib64","/lib64","--dev","/dev","--proc","/proc",
        "--dir","/etc","--dir","/home","--dir","/root","--dir","/run","--dir","/tmp","--dir","/mnt",
        "--dir","/opt","--dir","/opt/probe","--bind",str(root),"/work","--chdir","/work"]
    for name in HELPERS:command += ["--ro-bind",str(ROOT/"tests"/name),"/opt/probe/"+name]
    if sdk_root is not None:
        command += ["--ro-bind",str(sdk_root),"/opt/sdk","--tmpfs","/opt/sdk/claude_agent_sdk/_bundled"]
    if not audit:
        command += ["--ro-bind",str(root/"source"),"/work/source",
                    "--ro-bind",str(cli_path),"/opt/probe/claude","--ro-bind",str(node_path),"/opt/probe/node"]
    command += ["--clearenv","--setenv","PATH","/opt/probe:/usr/bin:/bin","--setenv","HOME","/work/home",
        "--setenv","PYTHONNOUSERSITE","1","--setenv","PYTHONDONTWRITEBYTECODE","1",
        "--setenv","PYTHONPATH","/opt/probe:/work/source:/work/source/tests:/opt/sdk","/usr/bin/python3","-B","/opt/probe/offline-browser-context-smoke.py",
        "--inner-audit" if audit else "--inner-offline",str(parent_net),str(deadline if deadline is not None else time.monotonic()+600)]
    return command


def collect(process,cancellation,deadline):
    data=bytearray();eof=False;os.set_blocking(process.stdout.fileno(),False)
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout,selectors.EVENT_READ)
        while not (eof and process.poll() is not None):
            cancellation.check()
            if time.monotonic()>=deadline:raise TimeoutError()
            for _,_ in selector.select(.02):
                chunk=os.read(process.stdout.fileno(),65537-len(data))
                if chunk:data.extend(chunk)
                else:eof=True;selector.unregister(process.stdout)
                if len(data)>65536:raise ValueError("oversize aggregate")
    return process.returncode,bytes(data)


def run_namespace(*,audit,sdk_root,cli_path,node_path,deadline):
    root=Path(tempfile.mkdtemp(prefix="p004b-stage-context-",dir="/tmp"));identity=root.lstat()
    result={"outcome":"INCONCLUSIVE","reason":"ISOLATION_UNPROVEN"};owned=False;cleanup=False;process=None
    try:
        if not audit:
            from scripts.nori_package import build_staging
            source=root/"source";build_staging(ROOT,source)
            # Validator/configurator dependencies only; no user config, git metadata or external dependency.
            for name in ("scripts/nori_package.py","subagent_runtime_policy.py","tests/validate-installed-subagents.py",
                         "tests/command_guard_install_policy.py","tests/context_continuity_install_policy.py",
                         "tests/browser-measurement-guard.py","tests/mcp-context-fixture.py"):
                target=source/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
        command=namespace_command(root,sdk_root,cli_path,node_path,audit=audit,parent_net=Path("/proc/self/ns/net").stat().st_ino,deadline=deadline-.8)
        with TerminalCancellation() as cancellation:
            try:
                process=cancellation.spawn(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                    env={"PATH":"/usr/bin:/bin"},start_new_session=True)
                code,raw=collect(process,cancellation,deadline-.8)
                candidate=decode_report(raw)
                if audit:
                    exact(candidate,{"outcome","networkIsolated","operatorStateHidden","capabilitiesDropped"})
                    if candidate["outcome"]!="ISOLATION_AUDIT_PASSED" or any(candidate[k] is not True for k in candidate if k!="outcome") or code:raise ValueError()
                else:
                    exact(candidate,{"main","traffic","reason"})
                    if candidate["main"] is not None:public_main(candidate["main"])
                result=candidate
            finally:
                if process is not None:
                    cancellation.terminate_child(process)
                    if process.stdout:process.stdout.close()
        owned=process is not None and process.poll() is not None
    except Exception:pass
    finally:
        try:cleanup=dispose_owned(root,identity,"p004b-stage-context-")
        except Exception:cleanup=False
    result["cleanupVerified"]=cleanup and owned and time.monotonic()<deadline
    if audit:result["nativeExecutablesMounted"]=0
    if not result["cleanupVerified"]:result.update(outcome="INCONCLUSIVE",reason="CLEANUP_INCONCLUSIVE")
    return result


def audit_namespace(parent_net):
    caps=next(line.split(":",1)[1].strip() for line in Path("/proc/self/status").read_text().splitlines() if line.startswith("CapEff:"))
    if (Path("/proc/self/ns/net").stat().st_ino==parent_net or {name for _,name in socket.if_nameindex()}!={"lo"} or
        int(caps,16)!=0 or Path("/mnt/c").exists() or any(Path("/home").iterdir()) or any(Path("/root").iterdir())):
        raise ValueError("ISOLATION_UNPROVEN")
    return dict(outcome="ISOLATION_AUDIT_PASSED",networkIsolated=True,operatorStateHidden=True,capabilitiesDropped=True)


def inner(arguments):
    audit_namespace(int(arguments[1]))
    if arguments[0]=="--inner-audit":return audit_namespace(int(arguments[1]))
    deadline=float(arguments[2])
    if not time.monotonic()<deadline<=time.monotonic()+600:raise ValueError("OPERATION_TIMEOUT")
    from browser_context_project import prepare_project
    import claude_agent_sdk as sdk
    if not detect_sdk(sdk)["available"]:raise ValueError("CAPABILITY_UNAVAILABLE")
    work=Path("/work/owned");work.mkdir(mode=0o700)
    project=prepare_project(Path("/work/source"),work,node_path=Path("/opt/probe/node"))
    nonce=uuid.uuid4().hex;session=str(uuid.uuid4());g=Gateway(nonce)
    def factory(policy,sid,resume):
        options=build_options(policy,work,Path("/opt/probe/claude"),sid,resume=resume)
        # This process inherited only the namespace's synthetic environment.
        options.env={"HOME":str(project["home"]),"CLAUDE_CONFIG_DIR":str(project["home"]/".claude"),
            "ANTHROPIC_API_KEY":"synthetic-offline-only-key","ANTHROPIC_BASE_URL":f"http://127.0.0.1:{g.port}",
            "ANTHROPIC_MODEL":"synthetic-model","DISABLE_NONESSENTIAL_TRAFFIC":"1","CLAUDE_CODE_MAX_RETRIES":"0"}
        return sdk.ClaudeSDKClient(options)
    main=asyncio.run(run_main(factory,g,project,nonce=nonce,requested_session=session,deadline=deadline))
    snap=g.snapshot()
    return dict(main=main,traffic=dict(userQueries=g.user_queries,contextCalls=g.context_calls,
        generationAttempts=snap["generationAttempts"],countAttempts=snap["countAttempts"],stageCounts=snap["stageCounts"]),reason=main["reason"])


def self_test():
    from browser_context_contract import offline_usage
    value={"context":dict(totalTokens=100,maxTokens=10000,rawMaxTokens=10000,percentage=1,autoCompactEnabled=True,categoryCount=0),
           "apiUsage":{"state":"NULL","values":None}}
    assert offline_usage(value,1)["input_tokens"]==1251
    return dict(scope="SELF_TEST_ONLY",outcome="LOCAL_SELF_TEST_PASSED",nativeProcesses=0)


def main(arguments=None):
    args=list(sys.argv[1:] if arguments is None else arguments)
    if args in ([],["--self-test"]):print(json.dumps(self_test(),sort_keys=True));return 0
    try:
        if len(args)==3 and args[0] in ("--inner-audit","--inner-offline"):
            result=inner(args);print(json.dumps(result,separators=(",",":")));return 0
        parser=argparse.ArgumentParser(add_help=False)
        modes=parser.add_mutually_exclusive_group(required=True)
        modes.add_argument("--fingerprint",action="store_true");modes.add_argument("--audit-isolation",action="store_true");modes.add_argument("--run-offline")
        for name in ("cli","sdk-root","node"):parser.add_argument("--"+name,type=Path,required=True)
        opts=parser.parse_args(args)
        cli=opts.cli.resolve(strict=True);sdk=opts.sdk_root.resolve(strict=True);node=opts.node.resolve(strict=True)
        sha,commit=fingerprint(ROOT,cli,sdk,node)
        if opts.fingerprint:print(json.dumps(dict(artifactSHA256=sha,sourceCommit=commit)));return 0
        if opts.audit_isolation:
            result=run_namespace(audit=True,sdk_root=sdk,cli_path=cli,node_path=node,deadline=time.monotonic()+25)
            print(json.dumps(result,sort_keys=True));return 0 if result.get("outcome")=="ISOLATION_AUDIT_PASSED" else 2
        if opts.run_offline!=sha:raise ValueError("ARTIFACT_CHANGED")
        if not recognized_shutdown_protocol():
            report=empty_report(sha,commit)
            report.update(reason="CAPABILITY_UNAVAILABLE",cleanupVerified=True)
            print(json.dumps(validate_outer(report),sort_keys=True));return 2
        state=ROOT/".superpowers/offline-context";state.mkdir(parents=True,exist_ok=True)
        result_path=state/(sha+".result.json")
        if result_path.exists() or result_path.is_symlink():raise ValueError("STATE_UNPROVEN")
        reserve(state/(sha+".attempt.json"),sha,opts.run_offline,commit)
        started=time.monotonic();report=empty_report(sha,commit)
        inner_result=run_namespace(audit=False,sdk_root=sdk,cli_path=cli,node_path=node,deadline=started+599)
        report["cleanupVerified"]=inner_result.get("cleanupVerified") is True
        report["reason"]=inner_result.get("reason","STATE_UNPROVEN")
        if inner_result.get("main") is not None:report["main"]=public_main(inner_result["main"])
        if inner_result.get("traffic") is not None:report["traffic"]=inner_result["traffic"]
        if fingerprint(ROOT,cli,sdk,node)!=(sha,commit):report["reason"]="ARTIFACT_CHANGED"
        report["elapsedSeconds"]=round(time.monotonic()-started,3)
        if report["main"] is not None and report["main"]["outcome"]=="MAIN_STAGE_QUALIFIED" and report["reason"]=="NONE" and report["cleanupVerified"]:
            report["outcome"]="MAIN_STAGE_QUALIFIED"
        validate_outer(report)
        payload=json.dumps(report,sort_keys=True,separators=(",",":"))
        if len(payload.encode())>65536:raise ValueError("STATE_UNPROVEN")
        fd=os.open(result_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,"w") as stream:stream.write(payload+"\n")
        print(payload);return 0 if report["outcome"]=="MAIN_STAGE_QUALIFIED" else 2
    except (Exception,SystemExit):
        print('{"outcome":"INCONCLUSIVE","reason":"STATE_UNPROVEN"}');return 2


if __name__=="__main__":raise SystemExit(main())
