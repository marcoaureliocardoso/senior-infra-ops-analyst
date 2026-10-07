"""Provisioning effects against an executable fake npm, never a provider."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/'tests/provision-terminal-runtime.py'


class TerminalRuntimeProvisioningTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.is_file(),'terminal provisioning interface missing')
        spec=importlib.util.spec_from_file_location('provision_terminal_runtime',MODULE)
        self.module=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.module)
        self.temp=tempfile.TemporaryDirectory(prefix='terminal-provision-test-')
        self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name)
        self.node=Path(os.environ['P004B_TERMINAL_NODE']).resolve(strict=True)
        self.source=Path(os.environ['P004B_TERMINAL_MODULE_ROOT']).resolve(strict=True)/'@xterm/headless'
        self.trace=self.root/'npm-record'; self.npm=self.root/'fake-npm'
        self.npm.write_text('#!/usr/bin/python3\nimport json,os,sys,shutil\nfrom pathlib import Path\n'
            'record={"args":sys.argv[1:],"envKeys":sorted(os.environ),"hasLock":Path("package-lock.json").is_file()}\n'
            'Path('+repr(str(self.trace))+').write_text(json.dumps(record))\n'
            'target=Path("node_modules/@xterm/headless")\n'
            'target.parent.mkdir(parents=True)\n'
            'shutil.copytree('+repr(str(self.source))+',target)\n')
        self.npm.chmod(0o700)

    def provision(self,target):
        return self.module.provision(target=target,npm=self.npm,node=self.node)

    def test_provisioning_is_locked_isolated_external(self):
        target=self.root/'runtime'
        with mock.patch.dict(os.environ,{'NPM_TOKEN':'synthetic','ANTHROPIC_API_KEY':'synthetic'}):
            result=self.provision(target)
        self.assertEqual(result['reasonCode'],'TERMINAL_RUNTIME_READY')
        self.assertEqual(Path(result['moduleRoot']),target/'node_modules')
        record=json.loads(self.trace.read_text())
        self.assertTrue(record['hasLock'])
        self.assertEqual(record['args'],['ci','--ignore-scripts','--no-audit','--no-fund'])
        self.assertNotIn('NPM_TOKEN',record['envKeys'])
        self.assertNotIn('ANTHROPIC_API_KEY',record['envKeys'])
        self.assertEqual(json.loads((target/'package-lock.json').read_text()),
                         json.loads((ROOT/'tests/terminal-runtime/package-lock.json').read_text()))

    def test_existing_target_is_never_overwritten(self):
        target=self.root/'runtime'; target.mkdir()
        sentinel=target/'operator'; sentinel.write_text('keep')
        result=self.provision(target)
        self.assertEqual(result['reasonCode'],'TERMINAL_TARGET_REJECTED')
        self.assertEqual(sentinel.read_text(),'keep')
        self.assertFalse(self.trace.exists())

    def test_symlink_and_checkout_targets_rejected_before_npm(self):
        protected=self.root/'protected'; protected.mkdir()
        link=self.root/'link'; link.symlink_to(protected)
        for target in (link,ROOT/'tests/forbidden-terminal-runtime'):
            result=self.provision(target)
            self.assertEqual(result['reasonCode'],'TERMINAL_TARGET_REJECTED')
        self.assertFalse(self.trace.exists())
        self.assertEqual(list(protected.iterdir()),[])

    def test_npm_failure_is_closed_not_raw_output(self):
        self.npm.write_text('#!/usr/bin/python3\nimport sys\nprint("unapproved diagnostic",file=sys.stderr)\nsys.exit(1)\n')
        result=self.provision(self.root/'runtime')
        self.assertEqual(result,{'reasonCode':'TERMINAL_PROVISION_FAILED'})


if __name__=='__main__': unittest.main()
