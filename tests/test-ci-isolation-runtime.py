"""Source-identity tests; no package, network or executable setup."""
from dataclasses import replace
import importlib
import json
import io
from pathlib import Path
import tempfile
import tarfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RuntimeIdentityTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(Path(__file__).with_name("ci_isolation_runtime.py").is_file(),
                        "verified CI runtime identity is not implemented")
        self.m = importlib.import_module("ci_isolation_runtime")

    def lock(self):
        return json.loads((ROOT / "tests/ci-runtime-lock.json").read_text())

    def load(self, record):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lock.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            return self.m.load_runtime_spec(path)

    def test_reviewed_manifest_supplies_immutable_build_identity(self):
        spec = self.m.load_runtime_spec(ROOT / "tests/ci-runtime-lock.json")
        self.assertEqual(spec.version, "0.12.0")
        self.assertEqual(spec.source_commit, "2a76602a8c71f36c1527cf9fc3417d9149822e0c")
        self.assertEqual(spec.source_size, 126452)
        self.assertEqual(spec.source_sha256,
                         "9760d007363e3abba7c747489910f9f82d9fca53ba3bd3282e396fa3c97a3314")
        with self.assertRaises(AttributeError):
            spec.version = "0.9.0"

    def test_manifest_rejects_unqualified_or_injectable_provenance(self):
        mutations = [
            ("version", "0.9.0"), ("architecture", "arm64"),
            ("sourceUrl", "https://example.invalid/latest.tar.xz"),
            ("sourceUrl", "https://github.com/containers/bubblewrap/releases/download/v0.12.0/bubblewrap-0.12.0.tar.xz?override=1"),
            ("sourceSha256", ""), ("sourceSha256", "a" * 63),
            ("sourceCommit", "main"), ("sourceSize", True),
            ("sourceSize", 0), ("sourceSize", 100_000_001),
            ("buildOptions", ["-Dsetuid=true"]), ("unmodelled", "value"),
        ]
        for key, value in mutations:
            record = self.lock()
            record["bubblewrap"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.load(record)

    def test_missing_profile_origin_or_unknown_schema_is_rejected(self):
        for mutation in ("profile", "schema", "extra"):
            record = self.lock()
            if mutation == "profile":
                del record["apparmorSource"]["commit"]
            elif mutation == "schema":
                record["schemaVersion"] = 2
            else:
                record["executor"] = "unmodelled"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.load(record)

    def test_duplicate_keys_and_oversized_lock_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lock.json"
            for text in ('{"schemaVersion":1,"schemaVersion":1}', " " * 16385):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.m.load_runtime_spec(path)

    def test_exact_fixture_digest_and_size_are_both_required(self):
        # Independent standard SHA-256 vector; not an upstream archive receipt.
        spec = replace(self.m.load_runtime_spec(ROOT / "tests/ci-runtime-lock.json"),
                       source_size=3,
                       source_sha256="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        self.assertIsNone(self.m.verify_archive(b"abc", spec))
        for data in (b"abd", b"abcd", b"ab", bytearray(b"abc")):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                self.m.verify_archive(data, spec)

    def test_archive_members_are_validated_before_any_extraction(self):
        self.assertTrue(hasattr(self.m, "extract_verified_archive"), "safe extraction is absent")
        import hashlib
        for name, kind, allowed in (("bubblewrap-0.12.0/meson.build", "file", True),
                                    ("../outside", "file", False),
                                    ("/absolute", "file", False),
                                    ("bubblewrap-0.12.0/link", "symlink", False),
                                    ("bubblewrap-0.12.0/../outside", "file", False)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                buffer = io.BytesIO()
                with tarfile.open(fileobj=buffer, mode="w:xz") as archive:
                    info = tarfile.TarInfo(name)
                    if kind == "symlink":
                        info.type, info.linkname = tarfile.SYMTYPE, "../outside"
                        archive.addfile(info)
                    else:
                        info.size = 3
                        archive.addfile(info, io.BytesIO(b"abc"))
                data = buffer.getvalue()
                spec = replace(self.m.load_runtime_spec(ROOT / "tests/ci-runtime-lock.json"),
                               source_size=len(data), source_sha256=hashlib.sha256(data).hexdigest())
                destination = Path(directory) / "source"
                if allowed:
                    self.m.extract_verified_archive(data, spec, destination)
                    self.assertEqual((destination / name).read_bytes(), b"abc")
                else:
                    with self.assertRaises(ValueError):
                        self.m.extract_verified_archive(data, spec, destination)
                    self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
