# CCPack

English | [Tiếng Việt](README.vi.md)

Command-line tool that packages a CapCut desktop project with all linked media into a single `.ccpack` file, and imports it into CapCut on another machine.

- Collects external media into the project and rewrites paths.
- Stores files uncompressed (ZIP64, files over 4 GB supported) with a SHA-256 checksum per file.
- Optionally includes installed fonts.
- Never modifies the source project.

## Download

Get the binary for your OS from [Releases](../../releases). No Python required.

| OS | File |
|---|---|
| Windows 10/11 | `ccpack-windows-x64.exe` |
| macOS Apple Silicon | `ccpack-macos-arm64.zip` |
| macOS Intel | `ccpack-macos-x64.zip` |

The binaries are unsigned.

- **Windows:** if SmartScreen blocks the file, select **More info → Run anyway**.
- **macOS:** unzip, then run `xattr -d com.apple.quarantine ccpack`, or right-click → **Open**.

## Usage

### Menu

Run `ccpack` with no arguments, or double-click it:

```
1. Pack project
2. Import package
3. Verify package
0. Quit
```

| Task | Steps |
|---|---|
| Send a project | Close the project in CapCut (return to Home). Select **1**, then the project. The package is verified after writing. |
| Import a project | Select **2** and drop in the `.ccpack` file (Windows: or drop it onto `ccpack.exe`). Install any bundled fonts listed in the output. |
| Archive a project | Pack, copy the package to its destination, then select **3** on the copy. Delete source media only after `OK`. |

### Commands

```
ccpack scan   <project> [--json]
ccpack pack   <project> [-o OUTPUT] [--folder] [--fonts] [--allow-missing] [--force]
ccpack verify <package>
ccpack unpack <package> [--name NAME] [--no-verify]
```

| Command | Description |
|---|---|
| `scan` | List media, fonts and effects used by a project, and report missing files. |
| `pack` | Write a `.ccpack` file (or a folder with `--folder`). |
| `verify` | Check every file against the manifest checksums. Exit code 1 on failure. |
| `unpack` | Verify and import a package into CapCut. A name in use gets a ` (1)`, ` (2)`… suffix. |

`<project>` is a project name or a path to a project folder. Run `ccpack <command> --help` for all options.

### Projects folder

Resolved in this order:

1. `--drafts-dir PATH` (global option, placed before the command).
2. CapCut **Settings → Draft → Save to**.
3. The folder last entered at the prompt (asked when the folder is missing or empty).
4. CapCut's default location.

## Limitations

- Effects, transitions and stickers from the CapCut library are not packed. CapCut downloads them again when the project opens (sign-in required; Pro assets need a Pro account).
- Fonts are packed only from the menu or with `--fonts`.
- Tested with CapCut 9.6 on Windows and macOS. CapCut's project format is undocumented and may change.

## Build from source

Requires Python 3.10 or later. Build on the OS you are targeting; PyInstaller does not cross-compile.

```bash
git clone https://github.com/thangghm/CCPack.git
cd CCPack
python3 -m venv .venv
.venv/bin/python -m pip install pyinstaller
.venv/bin/python build.py
```

On Windows, use `python` instead of `python3` and `.venv\Scripts\python` instead of `.venv/bin/python`.

Output: `dist/ccpack` (macOS) or `dist/ccpack.exe` (Windows).

## Disclaimer

CCPack is an independent tool, not affiliated with or endorsed by CapCut or ByteDance. It is provided "as is", without warranty. Run `verify` before deleting source media. You are responsible for the licenses of the media, fonts and music you share.
