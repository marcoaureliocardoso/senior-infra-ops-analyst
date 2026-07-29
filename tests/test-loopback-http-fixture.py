#!/usr/bin/env python3
"""Behavioral tests for the disposable loopback-only HTTP fixture."""
from __future__ import annotations

import subprocess
import shutil
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "loopback-http-fixture.py"


class LoopbackHttpFixtureTests(unittest.TestCase):
    def test_curl_remote_name_does_not_hide_effective_post(self) -> None:
        curl = shutil.which("curl") or shutil.which("curl.exe")
        if curl is None:
            self.skipTest("curl capability unavailable; parser matrix remains mandatory")
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            ready = work / "ready"
            request_log = work / "requests.log"
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(FIXTURE),
                    "--port",
                    "0",
                    "--ready-file",
                    str(ready),
                    "--request-log",
                    str(request_log),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            try:
                for _ in range(100):
                    if ready.is_file():
                        break
                    if process.poll() is not None:
                        self.fail(process.stderr.read().decode())
                    time.sleep(0.02)
                else:
                    self.fail("fixture did not publish its port")

                port = int(ready.read_text(encoding="utf-8"))
                completed = subprocess.run(
                    [
                        curl,
                        "-sS",
                        "-O",
                        "-d",
                        "action=restart",
                        f"http://127.0.0.1:{port}/reload",
                    ],
                    cwd=work,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr.decode(errors="replace"))
                self.assertEqual(request_log.read_text(encoding="utf-8"), "POST /reload\n")
                self.assertTrue((work / "reload").is_file())
            finally:
                process.terminate()
                process.wait(timeout=5)
                if process.stderr is not None:
                    process.stderr.close()

    def test_accepts_supported_paths_without_retaining_headers_or_body(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            ready = work / "ready"
            request_log = work / "requests.log"
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(FIXTURE),
                    "--port",
                    "0",
                    "--ready-file",
                    str(ready),
                    "--request-log",
                    str(request_log),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            try:
                for _ in range(100):
                    if ready.is_file():
                        break
                    if process.poll() is not None:
                        self.fail(process.stderr.read().decode())
                    time.sleep(0.02)
                else:
                    self.fail("fixture did not publish its port")

                port = int(ready.read_text(encoding="utf-8"))
                secret = "SYNTHETIC_DO_NOT_RETAIN"
                request = urllib.request.Request(
                    f"http://127.0.0.1:{port}/reload",
                    data=secret.encode(),
                    headers={"Authorization": f"Bearer {secret}"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    self.assertEqual(response.status, 204)

                log = request_log.read_text(encoding="utf-8")
                self.assertEqual(log, "POST /reload\n")
                self.assertNotIn(secret, log)
            finally:
                process.terminate()
                process.wait(timeout=5)
                if process.stderr is not None:
                    process.stderr.close()

    def test_rejects_unrecognised_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            ready = work / "ready"
            request_log = work / "requests.log"
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(FIXTURE),
                    "--port",
                    "0",
                    "--ready-file",
                    str(ready),
                    "--request-log",
                    str(request_log),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            try:
                for _ in range(100):
                    if ready.is_file():
                        break
                    time.sleep(0.02)
                port = int(ready.read_text(encoding="utf-8"))
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/outside", timeout=5
                    )
                self.assertEqual(raised.exception.code, 404)
            finally:
                process.terminate()
                process.wait(timeout=5)
                if process.stderr is not None:
                    process.stderr.close()


if __name__ == "__main__":
    unittest.main()
