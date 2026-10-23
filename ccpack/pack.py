"""Write a scanned draft and its media into a .ccpack (zip, stored) or a plain folder.

Layout (same for both):
    manifest.json
    <draft name>/...                      the draft, paths rewritten
    <draft name>/_packed_media/...        user media, referenced via the CapCut placeholder
    _fonts/...                            optional, fonts to install on the target machine
"""

import datetime
import hashlib
import os
import platform
import shutil
import time
import zipfile

from ccpack import __version__, capcut
from ccpack.capcut import PACKED_MEDIA_DIR
from ccpack.i18n import files, tr
from ccpack.scan import ScanResult, human_size

FORMAT = "ccpack"
FORMAT_VERSION = 1
MANIFEST = "manifest.json"
FONTS_DIR = "_fonts"
CHUNK = 8 * 1024 * 1024


class PackError(Exception):
    pass


class _ZipWriter:
    def __init__(self, path):
        self.zf = zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED, allowZip64=True)

    def add_file(self, src, arcname):
        info = zipfile.ZipInfo(arcname, _zip_time(os.path.getmtime(src)))
        info.file_size = os.path.getsize(src)
        digest = hashlib.sha256()
        with open(src, "rb") as fin, self.zf.open(info, "w") as fout:
            while chunk := fin.read(CHUNK):
                digest.update(chunk)
                fout.write(chunk)
        return info.file_size, digest.hexdigest()

    def add_bytes(self, data, arcname):
        self.zf.writestr(zipfile.ZipInfo(arcname, _zip_time(time.time())), data)
        return len(data), hashlib.sha256(data).hexdigest()

    def close(self):
        self.zf.close()


class _FolderWriter:
    def __init__(self, path):
        self.root = path
        os.makedirs(path)

    def _target(self, arcname):
        target = os.path.join(self.root, *arcname.split("/"))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        return target

    def add_file(self, src, arcname):
        target = self._target(arcname)
        digest = hashlib.sha256()
        with open(src, "rb") as fin, open(target, "wb") as fout:
            while chunk := fin.read(CHUNK):
                digest.update(chunk)
                fout.write(chunk)
        shutil.copystat(src, target)
        return os.path.getsize(target), digest.hexdigest()

    def add_bytes(self, data, arcname):
        with open(self._target(arcname), "wb") as f:
            f.write(data)
        return len(data), hashlib.sha256(data).hexdigest()

    def close(self):
        pass


def _zip_time(ts):
    return max(time.localtime(ts)[:6], (1980, 1, 1, 0, 0, 0))


def default_output(scan: ScanResult, as_folder: bool) -> str:
    return scan.draft_name + ("_ccpack" if as_folder else ".ccpack")


def pack_draft(scan: ScanResult, output: str, *, as_folder=False, include_fonts=False,
               allow_missing=False, force=False, log=print) -> dict:
    """Pack the draft described by `scan` into `output`. Returns the manifest."""
    if scan.is_open and not force:
        raise PackError(tr("The project is open in CapCut. Close it (go back to the Home screen) and try again, "
                           "or add --force if you are sure CapCut is not writing to it.",
                           "Project đang mở trong CapCut. Đóng project (về màn hình Home) rồi chạy lại, "
                           "hoặc thêm --force nếu chắc chắn CapCut không ghi vào nó."))
    if scan.missing and not allow_missing:
        n = len(scan.missing)
        raise PackError(tr(f"{files(n)} of media missing (see `ccpack scan`). "
                           "Put them back, or add --allow-missing to pack anyway.",
                           f"Thiếu {n} file media (xem `ccpack scan`). "
                           "Tìm lại file, hoặc thêm --allow-missing để vẫn đóng gói."))
    if os.path.exists(output) and not force:
        raise PackError(tr(f"{output} already exists. Choose another name, or add --force to overwrite.",
                           f"Đã có {output}. Chọn tên khác hoặc thêm --force để ghi đè."))

    partial = output + ".partial"
    _remove(partial)
    writer = _FolderWriter(partial) if as_folder else _ZipWriter(partial)
    try:
        manifest = _write_all(scan, writer, include_fonts, log)
        writer.add_bytes(capcut.dump_json_bytes(manifest), MANIFEST)
        writer.close()
    except BaseException:
        writer.close()
        _remove(partial)
        raise
    _remove(output)
    os.replace(partial, output)
    return manifest


def _write_all(scan: ScanResult, writer, include_fonts, log) -> dict:
    root = scan.draft_name
    files = []

    def record(arcname, size_hash):
        files.append({"path": arcname, "size": size_hash[0], "sha256": size_hash[1]})

    log(tr(f"Packing project '{root}'…", f"Đóng gói project '{root}'…"))
    for full, rel in capcut.iter_draft_files(scan.draft_dir):
        if rel == capcut.LOCK_FILE:
            continue
        arcname = f"{root}/{rel}"
        if rel in scan.rewritten:
            record(arcname, writer.add_bytes(capcut.dump_json_bytes(scan.rewritten[rel]), arcname))
        else:
            record(arcname, writer.add_file(full, arcname))

    media = []
    for i, m in enumerate(scan.media, 1):
        arcname = f"{root}/{PACKED_MEDIA_DIR}/{m.packed_name}"
        log(f"  [{i}/{len(scan.media)}] {m.packed_name} ({human_size(m.size)})")
        size, sha = writer.add_file(m.source, arcname)
        record(arcname, (size, sha))
        media.append({"original_path": m.source, "packed_path": arcname, "size": size, "sha256": sha})

    fonts = []
    used_font_names = set()
    for p in scan.fonts:
        entry = {"original_path": p, "packed_path": None}
        if include_fonts and os.path.isfile(p):
            name = os.path.basename(p)
            if name.lower() in used_font_names:
                name = hashlib.sha1(p.encode("utf-8")).hexdigest()[:8] + "_" + name
            used_font_names.add(name.lower())
            arcname = f"{FONTS_DIR}/{name}"
            size, sha = writer.add_file(p, arcname)
            record(arcname, (size, sha))
            entry.update(packed_path=arcname, size=size, sha256=sha)
        fonts.append(entry)

    return {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "tool_version": __version__,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "source": {"os": platform.system(), "draft_dir": scan.draft_dir},
        "draft": {
            "name": scan.draft_name,
            "id": scan.draft_id,
            "capcut_version": scan.capcut_version,
            "draft_version": scan.draft_version,
            "root": root,
        },
        "media": media,
        "fonts": fonts,
        "effect_ids": scan.effect_ids,
        "missing": scan.missing,
        "files": files,
    }


def _remove(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)
