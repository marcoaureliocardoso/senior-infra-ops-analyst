#!/usr/bin/env python3
"""Run the real link validator with an offline network-boundary double."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LinkValidationTests(unittest.TestCase):
    def run_validator(self, markdown: str, *, head: str = "200", get: str = "200",
                      as_json: bool = True):
        with tempfile.TemporaryDirectory(prefix="link-validation-") as directory:
            root = Path(directory)
            (root / "tests").mkdir()
            (root / "bin").mkdir()
            shutil.copy2(ROOT / "tests/validate-links.sh", root / "tests")
            (root / "fixture.md").write_text(markdown, encoding="utf-8")
            curl = root / "bin/curl"
            curl.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "with open(os.environ['CURL_LOG'], 'a') as stream:\n"
                "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "print(os.environ['HEAD_CODE' if '-I' in sys.argv else 'GET_CODE'], end='')\n",
                encoding="utf-8",
            )
            curl.chmod(0o755)
            sleep = root / "bin/sleep"
            sleep.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            sleep.chmod(0o755)
            environment = {
                "PATH": f"{root / 'bin'}:/usr/bin:/bin", "HOME": str(root),
                "LC_ALL": "C", "CURL_LOG": str(root / "curl.jsonl"),
                "HEAD_CODE": head, "GET_CODE": get,
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            command = ["bash", "tests/validate-links.sh"]
            if as_json:
                command.append("--json")
            result = subprocess.run(command, cwd=root, env=environment,
                                    capture_output=True, text=True, timeout=10)
            log = root / "curl.jsonl"
            calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            return result, calls

    def test_quoted_json_does_not_become_part_of_the_requested_url(self):
        url = "https://docs.python.org/3/library/json.html"
        result, calls = self.run_validator(f'{{"url":"{url}","locatorRole":"button"}}')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([call[-1] for call in calls], [url])
        self.assertEqual(json.loads(result.stdout)["checked"], 1)

    def test_loopback_and_existing_placeholders_never_reach_curl(self):
        result, calls = self.run_validator("\n".join([
            "http://127.0.0.1:43111", "http://127.42.0.9:43111/path",
            "http://localhost:43111", "http://LOCALHOST:43111",
            "http://[::1]:43111/path", "http://router.local/path",
            "http://host.invalid/path", "http://portal.example.edu/path",
            "http://app02/path", "https://<host>/path",
        ]))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(calls, [])
        self.assertEqual(json.loads(result.stdout)["checked"], 0)

    def test_empty_markdown_is_a_successful_zero_request_report(self):
        result, calls = self.run_validator("# No links\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])
        self.assertEqual(json.loads(result.stdout), {"status": "ok", "checked": 0, "broken": []})

    def test_public_success_is_checked_once_after_deduplication(self):
        url = "https://docs.python.org/3/"
        result, calls = self.run_validator(f"[{url}]({url})\n`{url}`\n'{url}'\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([call[-1] for call in calls], [url])
        self.assertEqual(json.loads(result.stdout), {
            "status": "ok", "checked": 1, "ok": 1, "broken": 0, "broken_urls": [],
        })

    def test_public_failure_remains_nonzero_with_head_and_get(self):
        url = "https://docs.python.org/missing"
        result, calls = self.run_validator(url, head="404", get="404")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual([call[-1] for call in calls], [url, url])
        self.assertIn("-I", calls[0])
        self.assertNotIn("-I", calls[1])
        self.assertEqual(json.loads(result.stdout), {
            "status": "broken", "checked": 1, "ok": 0, "broken": 1,
            "broken_urls": [{"code": "404", "url": url}],
        })

    def test_get_fallback_still_accepts_a_server_that_rejects_head(self):
        result, calls = self.run_validator("https://docs.python.org/3/", head="405")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 2)
        self.assertEqual(json.loads(result.stdout)["ok"], 1)

    def test_broken_url_with_backslash_is_valid_json_not_report_syntax(self):
        url = r"https://docs.python.org/a\b?q=one&mode=two"
        result, calls = self.run_validator(url, head="404", get="404")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual([call[-1] for call in calls], [url, url])
        self.assertEqual(json.loads(result.stdout)["broken_urls"], [{"code": "404", "url": url}])

    def test_human_output_still_fails_for_a_broken_public_link(self):
        result, calls = self.run_validator("https://docs.python.org/missing", head="404",
                                          get="404", as_json=False)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(calls), 2)
        self.assertIn("1 broken link(s) found.", result.stdout)


if __name__ == "__main__":
    unittest.main()
