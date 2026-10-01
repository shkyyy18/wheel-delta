"""Bounded wheel archive fingerprinting; no extraction or package import."""

import hashlib
import io
from pathlib import PurePosixPath
import re
import stat
import zipfile
from email.parser import BytesParser
from .common import read_bytes

MAX_ARCHIVE = 64 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024


def fingerprint(data):
    if len(data) > MAX_ARCHIVE:
        raise ValueError("Archive exceeds 64 MiB")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 5000:
                raise ValueError("Too many archive entries")
            names = [e.filename for e in entries]
            if len(names) != len(set(names)):
                raise ValueError("Duplicate ZIP entry")
            total = 0
            for e in entries:
                raw_name = e.orig_filename
                p = PurePosixPath(raw_name)
                if (
                    not raw_name
                    or p.is_absolute()
                    or ".." in p.parts
                    or "\\" in raw_name
                    or ":" in raw_name
                    or "\x00" in raw_name
                ):
                    raise ValueError("Unsafe archive path")
                if e.flag_bits & 1 or stat.S_ISLNK(e.external_attr >> 16):
                    raise ValueError("Encrypted entry or symlink")
                if e.file_size > 32 * 1024 * 1024:
                    raise ValueError("Entry exceeds 32 MiB")
                total += e.file_size
            if total > MAX_TOTAL:
                raise ValueError("Expanded archive exceeds 128 MiB")
            metas = [
                n
                for n in names
                if n.count("/") == 1 and n.endswith(".dist-info/METADATA")
            ]
            if len(metas) != 1:
                raise ValueError("Exactly one dist-info METADATA required")
            prefix = metas[0].split("/")[0]
            if prefix + "/WHEEL" not in names:
                raise ValueError("WHEEL missing")
            raw = archive.read(metas[0])
            if len(raw) > 1024 * 1024:
                raise ValueError("METADATA too large")
            metadata = BytesParser().parsebytes(raw)
            if (
                len(metadata.get_all("Name", [])) != 1
                or len(metadata.get_all("Version", [])) != 1
            ):
                raise ValueError("Exactly one Name/Version required")
            name, version = metadata["Name"], metadata["Version"]
            if not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]*", name
            ) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.!+_-]*", version):
                raise ValueError("Unsupported Name/Version syntax")
            expected = re.sub(r"[-_.]+", "_", name) + "-" + version
            if prefix.lower() != (expected + ".dist-info").lower():
                raise ValueError("Metadata directory mismatch")
            result = {}
            for e in entries:
                if e.is_dir():
                    continue
                path = e.filename
                parts = path.split("/")
                if parts[0] == prefix:
                    parts[0] = "{dist-info}"
                elif parts[0] == expected + ".data":
                    parts[0] = "{data}"
                normalized = "/".join(parts)
                if normalized in result:
                    raise ValueError("Normalized path collision")
                content = archive.read(e)
                if len(content) != e.file_size:
                    raise ValueError("Entry size mismatch")
                result[normalized] = {
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "bytes": len(content),
                }
            return {"name": name, "version": version, "files": result}
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, EOFError) as exc:
        raise ValueError("Unsupported or corrupt wheel") from exc


def compare(before, after):
    norm = lambda n: re.sub(r"[-_.]+", "-", n).lower()
    if norm(before["name"]) != norm(after["name"]):
        raise ValueError("Package names differ")
    changes = []
    for path in sorted(before["files"].keys() | after["files"].keys()):
        old, new = before["files"].get(path), after["files"].get(path)
        if old == new:
            continue
        changes.append(
            {
                "path": path,
                "change": "added"
                if old is None
                else "removed"
                if new is None
                else "changed",
                "kind": "metadata" if path.startswith("{dist-info}/") else "payload",
                "before_bytes": old["bytes"] if old else None,
                "after_bytes": new["bytes"] if new else None,
            }
        )
    return {
        "package": before["name"],
        "before_version": before["version"],
        "after_version": after["version"],
        "changes": changes,
        "finding_count": len(changes),
        "boundary": "Byte differences, not compatibility verdicts. dist-info/data version prefixes normalized. Metadata/RECORD changes are expected and still reported.",
    }


def configure(parser):
    parser.add_argument("before", nargs="?")
    parser.add_argument("after", nargs="?")


def run(args):
    if not args.before or not args.after:
        raise ValueError("Two wheels required")
    return compare(
        fingerprint(read_bytes(args.before, MAX_ARCHIVE)),
        fingerprint(read_bytes(args.after, MAX_ARCHIVE)),
    )


def synthetic(version, files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as z:
        z.writestr(
            f"example_pkg-{version}.dist-info/METADATA",
            f"Metadata-Version: 2.1\nName: example-pkg\nVersion: {version}\n",
        )
        z.writestr(
            f"example_pkg-{version}.dist-info/WHEEL",
            "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        for name, content in files.items():
            z.writestr(name, content)
    return output.getvalue()


def demo():
    return compare(
        fingerprint(
            synthetic(
                "1.0",
                {
                    "example_pkg/a.py": "# original",
                    "example_pkg/data.txt": "example resource",
                },
            )
        ),
        fingerprint(
            synthetic(
                "1.1",
                {"example_pkg/a.py": "# changed", "example_pkg/new.py": "# synthetic"},
            )
        ),
    )
