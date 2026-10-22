"""Check a package against the sizes and sha256 hashes recorded in its manifest."""

import hashlib
import zipfile
from dataclasses import dataclass, field

from ccpack.pack import CHUNK, MANIFEST
from ccpack.package import Package


@dataclass
class VerifyResult:
    checked: int = 0
    total_size: int = 0
    corrupt: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    unexpected: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.corrupt or self.missing)


def verify_package(pkg: Package, log=None) -> VerifyResult:
    result = VerifyResult()
    present = pkg.names()
    listed = pkg.manifest["files"]
    for i, entry in enumerate(listed, 1):
        path = entry["path"]
        if path not in present:
            result.missing.append(path)
            continue
        if log and entry["size"] >= 100 * 1024 * 1024:
            log(f"  [{i}/{len(listed)}] {path}")
        size, digest = _hash_member(pkg, path)
        result.checked += 1
        result.total_size += size
        if digest is None or size != entry["size"] or digest != entry["sha256"]:
            result.corrupt.append(path)
    result.unexpected = sorted(present - {e["path"] for e in listed} - {MANIFEST})
    return result


def _hash_member(pkg: Package, path: str):
    digest, size = hashlib.sha256(), 0
    try:
        with pkg.open_member(path) as f:
            while chunk := f.read(CHUNK):
                digest.update(chunk)
                size += len(chunk)
    except (zipfile.BadZipFile, OSError):  # zip CRC error or unreadable file
        return size, None
    return size, digest.hexdigest()
