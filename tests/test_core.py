import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import unittest
import tempfile
import json
from wheel_delta import core
import io
import zipfile
import hashlib


class WheelTests(unittest.TestCase):
    def test_same(self):
        a = core.fingerprint(core.synthetic("1.0", {"p/a.py": "x"}))
        self.assertEqual(core.compare(a, a)["finding_count"], 0)

    def test_changes(self):
        a = core.fingerprint(core.synthetic("1.0", {"p/a.py": "a", "p/gone.txt": "b"}))
        b = core.fingerprint(core.synthetic("1.1", {"p/a.py": "b", "p/new.txt": "c"}))
        r = core.compare(a, b)
        self.assertEqual(
            {x["change"] for x in r["changes"]}, {"added", "removed", "changed"}
        )
        self.assertTrue(any(x["path"] == "{dist-info}/METADATA" for x in r["changes"]))

    def test_no_content_leak(self):
        a = core.fingerprint(core.synthetic("1.0", {"p/a.py": "SECRET_MARKER"}))
        self.assertNotIn("SECRET_MARKER", json.dumps(a))

    def test_bad_zip(self):
        with self.assertRaises(ValueError):
            core.fingerprint(b"not zip")

    def test_unsafe_paths(self):
        for name in ["../xx", "/abcd", "a\\bxx", "C:/xx"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                core.fingerprint(
                    core.synthetic("1.0", {"entry": "bad"}).replace(
                        b"entry", name.encode().ljust(5, b"x")
                    )
                )

    def test_missing_metadata(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as z:
            z.writestr("a.py", "x")
        with self.assertRaises(ValueError):
            core.fingerprint(stream.getvalue())

    def test_duplicate_entry(self):
        import warnings

        stream = io.BytesIO(core.synthetic("1.0", {"a.py": "x"}))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with zipfile.ZipFile(stream, "a") as z:
                z.writestr("a.py", "y")
        with self.assertRaises(ValueError):
            core.fingerprint(stream.getvalue())

    def test_symlink_entry(self):
        stream = io.BytesIO(core.synthetic("1.0", {}))
        with zipfile.ZipFile(stream, "a") as z:
            info = zipfile.ZipInfo("link")
            info.create_system = 3
            info.external_attr = 0o120777 << 16
            z.writestr(info, "target")
        with self.assertRaises(ValueError):
            core.fingerprint(stream.getvalue())

    def test_oversize_entry(self):
        from unittest.mock import patch

        data = core.synthetic("1.0", {"a.py": "x"})
        with patch.object(core, "MAX_TOTAL", 1), self.assertRaises(ValueError):
            core.fingerprint(data)

    def test_different_packages(self):
        a = core.fingerprint(core.synthetic("1.0", {}))
        b = {**a, "name": "different"}
        with self.assertRaises(ValueError):
            core.compare(a, b)
