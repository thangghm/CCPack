"""What we know about CapCut desktop drafts (verified on CapCut 9.6 for Windows and macOS)."""

import json
import os
import subprocess

from ccpack.paths import IS_WINDOWS

# Same token in every draft; CapCut resolves it to the draft's own folder.
PLACEHOLDER = "##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##"
PACKED_MEDIA_DIR = "_packed_media"
DRAFTS_FOLDER = "com.lveditor.draft"
ROOT_META_FILE = "root_meta_info.json"  # CapCut keeps its project list here, even when empty
META_FILE = "draft_meta_info.json"
CONTENT_FILE = "draft_content.json"
SETTINGS_FILE = "draft_settings"
LOCK_FILE = ".locked"  # present while the draft is open in CapCut
JSON_SUFFIXES = (".json", ".tmp", ".bak")


def default_capcut_data_dir() -> str:
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
        return os.path.join(base, "CapCut", "User Data")
    return os.path.expanduser("~/Movies/CapCut/User Data")


def default_drafts_dir() -> str:
    return os.path.join(default_capcut_data_dir(), "Projects", DRAFTS_FOLDER)


def _config_path() -> str:
    if IS_WINDOWS:
        base = os.environ.get("APPDATA") or os.path.expanduser("~/AppData/Roaming")
    else:
        base = os.path.expanduser("~/Library/Application Support")
    return os.path.join(base, "ccpack", "config.json")


def capcut_drafts_setting() -> str | None:
    """The 'Save to' folder from CapCut's Settings → Draft. CapCut keeps it in an INI file
    and puts drafts straight into that folder."""
    path = os.path.join(default_capcut_data_dir(), "Config", "globalSetting")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                key, _, value = line.partition("=")
                if key.strip() == "currentCustomDraftPath":
                    return value.strip().strip('"').replace("\\\\", "\\") or None
    except OSError:
        pass
    return None


def drafts_dir() -> str:
    """Where CapCut saves drafts: its own setting, else the folder the user picked in
    ccpack, else CapCut's default."""
    setting = capcut_drafts_setting()
    if setting:
        return setting
    try:
        saved = load_json(_config_path()).get("drafts_dir")
    except (ValueError, OSError, AttributeError):
        saved = None
    return saved if saved and os.path.isdir(saved) else default_drafts_dir()


def save_drafts_dir(path: str):
    config = _config_path()
    os.makedirs(os.path.dirname(config), exist_ok=True)
    with open(config, "w", encoding="utf-8") as f:
        json.dump({"drafts_dir": path}, f, ensure_ascii=False, indent=2)


def find_drafts_dir(path: str) -> str | None:
    """Accept CapCut's drafts folder, the folder above it, or one project inside it."""
    path = os.path.abspath(os.path.expanduser(path))
    for candidate in (path, os.path.join(path, DRAFTS_FOLDER), os.path.dirname(path)):
        if os.path.isfile(os.path.join(candidate, ROOT_META_FILE)) or list_drafts(candidate):
            return candidate
    return None


class DraftNotFound(Exception):
    pass


def resolve_draft(name_or_path: str, drafts_dir: str) -> str:
    """Accept either a path to a draft folder or a draft name inside drafts_dir."""
    for candidate in (name_or_path, os.path.join(drafts_dir, name_or_path)):
        if os.path.isfile(os.path.join(candidate, META_FILE)):
            return os.path.abspath(candidate)
    raise DraftNotFound(f"Project '{name_or_path}' not found in {drafts_dir}.")


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
    """CapCut 9.6 on macOS lists a new draft as soon as its Home screen is shown; other
    versions may only pick it up at startup, so callers tell the user what to do."""
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
