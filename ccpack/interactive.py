"""Numbered menu for people who double-click ccpack instead of typing commands."""

import datetime
import os
import sys

from ccpack import __version__, capcut
from ccpack.pack import PackError, default_output, pack_draft
from ccpack.package import Package, PackageError
from ccpack.scan import format_report, human_size, scan_draft
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
    return default if not answer else answer in ("y", "yes", "c", "co", "có")


def default_output_dir() -> str:
    """Next to ccpack.exe when frozen (where the user found it), else the current folder."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.getcwd()


def run_menu(drafts_dir: str) -> int:
    print(f"ccpack {__version__} — đóng gói / cài project CapCut\n")
    actions = {"1": pack_flow, "2": unpack_flow, "3": verify_flow}
    while True:
        print("1. Đóng gói project (để gửi người khác / lưu trữ)")
        print("2. Cài file .ccpack vào CapCut")
        print("3. Kiểm tra file .ccpack còn nguyên vẹn")
        print("0. Thoát")
        try:
            choice = ask("Chọn")
        except Cancelled:
            return 0
        if choice == "0":
            return 0
        if choice not in actions:
            continue
        try:
            actions[choice](drafts_dir)
        except Cancelled:
            print("Đã huỷ.")
        except (capcut.DraftNotFound, PackError, PackageError) as e:
            print(f"Lỗi: {e}")
        print()


def pack_flow(drafts_dir: str):
    drafts = capcut.list_drafts(drafts_dir)
    if not drafts:
        raise PackError(f"Không thấy project nào trong {drafts_dir}.")
    print()
    for i, d in enumerate(drafts, 1):
        when = datetime.datetime.fromtimestamp(d["modified"] / 1e6).strftime("%d/%m/%Y %H:%M") if d["modified"] else ""
        print(f"{i:3}. {d['name']:<30} {when}  {human_size(d['media_size'])}")
    choice = ask("\nSố thứ tự project cần đóng gói")
    if not choice.isdigit() or not 1 <= int(choice) <= len(drafts):
        raise Cancelled
    draft = drafts[int(choice) - 1]

    print("\nĐang quét project…")
    scan = scan_draft(draft["path"])
    print(format_report(scan))
    if scan.is_open:
        raise PackError("Project đang mở trong CapCut. Về màn hình Home của CapCut rồi chọn lại.")
    allow_missing = False
    if scan.missing:
        allow_missing = ask_yes(f"\nThiếu {len(scan.missing)} file media. Vẫn đóng gói phần còn lại?", default=False)
        if not allow_missing:
            raise Cancelled

    out_dir = ask("\nLưu vào thư mục", default_output_dir())
    output = os.path.join(out_dir, default_output(scan, as_folder=False))
    if os.path.exists(output) and not ask_yes(f"Đã có {output}. Ghi đè?", default=False):
        raise Cancelled
    pack_draft(scan, output, include_fonts=True, allow_missing=allow_missing, force=True)

    print("\nKiểm tra lại file vừa tạo…")
    with Package(output) as pkg:
        result = verify_package(pkg)
    if not result.ok:
        raise PackError(f"File {output} bị lỗi khi ghi. Đừng xoá media gốc, hãy đóng gói lại.")
    print(f"\nXong: {output} ({human_size(result.total_size)}), đã kiểm tra hash OK.")
    print("Gửi file này cho người nhận; họ bấm đúp ccpack rồi chọn 2 (hoặc kéo file thả vào ccpack).")


def unpack_flow(drafts_dir: str, path: str | None = None):
    path = path or ask("Kéo file .ccpack vào đây rồi Enter")
    if not path:
        raise Cancelled
    with Package(path) as pkg:
        print(f"Project trong gói: {pkg.manifest['draft']['name']}")
        name = ask("Tên project trong CapCut (Enter để giữ tên gốc)")
        result = unpack_package(pkg, drafts_dir, name=name or None)
    print(f"\nXong: project '{result.name}' đã được cài vào CapCut.")
    if result.fonts:
        print("Cài các font sau (chuột phải → Install) để chữ hiện đúng:")
        print("\n".join(f"  {p}" for p in result.fonts))
    if capcut.capcut_running():
        print("CapCut đang chạy: tắt hẳn CapCut rồi mở lại thì project mới hiện ra.")
    else:
        print("Mở CapCut là thấy project ở đầu danh sách.")


def verify_flow(_drafts_dir: str):
    path = ask("Kéo file .ccpack vào đây rồi Enter")
    if not path:
        raise Cancelled
    with Package(path) as pkg:
        result = verify_package(pkg, log=print)
    if result.ok:
        print(f"OK: {result.checked} file ({human_size(result.total_size)}) khớp hash. Gói nguyên vẹn.")
    else:
        print(f"GÓI BỊ LỖI: {len(result.corrupt)} file sai hash, {len(result.missing)} file bị thiếu. "
              "Đừng xoá media gốc.")


def run_dropped(path: str, drafts_dir: str) -> int:
    """A file was dropped onto ccpack.exe: install it."""
    try:
        unpack_flow(drafts_dir, path)
        return 0
    except Cancelled:
        print("Đã huỷ.")
        return 1
    except (PackError, PackageError) as e:
        print(f"Lỗi: {e}")
        return 1
