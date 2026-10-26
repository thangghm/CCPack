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

### Running from a terminal

Commands are typed in Terminal (macOS) or PowerShell (Windows). The shell finds `ccpack` only if it is in a folder on your `PATH`; otherwise you get `command not found`. Either run it by path, or install it once.

Run by path, from the folder that contains the file:

```bash
cd ~/Downloads
./ccpack --help            # Windows: .\ccpack.exe --help
```

Install on macOS, so `ccpack` works from any folder:

```bash
mkdir -p ~/.local/bin
cp ~/Downloads/ccpack ~/.local/bin/
xattr -d com.apple.quarantine ~/.local/bin/ccpack
ccpack --help
```

If `ccpack` is still not found, add `~/.local/bin` to your `PATH`: run `echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc`, then open a new Terminal window. If you get `permission denied`, run `chmod +x ~/.local/bin/ccpack`.

### Commands

```
ccpack [--drafts-dir PATH] <command> [options]
```

`<project>` is the project name shown in CapCut, or a path to a project folder. `<package>` is a `.ccpack` file, or a folder written by `pack --folder`. On Windows, rename the download to `ccpack.exe` to use the commands as written.

**Global options** (before the command)

| Option | Description |
|---|---|
| `--drafts-dir PATH` | CapCut projects folder for this run only. See [Projects folder](#projects-folder). |
| `--version` | Print the version. |
| `-h`, `--help` | Show help. `ccpack <command> --help` shows command options. |

**`scan <project>`** lists media, fonts, library effects and missing files. Read-only.

| Option | Description |
|---|---|
| `--json` | Print the result as JSON. |

**`pack <project>`** writes the project and its media to a package, then prints a summary.

| Option | Description |
|---|---|
| `-o`, `--output PATH` | Output path. Default: `<project>.ccpack` in the current folder (`<project>_ccpack` with `--folder`). |
| `--folder` | Write a plain folder instead of a `.ccpack` file. |
| `--fonts` | Include installed fonts used by the project. |
| `--allow-missing` | Pack even if media is missing. Missing files are listed in `manifest.json`. |
| `--force` | Overwrite an existing output. Also packs a project that is open in CapCut; use only when CapCut is not editing it. |

**`verify <package>`** checks every file against the manifest checksums. No options.

**`unpack <package>`** verifies the package, then imports it into the projects folder.

| Option | Description |
|---|---|
| `--name NAME` | Project name in CapCut. Default: the original name, with ` (1)`, ` (2)`… added if taken. |
| `--no-verify` | Skip checksum verification before extracting. |

Exit codes: `0` success, `1` error or failed verification, `2` invalid arguments.

**Examples**

```bash
ccpack scan "My Video"
ccpack scan "My Video" --json > my-video.json
ccpack pack "My Video" -o ~/Archive/my-video.ccpack --fonts
ccpack pack "My Video" --allow-missing --force
ccpack verify ~/Archive/my-video.ccpack
ccpack unpack my-video.ccpack --name "My Video (review)"
ccpack --drafts-dir "D:\CapCut Drafts" pack "My Video"
```

### Projects folder

ccpack locates the CapCut projects folder automatically, in this order:

1. `--drafts-dir PATH`, if given.
2. CapCut **Settings → Draft → Save to**.
3. The folder last entered in the menu.
4. CapCut's default location:
   - macOS: `~/Movies/CapCut/User Data/Projects/com.lveditor.draft`
   - Windows: `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft`

`ccpack --help` shows the folder in use as the `--drafts-dir` default.

**If the folder is not found**

- **Menu:** ccpack asks for the folder when it is missing or has no projects. In CapCut, open **Settings → Draft**, copy the **Save to** path and paste it, or drag the folder into the window. The projects folder, its parent folder, or any project inside it is accepted. The answer is saved for later runs.
- **Commands:** commands do not prompt. Add `--drafts-dir PATH` (the folder that contains the projects), or pass a project folder path instead of a name. To save the folder, enter it once in the menu.
- **CapCut never opened on this computer:** open CapCut once so it creates its projects folder, then retry.

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
