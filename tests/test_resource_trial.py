"""Synthetic fixture and real CLI regression checks; never install input wheels."""
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from make_resource_trial import RESOURCE, generate, wheel_bytes


class ResourceTrialTests(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(wheel_bytes("1.0"), wheel_bytes("1.0"))

    def test_record_hashes_and_sizes(self):
        for version, resource in [("1.0", True), ("1.1", True), ("1.1", False)]:
            with self.subTest(version=version, resource=resource):
                with zipfile.ZipFile(io.BytesIO(wheel_bytes(version, resource))) as z:
                    record = f"example_resource_pkg-{version}.dist-info/RECORD"
                    rows = list(csv.reader(io.StringIO(z.read(record).decode())))
                    self.assertEqual({row[0] for row in rows}, set(z.namelist()))
                    for name, digest, size in rows:
                        if name == record:
                            self.assertEqual((digest, size), ("", ""))
                        else:
                            data = z.read(name)
                            actual = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
                            self.assertEqual(digest, "sha256=" + actual)
                            self.assertEqual(int(size), len(data))

    def test_existing_directory_not_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "inputs"
            generate(destination)
            before = {str(p.relative_to(destination)): p.read_bytes() for p in destination.rglob("*.whl")}
            with self.assertRaises(FileExistsError):
                generate(destination)
            self.assertEqual(before, {str(p.relative_to(destination)): p.read_bytes() for p in destination.rglob("*.whl")})

    def test_real_cli_distinguishes_payload_from_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = generate(Path(tmp) / "inputs")
            before = root / "before/example_resource_pkg-1.0-py3-none-any.whl"
            for label, expected in [("version-only", []), ("missing-resource", [RESOURCE])]:
                after = root / label / "example_resource_pkg-1.1-py3-none-any.whl"
                command = [sys.executable, "-m", "wheel_delta", str(before), str(after)]
                result = subprocess.run(command, cwd=ROOT / "src", capture_output=True, text=True, check=True)
                report = json.loads(result.stdout)
                payload = [c for c in report["changes"] if c["kind"] == "payload"]
                self.assertEqual([c["path"] for c in payload], expected)
                self.assertTrue(all(c["change"] == "removed" for c in payload))
                self.assertEqual([c["path"] for c in report["changes"] if c["kind"] == "metadata"], ["{dist-info}/METADATA", "{dist-info}/RECORD"])
                # Both contain findings, even the intended version-only release.
                flagged = subprocess.run(command + ["--fail-on-findings"], cwd=ROOT / "src", capture_output=True)
                self.assertEqual(flagged.returncode, 1)


if __name__ == "__main__":
    unittest.main()
