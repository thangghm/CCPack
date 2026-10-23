"""Build a single-file ccpack executable for the OS this runs on.

Windows:
    python -m venv .venv
    .venv/Scripts/python -m pip install pyinstaller
    .venv/Scripts/python build.py

macOS (the system /usr/bin/python3 is 3.9, too old; use Homebrew's):
    /opt/homebrew/bin/python3 -m venv .venv
    .venv/bin/python -m pip install pyinstaller
    .venv/bin/python build.py

Output: dist/ccpack.exe on Windows, dist/ccpack on macOS. PyInstaller cannot cross-compile,
so the macOS binary must be built on a Mac. Requires Python 3.10+.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    if sys.version_info < (3, 10):
        print(f"ccpack needs Python 3.10+, but this is {sys.version.split()[0]} ({sys.executable}).")
        return 1
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
