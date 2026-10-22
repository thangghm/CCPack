"""What we know about CapCut desktop drafts (verified on CapCut 9.6 for Windows)."""

import json
import os
import subprocess

from ccpack.paths import IS_WINDOWS

# Same token in every draft; CapCut resolves it to the draft's own folder.
PLACEHOLDER = "##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##"
PACKED_MEDIA_DIR = "_packed_media"
META_FILE = "draft_meta_info.json"
CONTENT_FILE = "draft_content.json"
SETTINGS_FILE = "draft_settings"
LOCK_FILE = ".locked"  # present while the draft is open in CapCut
JSON_SUFFIXES = (".json", ".tmp", ".bak")


def default_capcut_data_dir() -> str:
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
        return os.path.join(base, "CapCut", "User Data")
    # macOS location not verified yet.
    return os.path.expanduser("~/Movies/CapCut/User Data")


def default_drafts_dir() -> str:
    return os.path.join(default_capcut_data_dir(), "Projects", "com.lveditor.draft")


class DraftNotFound(Exception):
    pass


def resolve_draft(name_or_path: str, drafts_dir: str) -> str:
    """Accept either a path to a draft folder or a draft name inside drafts_dir."""
    for candidate in (name_or_path, os.path.join(drafts_dir, name_or_path)):
        if os.path.isfile(os.path.join(candidate, META_FILE)):
            return os.path.abspath(candidate)
    raise DraftNotFound(f"Không tìm thấy project CapCut '{name_or_path}' (đã tìm trong {drafts_dir}).")


def list_drafts(drafts_dir: str) -> list[dict]:
    """Drafts in CapCut's folder, newest first (the order CapCut's Home shows)."""
    drafts = []
    if not os.path.isdir(drafts_dir):
        return drafts
    for name in os.listdir(drafts_dir):
        path = os.path.join(drafts_dir, name)
        if name.startswith(".") or not os.path.isfile(os.path.join(path, META_FILE)):
            continue
        try:
            meta = load_json(os.path.join(path, META_FILE))
        except (ValueError, OSError):
            continue
        drafts.append({"name": name, "path": path, "modified": meta.get("tm_draft_modified", 0),
                       "media_size": meta.get("draft_timeline_materials_size_", 0)})
    return sorted(drafts, key=lambda d: d["modified"], reverse=True)


def is_open_in_capcut(draft_dir: str) -> bool:
    return os.path.exists(os.path.join(draft_dir, LOCK_FILE))


def capcut_running() -> bool:
    """CapCut only picks up new drafts at startup, so callers warn when it is running."""
    try:
        if IS_WINDOWS:
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CapCut.exe", "/NH"],
                                 capture_output=True, text=True).stdout
            return "capcut.exe" in out.lower()
        return subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0
    except OSError:
        return False


def iter_draft_files(draft_dir: str):
    """Yield (absolute path, relative path with forward slashes) for every file in the draft."""
    for dirpath, dirnames, filenames in os.walk(draft_dir):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            yield full, os.path.relpath(full, draft_dir).replace(os.sep, "/")


def is_json_candidate(rel: str) -> bool:
    return rel.endswith(JSON_SUFFIXES)


def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump_json_bytes(data) -> bytes:
    """Compact UTF-8 JSON, matching how CapCut writes its draft files."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
