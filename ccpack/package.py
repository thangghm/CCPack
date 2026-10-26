"""Read a package written by `ccpack pack`, whether it is a .ccpack zip or a plain folder."""

import json
import os
import time
import zipfile

from ccpack.pack import FORMAT, FORMAT_VERSION, MANIFEST


class PackageError(Exception):
    pass


class Package:
    def __init__(self, path: str):
        self.path = path
        self.is_folder = os.path.isdir(path)
        self._zip = None
        if not self.is_folder:
            if not zipfile.is_zipfile(path):
                raise PackageError(f"Not a valid .ccpack file: {path}")
            self._zip = zipfile.ZipFile(path)
        try:
            with self.open_member(MANIFEST) as f:
                self.manifest = json.load(f)
        except (KeyError, FileNotFoundError, ValueError) as e:
            self.close()
            raise PackageError(f"Cannot read {MANIFEST} in {path}: {e}") from e
        if self.manifest.get("format") != FORMAT or self.manifest.get("format_version", 0) > FORMAT_VERSION:
            self.close()
            raise PackageError(f"Not a ccpack package, or made by a newer ccpack: {path}")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        if self._zip:
            self._zip.close()
            self._zip = None

    @property
    def root(self) -> str:
        return self.manifest["draft"]["root"]

    def names(self) -> set[str]:
        """Every file in the package, as forward-slash relative paths."""
        if self._zip:
            return {n for n in self._zip.namelist() if not n.endswith("/")}
        out = set()
        for dirpath, _, files in os.walk(self.path):
            for name in files:
                out.add(os.path.relpath(os.path.join(dirpath, name), self.path).replace(os.sep, "/"))
        return out

    def open_member(self, name: str):
        if self._zip:
            return self._zip.open(name)
        return open(os.path.join(self.path, *name.split("/")), "rb")

    def member_mtime(self, name: str) -> float:
        if self._zip:
            return time.mktime(self._zip.getinfo(name).date_time + (0, 0, -1))
        return os.path.getmtime(os.path.join(self.path, *name.split("/")))
