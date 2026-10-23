"""English or Vietnamese messages: --lang or CCPACK_LANG, else the system language."""

import os
import re
import subprocess
import sys

LANGS = ("en", "vi")
_lang = None


def _system_language() -> str:
    """The OS display language. Double-clicked apps often get no LANG, or just C.UTF-8."""
    try:
        if sys.platform == "win32":
            import ctypes
            return "vi" if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x2A else ""
        if sys.platform == "darwin":
            out = subprocess.run(["defaults", "read", "-g", "AppleLanguages"],
                                 capture_output=True, text=True, timeout=2).stdout
            first = re.search(r'"?([A-Za-z-]+)"?', out.strip("( \n"))
            return first.group(1) if first else ""
    except (OSError, subprocess.SubprocessError, AttributeError):
        pass
    return ""


def detect() -> str:
    for var in ("CCPACK_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        if value and value.split(".")[0] not in ("C", "POSIX"):
            return "vi" if value.lower().startswith("vi") else "en"
    return "vi" if _system_language().lower().startswith("vi") else "en"


def set_lang(lang: str):
    global _lang
    _lang = lang


def lang() -> str:
    global _lang
    if _lang is None:
        _lang = detect()
    return _lang


def tr(en: str, vi: str) -> str:
    return vi if lang() == "vi" else en


def files(n: int) -> str:
    """'1 file' / '3 files' in English; Vietnamese has no plural."""
    return f"{n} file" if n == 1 or lang() == "vi" else f"{n} files"
