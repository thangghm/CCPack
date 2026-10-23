"""Numbered menu for people who double-click ccpack instead of typing commands."""

import datetime
import os
import sys

from ccpack import __version__, capcut
from ccpack.i18n import files, tr
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


def print_fonts(fonts: list[str]):
    print(tr("Install these fonts so text displays correctly:",
             "Cài các font sau (chuột phải → Install) để chữ hiện đúng:"))
    print("\n".join(f"  {p}" for p in fonts))


def choose_drafts_dir(reason: str) -> str:
    """Ask for CapCut's drafts folder and remember it for next time."""
    print(f"\n{reason}")
    print(tr("Open CapCut → Settings → Draft, copy the path under Save to and paste it here.",
             "Mở CapCut → Settings → Draft, copy đường dẫn ở mục Save to rồi dán vào đây."))
    path = ask(tr("Paste the path or drag the folder here, then press Enter (Enter alone cancels)",
                  "Dán đường dẫn hoặc kéo thư mục vào đây rồi Enter (Enter để huỷ)"))
    if not path:
        raise Cancelled
    found = capcut.find_drafts_dir(path)
    if not found:
        raise PackError(tr(f"{path} is not a CapCut projects folder.",
                           f"{path} không phải thư mục project của CapCut."))
    capcut.save_drafts_dir(found)
    print(tr(f"Saved: {found}. ccpack will use this folder from now on.",
             f"Đã lưu: {found}. Lần sau ccpack sẽ dùng thư mục này."))
    return found


def run_menu() -> int:
    print(tr(f"ccpack {__version__} — pack and import CapCut projects\n",
             f"ccpack {__version__} — đóng gói / cài project CapCut\n"))
    actions = {"1": pack_flow, "2": unpack_flow, "3": verify_flow, "4": change_dir_flow}
    while True:
        print(tr("1. Pack a project (to send or archive)", "1. Đóng gói project (để gửi người khác / lưu trữ)"))
        print(tr("2. Import a .ccpack file into CapCut", "2. Cài file .ccpack vào CapCut"))
        print(tr("3. Check that a .ccpack file is intact", "3. Kiểm tra file .ccpack còn nguyên vẹn"))
        print(tr("4. Change the CapCut projects folder", "4. Đổi thư mục project của CapCut"))
        print(tr("0. Exit", "0. Thoát"))
        try:
            choice = ask(tr("Choose", "Chọn"))
        except Cancelled:
            return 0
        if choice == "0":
            return 0
        if choice not in actions:
            continue
        try:
            actions[choice](capcut.drafts_dir())
        except Cancelled:
            print(tr("Cancelled.", "Đã huỷ."))
        except (capcut.DraftNotFound, PackError, PackageError) as e:
            print(tr(f"Error: {e}", f"Lỗi: {e}"))
        print()


def pack_flow(drafts_dir: str):
    drafts = capcut.list_drafts(drafts_dir)
    if not drafts:
        drafts = capcut.list_drafts(choose_drafts_dir(tr(f"No projects found in {drafts_dir}.",
                                                         f"Không thấy project nào trong {drafts_dir}.")))
    if not drafts:
        raise PackError(tr("This folder has no projects yet.", "Thư mục này chưa có project nào."))
    print()
    date_format = tr("%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M")
    for i, d in enumerate(drafts, 1):
        when = datetime.datetime.fromtimestamp(d["modified"] / 1e6).strftime(date_format) if d["modified"] else ""
        print(f"{i:3}. {d['name']:<30} {when}  {human_size(d['media_size'])}")
    choice = ask(tr("\nNumber of the project to pack", "\nSố thứ tự project cần đóng gói"))
    if not choice.isdigit() or not 1 <= int(choice) <= len(drafts):
        raise Cancelled
    draft = drafts[int(choice) - 1]

    print(tr("\nScanning the project…", "\nĐang quét project…"))
    scan = scan_draft(draft["path"])
    print(format_report(scan))
    if scan.is_open:
        raise PackError(tr("The project is open in CapCut. Go back to CapCut's Home screen, then try again.",
                           "Project đang mở trong CapCut. Về màn hình Home của CapCut rồi chọn lại."))
    allow_missing = False
    if scan.missing:
        n = len(scan.missing)
        allow_missing = ask_yes(tr(f"\n{files(n)} of media missing. Pack the rest anyway?",
                                   f"\nThiếu {n} file media. Vẫn đóng gói phần còn lại?"), default=False)
        if not allow_missing:
            raise Cancelled

    out_dir = ask(tr("\nSave to folder", "\nLưu vào thư mục"), default_output_dir())
    output = os.path.join(out_dir, default_output(scan, as_folder=False))
    if os.path.exists(output) and not ask_yes(tr(f"{output} already exists. Overwrite?",
                                                 f"Đã có {output}. Ghi đè?"), default=False):
        raise Cancelled
    pack_draft(scan, output, include_fonts=True, allow_missing=allow_missing, force=True)

    print(tr("\nChecking the new file…", "\nKiểm tra lại file vừa tạo…"))
    with Package(output) as pkg:
        result = verify_package(pkg)
    if not result.ok:
        raise PackError(tr(f"{output} was not written correctly. Keep the original media and pack again.",
                           f"File {output} bị lỗi khi ghi. Đừng xoá media gốc, hãy đóng gói lại."))
    print(tr(f"\nDone: {output} ({human_size(result.total_size)}), hashes verified.",
             f"\nXong: {output} ({human_size(result.total_size)}), đã kiểm tra hash OK."))
    print(tr("Send this file to the recipient. They double-click ccpack and choose 2 "
             "(or drag the file onto ccpack).",
             "Gửi file này cho người nhận; họ bấm đúp ccpack rồi chọn 2 (hoặc kéo file thả vào ccpack)."))


