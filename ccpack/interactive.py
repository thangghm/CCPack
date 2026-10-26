"""Numbered menu for people who double-click ccpack instead of typing commands."""

import datetime
import os
import sys

from ccpack import __version__, capcut
from ccpack.pack import PackError, default_output, pack_draft
from ccpack.package import Package, PackageError
from ccpack.scan import files, format_report, human_size, scan_draft
from ccpack.unpack import unpack_package
from ccpack.verify import verify_package


class Cancelled(Exception):
    pass


def ask(prompt: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    try:
        answer = input(f"{prompt}{hint}: ").strip()
    except EOFError:
        raise Cancelled from None
    # Dragging a file into the console window pastes its path in quotes.
    answer = answer.strip('"').strip("'").strip()
    return answer or default


def ask_yes(prompt: str, default=True) -> bool:
    answer = ask(prompt + (" (Y/n)" if default else " (y/N)")).lower()
    return default if not answer else answer in ("y", "yes")


def default_output_dir() -> str:
    """Next to ccpack.exe when frozen (where the user found it), else the current folder."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.getcwd()


def print_fonts(fonts: list[str]):
    print("Install these fonts for correct text rendering:")
    print("\n".join(f"  {p}" for p in fonts))


def print_capcut_hint():
    if capcut.capcut_running():
        print("CapCut is running. Return to Home to see the project. If not listed, restart CapCut.")
    else:
        print("Open CapCut. The project is at the top of the list.")


def choose_drafts_dir(reason: str) -> str:
    """Ask for CapCut's drafts folder and remember it for next time."""
    print(f"\n{reason}")
    print("CapCut → Settings → Draft: copy the Save to path.")
    path = ask("Paste path or drop folder here (Enter to cancel)")
    if not path:
        raise Cancelled
    found = capcut.find_drafts_dir(path)
    if not found:
        raise PackError(f"Not a CapCut projects folder: {path}")
    capcut.save_drafts_dir(found)
    print(f"Projects folder saved: {found}")
    return found


def run_menu() -> int:
    print(f"ccpack {__version__} — CapCut project packager\n")
    actions = {"1": pack_flow, "2": unpack_flow, "3": verify_flow}
    while True:
        print("1. Pack project")
        print("2. Import package")
        print("3. Verify package")
        print("0. Quit")
        try:
            choice = ask("Select")
        except Cancelled:
            return 0
        if choice == "0":
            return 0
        if choice not in actions:
            continue
        try:
            actions[choice](capcut.drafts_dir())
        except Cancelled:
            print("Cancelled.")
        except (capcut.DraftNotFound, PackError, PackageError) as e:
            print(f"Error: {e}")
        print()


def pack_flow(drafts_dir: str):
    drafts = capcut.list_drafts(drafts_dir)
    if not drafts:
        drafts = capcut.list_drafts(choose_drafts_dir(f"No projects in {drafts_dir}."))
    if not drafts:
        raise PackError("No projects in this folder.")
    print()
    for i, d in enumerate(drafts, 1):
        when = datetime.datetime.fromtimestamp(d["modified"] / 1e6).strftime("%Y-%m-%d %H:%M") if d["modified"] else ""
        print(f"{i:3}. {d['name']:<30} {when}  {human_size(d['media_size'])}")
    choice = ask("\nSelect project")
    if not choice.isdigit() or not 1 <= int(choice) <= len(drafts):
        raise Cancelled
    draft = drafts[int(choice) - 1]

    print("\nScanning project…")
    scan = scan_draft(draft["path"])
    print(format_report(scan))
    if scan.is_open:
        raise PackError("Project is open in CapCut. Return to Home and retry.")
    allow_missing = False
    if scan.missing:
        n = len(scan.missing)
        allow_missing = ask_yes(f"\n{files(n)} missing. Pack anyway?", default=False)
        if not allow_missing:
            raise Cancelled

    out_dir = ask("\nOutput folder", default_output_dir())
    output = os.path.join(out_dir, default_output(scan, as_folder=False))
    if os.path.exists(output) and not ask_yes(f"{output} exists. Overwrite?", default=False):
        raise Cancelled
    pack_draft(scan, output, include_fonts=True, allow_missing=allow_missing, force=True)

    print("\nVerifying checksums…")
    with Package(output) as pkg:
        result = verify_package(pkg)
    if not result.ok:
        raise PackError(f"Verify failed: {output}. Keep source media and pack again.")
    print(f"\nDone: {output} ({human_size(result.total_size)}), checksums OK.")
    print("Send this file. Recipient: open ccpack, select 2 (or drop the file onto ccpack).")


def unpack_flow(drafts_dir: str, path: str | None = None):
    path = path or ask("Drop .ccpack file here, then press Enter")
    if not path:
        raise Cancelled
    if not os.path.isdir(drafts_dir):
        drafts_dir = choose_drafts_dir(f"CapCut projects folder not found: {drafts_dir}. Open CapCut once, then retry.")
    with Package(path) as pkg:
        print(f"Package project: {pkg.manifest['draft']['name']}")
        name = ask("Project name in CapCut (Enter = original)")
        result = unpack_package(pkg, drafts_dir, name=name or None)
    print(f"\nDone: '{result.name}' imported into CapCut.")
    if result.fonts:
        print_fonts(result.fonts)
    print_capcut_hint()


def verify_flow(_drafts_dir: str):
    path = ask("Drop .ccpack file here, then press Enter")
    if not path:
        raise Cancelled
    with Package(path) as pkg:
        result = verify_package(pkg, log=print)
    if result.ok:
        print(f"OK: {files(result.checked)} ({human_size(result.total_size)}), checksums match.")
    else:
        print(f"VERIFY FAILED: {files(len(result.corrupt))} mismatched, "
                 f"{files(len(result.missing))} missing. Keep source media.")


def run_dropped(path: str) -> int:
    """A file was dropped onto ccpack.exe: install it."""
    try:
        unpack_flow(capcut.drafts_dir(), path)
        return 0
    except Cancelled:
        print("Cancelled.")
        return 1
    except (PackError, PackageError) as e:
        print(f"Error: {e}")
        return 1
