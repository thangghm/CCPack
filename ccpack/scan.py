"""Read a draft, list everything it depends on and prepare the rewritten JSON files."""

import os
import re
from dataclasses import dataclass, field

from ccpack import capcut
from ccpack.paths import is_cloud_only
from ccpack.rewrite import CAPCUT, FONT, INTERNAL, MEDIA, MISSING, OTHER, DraftRewriter

_EFFECT_ID = re.compile(r"/cache/effect/(\d+)/", re.IGNORECASE)


@dataclass
class MediaFile:
    source: str
    packed_name: str
    size: int
    cloud_only: bool
    used_in: list[str]


@dataclass
class ScanResult:
    draft_dir: str
    draft_name: str
    draft_id: str
    capcut_version: str
    draft_version: int | None
    is_open: bool
    media: list[MediaFile] = field(default_factory=list)
    fonts: list[str] = field(default_factory=list)
    effect_ids: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    internal_count: int = 0
    # relative path -> rewritten JSON document, only for files that changed
    rewritten: dict = field(default_factory=dict)

    @property
    def media_size(self) -> int:
        return sum(m.size for m in self.media)


def scan_draft(draft_dir: str, capcut_data_dir: str | None = None) -> ScanResult:
    capcut_data_dir = capcut_data_dir or capcut.default_capcut_data_dir()
    meta = capcut.load_json(os.path.join(draft_dir, capcut.META_FILE))
    content_path = os.path.join(draft_dir, capcut.CONTENT_FILE)
    content = capcut.load_json(content_path) if os.path.isfile(content_path) else {}

    rw = DraftRewriter(draft_dir, capcut_data_dir)
    rewritten = {}
    for full, rel in capcut.iter_draft_files(draft_dir):
        if not capcut.is_json_candidate(rel):
            continue
        try:
            data = capcut.load_json(full)
        except (ValueError, UnicodeDecodeError):
            continue  # not JSON (e.g. some .tmp files): copied as-is
        new = rw.rewrite_file(rel, data)
        if new != data:
            rewritten[rel] = new

    result = ScanResult(
        draft_dir=os.path.abspath(draft_dir),
        draft_name=os.path.basename(os.path.abspath(draft_dir)),
        draft_id=meta.get("draft_id", ""),
        capcut_version=content.get("new_version", ""),
        draft_version=content.get("version"),
        is_open=capcut.is_open_in_capcut(draft_dir),
        rewritten=rewritten,
    )
    for ref in rw.refs_of(MEDIA):
        result.media.append(MediaFile(ref.path, ref.packed_name, os.path.getsize(ref.path),
                                      is_cloud_only(ref.path), sorted(ref.files)))
    result.fonts = [r.path for r in rw.refs_of(FONT)]
    result.effect_ids = sorted({m.group(1) for r in rw.refs_of(CAPCUT) if (m := _EFFECT_ID.search(r.path + "/"))})
    result.missing = [r.path for r in rw.refs_of(MISSING)]
    result.internal_count = len(rw.refs_of(INTERNAL))
    return result


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} GB"


def format_report(r: ScanResult) -> str:
    lines = [
        f"Project:   {r.draft_name}",
        f"Thư mục:   {r.draft_dir}",
        f"CapCut:    {r.capcut_version or '?'} (draft version {r.draft_version})",
    ]
    if r.is_open:
        lines.append("⚠ Project đang mở trong CapCut — đóng project (về màn hình Home) trước khi pack.")
    lines.append(f"\nMedia sẽ đóng gói: {len(r.media)} file, {human_size(r.media_size)}")
    for m in r.media:
        flag = "  ☁ chỉ có trên cloud, sẽ phải tải về" if m.cloud_only else ""
        lines.append(f"  {human_size(m.size):>10}  {m.source}{flag}")
    if r.missing:
        lines.append(f"\n✗ Không tìm thấy: {len(r.missing)} file")
        lines += [f"  {p}" for p in r.missing]
    if r.fonts:
        lines.append(f"\nFont cài trên máy (người nhận cần cài, hoặc pack với --fonts): {len(r.fonts)}")
        for p in r.fonts:
            lines.append(f"  {p}" + ("" if os.path.isfile(p) else "  (không có trên máy này)"))
    if r.effect_ids:
        lines.append(f"\nHiệu ứng từ thư viện CapCut (CapCut tự tải lại): {len(r.effect_ids)}")
    lines.append(f"File nội bộ project: {r.internal_count} đường dẫn")
    lines.append(f"File JSON sẽ sửa đường dẫn: {len(r.rewritten)}")
    return "\n".join(lines)


def to_dict(r: ScanResult) -> dict:
    return {
        "draft_name": r.draft_name,
        "draft_dir": r.draft_dir,
        "draft_id": r.draft_id,
        "capcut_version": r.capcut_version,
        "draft_version": r.draft_version,
        "is_open": r.is_open,
        "media": [{"source": m.source, "packed_name": m.packed_name, "size": m.size,
                   "cloud_only": m.cloud_only, "used_in": m.used_in} for m in r.media],
        "media_size": r.media_size,
        "fonts": r.fonts,
        "effect_ids": r.effect_ids,
        "missing": r.missing,
        "rewritten_files": sorted(r.rewritten),
    }
