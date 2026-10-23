"""Command line: ccpack scan / pack / verify / unpack."""

import argparse
import json
import os
import sys

from ccpack import __version__, capcut, i18n, interactive
from ccpack.i18n import files, tr
from ccpack.pack import PackError, default_output, pack_draft
from ccpack.package import Package, PackageError
from ccpack.scan import format_report, human_size, scan_draft, to_dict
from ccpack.unpack import unpack_package
from ccpack.verify import verify_package


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="ccpack", description=tr(
        "Pack CapCut projects together with all their media.",
        "Đóng gói project CapCut kèm toàn bộ media."))
    ap.add_argument("--version", action="version", version=f"ccpack {__version__}")
    ap.add_argument("--drafts-dir", default=capcut.drafts_dir(), help=tr(
        "CapCut projects folder (default: %(default)s)",
        "thư mục chứa project CapCut (mặc định: %(default)s)"))
    ap.add_argument("--lang", choices=i18n.LANGS, help=tr(
        "interface language (default: the system language)",
        "ngôn ngữ giao diện (mặc định: theo ngôn ngữ của máy)"))
    sub = ap.add_subparsers(dest="command", required=True)
    draft_help = tr("project name in the projects folder, or the path to a project folder",
                    "tên project trong thư mục drafts, hoặc đường dẫn tới thư mục project")
    package_help = tr(".ccpack file, or a folder created by pack --folder",
                      "file .ccpack hoặc thư mục tạo bởi pack --folder")

    p = sub.add_parser("scan", help=tr("list the media, fonts and effects a project uses",
                                       "liệt kê media, font, hiệu ứng mà project đang dùng"))
    p.add_argument("draft", help=draft_help)
    p.add_argument("--json", action="store_true", help=tr("print the result as JSON", "in kết quả dạng JSON"))

    p = sub.add_parser("pack", help=tr("pack a project and its media into a .ccpack file",
                                       "đóng gói project và media thành một file .ccpack"))
    p.add_argument("draft", help=draft_help)
    p.add_argument("-o", "--output", help=tr("output file or folder (default: <project name>.ccpack)",
                                             "file/thư mục đầu ra (mặc định: <tên project>.ccpack)"))
    p.add_argument("--folder", action="store_true", help=tr("write a plain folder instead of a .ccpack file",
                                                            "xuất ra thư mục thường thay vì file .ccpack"))
    p.add_argument("--fonts", action="store_true", help=tr("include fonts installed on this computer",
                                                           "đóng gói kèm font cài trên máy"))
    p.add_argument("--allow-missing", action="store_true", help=tr("pack even if some media is missing",
                                                                   "vẫn đóng gói khi thiếu media"))
    p.add_argument("--force", action="store_true", help=tr(
        "overwrite an existing output, and skip the open-project check",
        "ghi đè đầu ra có sẵn / bỏ qua kiểm tra project đang mở"))

    p = sub.add_parser("verify", help=tr("check that a package is intact (hashes against the manifest)",
                                         "kiểm tra gói còn nguyên vẹn (so hash với manifest)"))
    p.add_argument("package", help=package_help)

    p = sub.add_parser("unpack", help=tr("import a package into CapCut on this computer",
                                         "cài gói vào CapCut trên máy này"))
    p.add_argument("package", help=package_help)
    p.add_argument("--name", help=tr(
        "project name in CapCut (default: the original name, plus (1), (2)… if taken)",
        "tên project trong CapCut (mặc định: tên gốc, thêm (1), (2)… nếu trùng)"))
    p.add_argument("--no-verify", action="store_true", help=tr("skip the hash check before extracting",
                                                               "bỏ qua bước kiểm tra hash trước khi giải nén"))
    return ap


