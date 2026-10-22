"""Command line: ccpack scan / pack / verify / unpack."""

import argparse
import json
import os
import sys

from ccpack import __version__, capcut, interactive
from ccpack.pack import PackError, default_output, pack_draft
from ccpack.package import Package, PackageError
from ccpack.scan import format_report, human_size, scan_draft, to_dict
from ccpack.unpack import unpack_package
from ccpack.verify import verify_package


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="ccpack", description="Đóng gói project CapCut kèm toàn bộ media.")
    ap.add_argument("--version", action="version", version=f"ccpack {__version__}")
    ap.add_argument("--drafts-dir", default=capcut.default_drafts_dir(),
                    help="thư mục chứa project CapCut (mặc định: %(default)s)")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("scan", help="liệt kê media, font, hiệu ứng mà project đang dùng")
    p.add_argument("draft", help="tên project trong thư mục drafts, hoặc đường dẫn tới thư mục project")
    p.add_argument("--json", action="store_true", help="in kết quả dạng JSON")

    p = sub.add_parser("pack", help="đóng gói project và media thành một file .ccpack")
    p.add_argument("draft", help="tên project trong thư mục drafts, hoặc đường dẫn tới thư mục project")
    p.add_argument("-o", "--output", help="file/thư mục đầu ra (mặc định: <tên project>.ccpack)")
    p.add_argument("--folder", action="store_true", help="xuất ra thư mục thường thay vì file .ccpack")
    p.add_argument("--fonts", action="store_true", help="đóng gói kèm font cài trên máy")
    p.add_argument("--allow-missing", action="store_true", help="vẫn đóng gói khi thiếu media")
    p.add_argument("--force", action="store_true", help="ghi đè đầu ra có sẵn / bỏ qua kiểm tra project đang mở")

    p = sub.add_parser("verify", help="kiểm tra gói còn nguyên vẹn (so hash với manifest)")
    p.add_argument("package", help="file .ccpack hoặc thư mục tạo bởi pack --folder")

    p = sub.add_parser("unpack", help="cài gói vào CapCut trên máy này")
    p.add_argument("package", help="file .ccpack hoặc thư mục tạo bởi pack --folder")
    p.add_argument("--name", help="tên project trong CapCut (mặc định: tên gốc, thêm (1), (2)… nếu trùng)")
    p.add_argument("--no-verify", action="store_true", help="bỏ qua bước kiểm tra hash trước khi giải nén")
    return ap


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):  # Windows consoles default to a non-UTF-8 code page
            stream.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    commands = {"scan": _scan, "pack": _pack, "verify": _verify, "unpack": _unpack}
    if not argv:
        return interactive.run_menu(capcut.default_drafts_dir())
    if len(argv) == 1 and argv[0] not in commands and not argv[0].startswith("-") and os.path.exists(argv[0]):
        return interactive.run_dropped(argv[0], capcut.default_drafts_dir())
    args = _build_parser().parse_args(argv)
    try:
        return commands[args.command](args)
    except (capcut.DraftNotFound, PackError, PackageError) as e:
        print(f"Lỗi: {e}", file=sys.stderr)
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
    total = sum(f["size"] for f in manifest["files"])
    print(f"\nXong: {output} ({human_size(total)}, {len(manifest['media'])} media, "
          f"{len(manifest['files'])} file)")
    unpacked_fonts = [f["original_path"] for f in manifest["fonts"] if not f["packed_path"]]
    if unpacked_fonts:
        print(f"Lưu ý: {len(unpacked_fonts)} font chưa đóng gói, người nhận cần tự cài (hoặc dùng --fonts).")
    if manifest["missing"]:
        print(f"Lưu ý: thiếu {len(manifest['missing'])} file media, xem 'missing' trong manifest.json.")
    print(f"Chạy `ccpack verify \"{output}\"` trước khi xoá media gốc.")
    return 0


def _verify(args) -> int:
    with Package(args.package) as pkg:
        result = verify_package(pkg, log=print)
        media = pkg.manifest["media"]
    for label, paths in (("✗ Sai hash/hỏng", result.corrupt), ("✗ Bị thiếu", result.missing),
                         ("⚠ Không có trong manifest", result.unexpected)):
        if paths:
            print(f"{label}: {len(paths)}")
            print("\n".join(f"  {p}" for p in paths))
    if not result.ok:
        print("Gói KHÔNG nguyên vẹn. Đừng xoá media gốc.")
        return 1
    print(f"OK: {result.checked} file ({human_size(result.total_size)}) khớp hash.")
    print(f"Gói chứa bản sao đầy đủ của {len(media)} file media gốc.")
    return 0


def _unpack(args) -> int:
    with Package(args.package) as pkg:
        result = unpack_package(pkg, args.drafts_dir, name=args.name, verify=not args.no_verify)
    print(f"\nXong: project '{result.name}' đã ở {result.draft_dir}")
    if result.fonts:
        print("Cài các font sau (chuột phải → Install) để chữ hiện đúng:")
        print("\n".join(f"  {p}" for p in result.fonts))
    if capcut.capcut_running():
        print("CapCut đang chạy: tắt hẳn CapCut rồi mở lại thì project mới hiện ra.")
    else:
        print("Mở CapCut là thấy project.")
    return 0
