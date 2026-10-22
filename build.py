"""Build a single-file ccpack executable for the OS this runs on.

    python -m venv .venv
    .venv/Scripts/python -m pip install pyinstaller      (macOS: .venv/bin/python)
    .venv/Scripts/python build.py

Output: dist/ccpack.exe on Windows, dist/ccpack on macOS. PyInstaller cannot cross-compile,
so the macOS binary must be built on a Mac.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--console", "--clean", "--noconfirm",
        "--name", "ccpack",
        "--paths", ROOT,
        "--distpath", os.path.join(ROOT, "dist"),
        "--workpath", os.path.join(ROOT, "build"),
        "--specpath", os.path.join(ROOT, "build"),
        os.path.join(ROOT, "ccpack", "__main__.py"),
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
