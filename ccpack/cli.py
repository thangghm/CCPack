"""Command line: ccpack scan / pack / verify / unpack."""

import argparse
import json
import os
import sys

from ccpack import __version__, capcut, interactive
from ccpack.pack import PackError, default_output, pack_draft
from ccpack.package import Package, PackageError
from ccpack.scan import files, format_report, human_size, scan_draft, to_dict
from ccpack.unpack import unpack_package
from ccpack.verify import verify_package


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="ccpack", description="Package CapCut projects with all linked media.")
    ap.add_argument("--version", action="version", version=f"ccpack {__version__}")
    ap.add_argument("--drafts-dir", default=capcut.drafts_dir(), help="CapCut projects folder (default: %(default)s)")
    sub = ap.add_subparsers(dest="command", required=True)
    draft_help = "project name, or path to a project folder"
    package_help = ".ccpack file, or folder from pack --folder"

    p = sub.add_parser("scan", help="list media, fonts and effects used by a project")
    p.add_argument("draft", help=draft_help)
    p.add_argument("--json", action="store_true", help="output JSON")

    p = sub.add_parser("pack", help="package a project and its media into a .ccpack file")
    p.add_argument("draft", help=draft_help)
    p.add_argument("-o", "--output", help="output file or folder (default: <project>.ccpack)")
    p.add_argument("--folder", action="store_true", help="write a folder instead of a .ccpack file")
    p.add_argument("--fonts", action="store_true", help="include installed fonts")
    p.add_argument("--allow-missing", action="store_true", help="pack even if media is missing")
    p.add_argument("--force", action="store_true", help="overwrite existing output; skip the open-project check")

    p = sub.add_parser("verify", help="verify package checksums against the manifest")
    p.add_argument("package", help=package_help)

    p = sub.add_parser("unpack", help="import a package into CapCut")
    p.add_argument("package", help=package_help)
    p.add_argument("--name", help="project name in CapCut (default: original; adds (1), (2)… if taken)")
    p.add_argument("--no-verify", action="store_true", help="skip checksum verification before extracting")
    return ap


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):  # Windows consoles default to a non-UTF-8 code page
            stream.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    commands = {"scan": _scan, "pack": _pack, "verify": _verify, "unpack": _unpack}
    if not argv:
        return interactive.run_menu()
    if len(argv) == 1 and argv[0] not in commands and not argv[0].startswith("-") and os.path.exists(argv[0]):
        return interactive.run_dropped(argv[0])
    args = _build_parser().parse_args(argv)
    try:
        return commands[args.command](args)
    except (capcut.DraftNotFound, PackError, PackageError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _scan(args) -> int:
    result = scan_draft(capcut.resolve_draft(args.draft, args.drafts_dir))
    if args.json:
        print(json.dumps(to_dict(result), ensure_ascii=False, indent=2))
    else:
        print(format_report(result))
    return 0


def _pack(args) -> int:
    result = scan_draft(capcut.resolve_draft(args.draft, args.drafts_dir))
    output = args.output or default_output(result, args.folder)
    manifest = pack_draft(result, output, as_folder=args.folder, include_fonts=args.fonts,
                          allow_missing=args.allow_missing, force=args.force)
    total = human_size(sum(f["size"] for f in manifest["files"]))
    n_media, n_files = len(manifest["media"]), len(manifest["files"])
    print(f"\nDone: {output} ({total}, {n_media} media, {files(n_files)})")
    unpacked_fonts = [f["original_path"] for f in manifest["fonts"] if not f["packed_path"]]
    if unpacked_fonts:
        n = len(unpacked_fonts)
        print(f"Warning: {n} font(s) not packed. Install them on the target, or repack with --fonts.")
    if manifest["missing"]:
        n = len(manifest["missing"])
        print(f"Warning: {n} media missing. See 'missing' in manifest.json.")
    print(f"Verify before deleting source media: ccpack verify \"{output}\"")
    return 0


def _verify(args) -> int:
    with Package(args.package) as pkg:
        result = verify_package(pkg, log=print)
        media = pkg.manifest["media"]
    for label, paths in (("✗ Checksum mismatch", result.corrupt),
                         ("✗ Missing", result.missing),
                         ("⚠ Not in manifest", result.unexpected)):
        if paths:
            print(f"{label}: {len(paths)}")
            print("\n".join(f"  {p}" for p in paths))
    if not result.ok:
        print("Verify failed. Keep source media.")
        return 1
    print(f"OK: {files(result.checked)} ({human_size(result.total_size)}), checksums match.")
    print(f"Package contains all source media ({files(len(media))}).")
    return 0


def _unpack(args) -> int:
    with Package(args.package) as pkg:
        result = unpack_package(pkg, args.drafts_dir, name=args.name, verify=not args.no_verify)
    print(f"\nDone: '{result.name}' imported to {result.draft_dir}")
    if result.fonts:
        interactive.print_fonts(result.fonts)
    interactive.print_capcut_hint()
    return 0