def unpack_flow(drafts_dir: str, path: str | None = None):
    path = path or ask(tr("Drag the .ccpack file here, then press Enter", "Kéo file .ccpack vào đây rồi Enter"))
    if not path:
        raise Cancelled
    if not os.path.isdir(drafts_dir):
        drafts_dir = choose_drafts_dir(tr(
            f"CapCut projects folder not found ({drafts_dir}). "
            "If you have never opened CapCut, open it once and try again.",
            f"Không thấy thư mục project của CapCut ({drafts_dir}). "
            "Nếu chưa mở CapCut lần nào, mở CapCut một lần rồi thử lại."))
    with Package(path) as pkg:
        print(tr(f"Project in package: {pkg.manifest['draft']['name']}",
                 f"Project trong gói: {pkg.manifest['draft']['name']}"))
        name = ask(tr("Project name in CapCut (Enter keeps the original name)",
                      "Tên project trong CapCut (Enter để giữ tên gốc)"))
        result = unpack_package(pkg, drafts_dir, name=name or None)
    print(tr(f"\nDone: project '{result.name}' has been imported into CapCut.",
             f"\nXong: project '{result.name}' đã được cài vào CapCut."))
    if result.fonts:
        print_fonts(result.fonts)
    if capcut.capcut_running():
        print(tr("CapCut is running: quit CapCut completely and reopen it to see the new project.",
                 "CapCut đang chạy: tắt hẳn CapCut rồi mở lại thì project mới hiện ra."))
    else:
        print(tr("Open CapCut and the project will be at the top of the list.",
                 "Mở CapCut là thấy project ở đầu danh sách."))


def verify_flow(_drafts_dir: str):
    path = ask(tr("Drag the .ccpack file here, then press Enter", "Kéo file .ccpack vào đây rồi Enter"))
    if not path:
        raise Cancelled
    with Package(path) as pkg:
        result = verify_package(pkg, log=print)
    if result.ok:
        print(tr(f"OK: {files(result.checked)} ({human_size(result.total_size)}) match their hashes. "
                 "The package is intact.",
                 f"OK: {result.checked} file ({human_size(result.total_size)}) khớp hash. Gói nguyên vẹn."))
    else:
        print(tr(f"PACKAGE DAMAGED: {files(len(result.corrupt))} with a wrong hash, "
                 f"{files(len(result.missing))} missing. Keep the original media.",
                 f"GÓI BỊ LỖI: {len(result.corrupt)} file sai hash, {len(result.missing)} file bị thiếu. "
                 "Đừng xoá media gốc."))


def change_dir_flow(drafts_dir: str):
    print(tr(f"\nCurrent folder: {drafts_dir}", f"\nThư mục đang dùng: {drafts_dir}"))
    if capcut.capcut_drafts_setting():
        print(tr("ccpack takes this folder from Save to in CapCut → Settings → Draft. "
                 "Change it there.",
                 "ccpack lấy thư mục này từ mục Save to trong CapCut → Settings → Draft. "
                 "Muốn đổi thì đổi trong CapCut."))
        return
    choose_drafts_dir(tr("Choose the new projects folder.", "Chọn thư mục project mới."))


def run_dropped(path: str) -> int:
    """A file was dropped onto ccpack.exe: install it."""
    try:
        unpack_flow(capcut.drafts_dir(), path)
        return 0
    except Cancelled:
        print(tr("Cancelled.", "Đã huỷ."))
        return 1
    except (PackError, PackageError) as e:
        print(tr(f"Error: {e}", f"Lỗi: {e}"))
        return 1
