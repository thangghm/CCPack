"""Find every path a draft refers to and rewrite user media to live inside the draft."""

import hashlib
import json
import os
from dataclasses import dataclass, field

from ccpack.capcut import PACKED_MEDIA_DIR, PLACEHOLDER
from ccpack.paths import is_abs_path, is_under, norm, path_key

MEDIA = "media"        # user footage/images/audio outside the draft: packed
INTERNAL = "internal"  # file inside the draft folder: rewritten to the placeholder
CAPCUT = "capcut"      # CapCut's own cache (effects, downloaded fonts): CapCut re-downloads it
FONT = "font"          # font installed on this machine
MISSING = "missing"    # outside the draft and does not exist
OTHER = "other"        # existing folder or anything else we leave alone

FONT_EXTS = (".ttf", ".otf", ".ttc")
# Folder bookkeeping in draft_meta_info.json; unpack sets these for the target machine.
KEEP_KEYS = {"draft_fold_path", "draft_root_path"}
# The media bin in draft_meta_info.json uses CapCut's "./relative" form, not the placeholder.
# TODO: CapCut rebuilds the media bin from its own DB on the source machine; check how it
# behaves on a machine that has never seen these media.
BIN_PATH_KEY = "file_Path"


@dataclass
class PathRef:
    path: str
    kind: str
    files: set = field(default_factory=set)
    packed_name: str | None = None


class DraftRewriter:
    def __init__(self, draft_dir: str, capcut_data_dir: str):
        self.draft_dir = norm(os.path.abspath(draft_dir)).rstrip("/")
        self.capcut_data_dir = capcut_data_dir
        self.refs: dict[str, PathRef] = {}
        # A draft packed before already has _packed_media; never reuse those names.
        existing = os.path.join(draft_dir, PACKED_MEDIA_DIR)
        self._used_names = {n.lower() for n in os.listdir(existing)} if os.path.isdir(existing) else set()
        self._current_file = ""

    def rewrite_file(self, rel: str, data):
        """Return the rewritten JSON document for draft file `rel`."""
        self._current_file = rel
        return self._walk(data, "")

    def refs_of(self, kind: str) -> list[PathRef]:
        return sorted((r for r in self.refs.values() if r.kind == kind), key=lambda r: path_key(r.path))

    def _classify(self, p: str) -> str:
        if is_under(p, self.draft_dir):
            return INTERNAL
        if is_under(self.draft_dir, p):
            return OTHER  # an ancestor folder, e.g. draft_root_path
        if is_under(p, self.capcut_data_dir) or "/capcut/user data/" in p.lower():
            return CAPCUT
        if p.lower().endswith(FONT_EXTS):
            return FONT
        if os.path.isfile(p):
            return MEDIA
        return OTHER if os.path.exists(p) else MISSING

    def _ref(self, p: str) -> PathRef:
        key = path_key(p)
        ref = self.refs.get(key)
        if ref is None:
            ref = self.refs[key] = PathRef(p, self._classify(p))
            if ref.kind == MEDIA:
                ref.packed_name = self._unique_name(p)
        ref.files.add(self._current_file)
        return ref

    def _unique_name(self, p: str) -> str:
        name = os.path.basename(p)
        if name.lower() in self._used_names:
            name = hashlib.sha1(path_key(p).encode("utf-8")).hexdigest()[:8] + "_" + name
        self._used_names.add(name.lower())
        return name

    def _rewrite_path(self, s: str, key: str) -> str:
        p = norm(s)
        ref = self._ref(p)
        if key in KEEP_KEYS:
            return s
        if ref.kind == INTERNAL:
            return PLACEHOLDER + p[len(self.draft_dir):]
        if ref.kind == MEDIA:
            if key == BIN_PATH_KEY:
                return f"./{PACKED_MEDIA_DIR}/{ref.packed_name}"
            return f"{PLACEHOLDER}/{PACKED_MEDIA_DIR}/{ref.packed_name}"
        return s

    def _walk(self, o, key: str):
        if isinstance(o, dict):
            return {k: self._walk(v, k) for k, v in o.items()}
        if isinstance(o, list):
            return [self._walk(v, key) for v in o]
        if not isinstance(o, str):
            return o
        if o[:1] in "{[":
            # Some fields (text styles, extra_info) hold JSON documents inside a string.
            try:
                inner = json.loads(o)
            except ValueError:
                pass
            else:
                new = self._walk(inner, key)
                return o if new == inner else json.dumps(new, ensure_ascii=False, separators=(",", ":"))
        if is_abs_path(o):
            return self._rewrite_path(o, key)
        return o
