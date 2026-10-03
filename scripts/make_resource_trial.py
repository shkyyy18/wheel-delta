"""Generate three tiny SYNTHETIC wheel fixtures. No third-party code is used.

Run from the repository root: python scripts/make_resource_trial.py trial-inputs
The destination must not exist. Files are comparison inputs, not packages to use.
"""
import argparse
import base64
import csv
import hashlib
import io
from pathlib import Path
import zipfile

RESOURCE = "example_resource_pkg/templates/welcome.txt"


def wheel_bytes(version, include_resource=True):
    prefix = f"example_resource_pkg-{version}.dist-info"
    files = {
        "example_resource_pkg/__init__.py": b'"""Synthetic resource trial; not a real application."""\n',
        f"{prefix}/METADATA": (
            "Metadata-Version: 2.1\nName: example-resource-pkg\n"
            f"Version: {version}\nSummary: Synthetic comparison fixture\n"
        ).encode(),
        f"{prefix}/WHEEL": (
            "Wheel-Version: 1.0\nGenerator: synthetic-resource-trial\n"
            "Root-Is-Purelib: true\nTag: py3-none-any\n"
        ).encode(),
    }
    if include_resource:
        files[RESOURCE] = b"Hello from a SYNTHETIC template.\n"
    record = io.StringIO(newline="")
    writer = csv.writer(record, lineterminator="\n")
    for name, content in sorted(files.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=")
        writer.writerow([name, "sha256=" + digest.decode("ascii"), len(content)])
    record_name = f"{prefix}/RECORD"
    writer.writerow([record_name, "", ""])
    files[record_name] = record.getvalue().encode()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, content in sorted(files.items()):
            # Fixed timestamp, stored bytes and permissions make inputs reproducible.
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return stream.getvalue()


def generate(destination):
    destination = Path(destination)
    destination.mkdir(exist_ok=False)
    for label, version, resource in [
        ("before", "1.0", True),
        ("version-only", "1.1", True),
        ("missing-resource", "1.1", False),
    ]:
        folder = destination / label
        folder.mkdir()
        wheel = folder / f"example_resource_pkg-{version}-py3-none-any.whl"
        with wheel.open("xb") as output:
            output.write(wheel_bytes(version, resource))
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", help="New output directory; parent must exist")
    args = parser.parse_args()
    try:
        generate(args.destination)
    except OSError:
        parser.exit(2, "Cannot create fixtures. Use a NEW directory; partial outputs may remain.\n")
    print("Created three SYNTHETIC wheels. Follow docs/missing-resource-trial.md.")


if __name__ == "__main__":
    main()
