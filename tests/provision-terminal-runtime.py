#!/usr/bin/env python3
"""Explicit test-only locked provisioning. Never called by a context probe."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from terminal_state_adapter import validate_terminal_runtime, TerminalStateError

ROOT=Path(__file__).resolve().parents[1]


def provision(*,target:Path,npm:Path,node:Path)->dict:
    try:
        if (os.name!='posix' or not target.is_absolute() or target.exists() or target.is_symlink()
                or target.parent.resolve(strict=True)!=target.parent or not target.parent.is_dir()
                or target.parent.stat().st_uid!=os.getuid() or target.is_relative_to(ROOT)):
            return {'reasonCode':'TERMINAL_TARGET_REJECTED'}
        for executable in (npm,node):
            if (not executable.is_absolute() or executable.is_symlink()
                    or executable.resolve(strict=True)!=executable or not executable.is_file()
                    or not os.access(executable,os.X_OK)):
                return {'reasonCode':'TERMINAL_PROVISION_FAILED'}
        manifest=ROOT/'tests/terminal-runtime'
        package=json.loads((manifest/'package.json').read_text())
        lock=json.loads((manifest/'package-lock.json').read_text())
        if (package.get('private') is not True or package.get('dependencies')!={'@xterm/headless':'6.0.0'}
                or set(lock['packages'])!={'','node_modules/@xterm/headless'}):
            return {'reasonCode':'TERMINAL_PROVISION_FAILED'}
        target.mkdir(mode=0o700)
        for name in ('package.json','package-lock.json'):
            shutil.copyfile(manifest/name,target/name)
        home=target/'npm-home'; cache=target/'npm-cache'
        home.mkdir(mode=0o700); cache.mkdir(mode=0o700)
        user=target/'user.npmrc'; global_config=target/'global.npmrc'
        user.write_text(''); global_config.write_text('')
        environment={'HOME':str(home),'PATH':str(node.parent)+':/usr/bin:/bin',
            'NPM_CONFIG_USERCONFIG':str(user),'NPM_CONFIG_GLOBALCONFIG':str(global_config),
            'NPM_CONFIG_CACHE':str(cache),'NPM_CONFIG_REGISTRY':'https://registry.npmjs.org/',
            'NPM_CONFIG_UPDATE_NOTIFIER':'false'}
        result=subprocess.run([str(npm),'ci','--ignore-scripts','--no-audit','--no-fund'],
            cwd=target,env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            timeout=120,close_fds=True)
        if result.returncode: return {'reasonCode':'TERMINAL_PROVISION_FAILED'}
        modules=target/'node_modules'
        validate_terminal_runtime(node,modules)
        return {'reasonCode':'TERMINAL_RUNTIME_READY','moduleRoot':str(modules),'node':str(node)}
    except (OSError,ValueError,TypeError,KeyError,subprocess.SubprocessError,TerminalStateError):
        return {'reasonCode':'TERMINAL_PROVISION_FAILED'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path,required=True)
    parser.add_argument('--npm',type=Path,required=True)
    parser.add_argument('--node',type=Path,required=True)
    args=parser.parse_args()
    result=provision(target=args.target,npm=args.npm,node=args.node)
    print(json.dumps(result,sort_keys=True))
    return 0 if result['reasonCode']=='TERMINAL_RUNTIME_READY' else 2


if __name__=='__main__': raise SystemExit(main())
