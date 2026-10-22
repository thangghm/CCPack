"""Install a package into CapCut's drafts folder so it shows up as a normal project."""

import os
import shutil
import time
import uuid
from dataclasses import dataclass

from ccpack import capcut
from ccpack.pack import CHUNK, FONTS_DIR
from ccpack.package import Package, PackageError
from ccpack.paths import norm
from ccpack.verify import verify_package


@dataclass
class UnpackResult:
    draft_dir: str
    name: str
    fonts: list[str]


def unique_draft_name(drafts_dir: str, name: str) -> str:
    """Same naming CapCut uses for duplicates: "name", then "name (1)", "name (2)"…"""
    candidate, i = name, 1
    while os.path.exists(os.path.join(drafts_dir, candidate)):
        candidate, i = f"{name} ({i})", i + 1
    return candidate


def unpack_package(pkg: Package, drafts_dir: str, name: str | None = None, verify=True, log=print) -> UnpackResult:
    if not os.path.isdir(drafts_dir):
        raise PackageError(f"Không thấy thư mục project của CapCut: {drafts_dir}. "
                           "Mở CapCut một lần, hoặc chỉ định bằng --drafts-dir.")
    if verify:
        log("Kiểm tra gói…")
        result = verify_package(pkg, log)
        if not result.ok:
            raise PackageError(f"Gói bị hỏng: {len(result.corrupt)} file sai hash, {len(result.missing)} file bị thiếu "
                               "(chạy `ccpack verify` để xem chi tiết).")

    root = pkg.root
    _check_name(root)
    target_name = unique_draft_name(drafts_dir, name or pkg.manifest["draft"]["name"])
    _check_name(target_name)
    target = os.path.join(drafts_dir, target_name)

    # Dot-folders are ignored by CapCut (.recycle_bin, .cloud_cache_*), so a half-written
    # unpack never shows up as a broken project.
    staging = os.path.join(drafts_dir, f".ccpack-unpacking-{uuid.uuid4().hex[:8]}")
    staged_draft = os.path.join(staging, "draft")
    fonts = []
    try:
        log(f"Giải nén vào {target}…")
        for member in sorted(pkg.names()):
            if member.startswith(root + "/"):
                rel = member[len(root) + 1:]
            elif member.startswith(FONTS_DIR + "/"):
                rel = member
            else:
                continue  # manifest.json
            dest = _safe_join(staged_draft, rel)
            _extract(pkg, member, dest)
            if rel.startswith(FONTS_DIR + "/"):
                fonts.append(os.path.join(target, *rel.split("/")))
        if not os.path.isfile(os.path.join(staged_draft, capcut.META_FILE)):
            raise PackageError(f"Gói không chứa {capcut.META_FILE} của project.")
        _fix_meta(staged_draft, drafts_dir, target_name)
        os.replace(staged_draft, target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return UnpackResult(target, target_name, fonts)


def _check_name(name: str):
    if not name or name.startswith(".") or any(c in name for c in "/\\:"):
        raise PackageError(f"Tên project không hợp lệ: {name!r}")


def _safe_join(base: str, rel: str) -> str:
    dest = os.path.normpath(os.path.join(base, *rel.split("/")))
    if os.path.commonpath([os.path.abspath(base), os.path.abspath(dest)]) != os.path.abspath(base):
        raise PackageError(f"Gói chứa đường dẫn không an toàn: {rel}")
    return dest


def _extract(pkg: Package, member: str, dest: str):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with pkg.open_member(member) as fin, open(dest, "wb") as fout:
        while chunk := fin.read(CHUNK):
            fout.write(chunk)
    mtime = pkg.member_mtime(member)
    os.utime(dest, (mtime, mtime))


def _fix_meta(draft_dir: str, drafts_dir: str, name: str):
    """Point the draft at its new folder. CapCut assigns its own draft_id on discovery anyway;
    a fresh one here keeps it from ever matching the source project. The modified time is
    set to now because CapCut's Home list is sorted by tm_draft_modified."""
    now = time.time()
    path = os.path.join(draft_dir, capcut.META_FILE)
    meta = capcut.load_json(path)
    meta.update(
        draft_id=str(uuid.uuid4()).upper(),
        draft_name=name,
        draft_fold_path=norm(os.path.join(os.path.abspath(drafts_dir), name)),
        draft_root_path=norm(os.path.abspath(drafts_dir)),
        tm_draft_modified=int(now * 1_000_000),
    )
    with open(path, "wb") as f:
        f.write(capcut.dump_json_bytes(meta))
    _set_setting(os.path.join(draft_dir, capcut.SETTINGS_FILE), "draft_last_edit_time", str(int(now)))


def _set_setting(path: str, key: str, value: str):
    """Update one key in the small INI-style draft_settings file, if the draft has one."""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8", newline="") as f:
        lines = f.read().splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.split("=", 1)[0].strip() == key:
            ending = line[len(line.rstrip("\r\n")):]
            lines[i] = f"{key}={value}{ending}"
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.writelines(lines)
