"""Path helpers that work on paths written by either Windows or macOS CapCut."""

import os
import sys

IS_WINDOWS = sys.platform == "win32"

# Windows: OFFLINE | RECALL_ON_OPEN | RECALL_ON_DATA_ACCESS — cloud placeholders such as
# Dropbox Smart Sync / OneDrive files that are not stored locally.
_CLOUD_ONLY_ATTRS = 0x1000 | 0x40000 | 0x400000


def norm(p: str) -> str:
    """Use forward slashes everywhere; CapCut mixes both separators in one file."""
    return p.replace("\\", "/")


def path_key(p: str) -> str:
    """Comparison key: normalized, no trailing slash, case-insensitive on Windows."""
    k = norm(p).rstrip("/")
    return k.lower() if IS_WINDOWS else k


def is_abs_path(s: str) -> bool:
    if len(s) > 2 and s[0].isalpha() and s[1] == ":" and s[2] in "/\\":
        return True  # C:/... or C:\...
    if s.startswith(("//", "\\\\")):
        return True  # UNC share, e.g. \\nas\footage
    return not IS_WINDOWS and s.startswith("/")


def is_under(path: str, folder: str) -> bool:
    p, f = path_key(path), path_key(folder)
    return p == f or p.startswith(f + "/")


def is_cloud_only(path: str) -> bool:
    try:
        attrs = getattr(os.stat(path), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attrs & _CLOUD_ONLY_ATTRS)