def _take_lang(argv: list[str]) -> list[str]:
    """Apply --lang before anything prints, so it also works for the menu (`ccpack --lang en`)."""
    rest, i = [], 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--lang" and i + 1 < len(argv) and argv[i + 1] in i18n.LANGS:
            i18n.set_lang(argv[i + 1])
            i += 2
            continue
        if arg.startswith("--lang=") and arg[7:] in i18n.LANGS:
            i18n.set_lang(arg[7:])
        else:
            rest.append(arg)
        i += 1
    return rest


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):  # Windows consoles default to a non-UTF-8 code page
            stream.reconfigure(encoding="utf-8")
    argv = _take_lang(sys.argv[1:] if argv is None else argv)
    commands = {"scan": _scan, "pack": _pack, "verify": _verify, "unpack": _unpack}
    if not argv:
        return interactive.run_menu()
    if len(argv) == 1 and argv[0] not in commands and not argv[0].startswith("-") and os.path.exists(argv[0]):
        return interactive.run_dropped(argv[0])
    args = _build_parser().parse_args(argv)
    try:
        return commands[args.command](args)
    except (capcut.DraftNotFound, PackError, PackageError) as e:
        print(tr(f"Error: {e}", f"Lỗi: {e}"), file=sys.stderr)
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
    print(tr(f"\nDone: {output} ({total}; media: {n_media}, {files(n_files)} in total)",
             f"\nXong: {output} ({total}, {n_media} media, {n_files} file)"))
    unpacked_fonts = [f["original_path"] for f in manifest["fonts"] if not f["packed_path"]]
    if unpacked_fonts:
        n = len(unpacked_fonts)
        print(tr(f"Note: {n} font(s) not packed. The recipient has to install them (or pack with --fonts).",
                 f"Lưu ý: {n} font chưa đóng gói, người nhận cần tự cài (hoặc dùng --fonts)."))
    if manifest["missing"]:
        n = len(manifest["missing"])
        print(tr(f"Note: {files(n)} of media missing; see 'missing' in manifest.json.",
                 f"Lưu ý: thiếu {n} file media, xem 'missing' trong manifest.json."))
    print(tr(f"Run `ccpack verify \"{output}\"` before deleting the original media.",
             f"Chạy `ccpack verify \"{output}\"` trước khi xoá media gốc."))
    return 0


def _verify(args) -> int:
    with Package(args.package) as pkg:
        result = verify_package(pkg, log=print)
        media = pkg.manifest["media"]
    for label, paths in ((tr("✗ Wrong hash or corrupt", "✗ Sai hash/hỏng"), result.corrupt),
                         (tr("✗ Missing", "✗ Bị thiếu"), result.missing),
                         (tr("⚠ Not in the manifest", "⚠ Không có trong manifest"), result.unexpected)):
        if paths:
            print(f"{label}: {len(paths)}")
            print("\n".join(f"  {p}" for p in paths))
    if not result.ok:
        print(tr("The package is NOT intact. Keep the original media.",
                 "Gói KHÔNG nguyên vẹn. Đừng xoá media gốc."))
        return 1
    print(tr(f"OK: {files(result.checked)} ({human_size(result.total_size)}) match their hashes.",
             f"OK: {result.checked} file ({human_size(result.total_size)}) khớp hash."))
    print(tr(f"The package holds a full copy of the original media ({files(len(media))}).",
             f"Gói chứa bản sao đầy đủ của {len(media)} file media gốc."))
    return 0


def _unpack(args) -> int:
    with Package(args.package) as pkg:
        result = unpack_package(pkg, args.drafts_dir, name=args.name, verify=not args.no_verify)
    print(tr(f"\nDone: project '{result.name}' is in {result.draft_dir}",
             f"\nXong: project '{result.name}' đã ở {result.draft_dir}"))
    if result.fonts:
        interactive.print_fonts(result.fonts)
    if capcut.capcut_running():
        print(tr("CapCut is running: quit CapCut completely and reopen it to see the new project.",
                 "CapCut đang chạy: tắt hẳn CapCut rồi mở lại thì project mới hiện ra."))
    else:
        print(tr("Open CapCut to see the project.", "Mở CapCut là thấy project."))
    return 0
