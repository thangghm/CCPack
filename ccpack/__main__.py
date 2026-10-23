import sys

from ccpack.cli import main
from ccpack.i18n import tr


def _owns_console() -> bool:
    """True when Windows opened a console just for us (double-click or drag-and-drop in
    Explorer), so the window would vanish before the user can read the result."""
    if sys.platform != "win32":
        return False
    import ctypes
    count = ctypes.windll.kernel32.GetConsoleProcessList((ctypes.c_uint * 4)(), 4)
    # A one-file PyInstaller build runs as two processes: the bootloader and Python.
    return count <= (2 if getattr(sys, "frozen", False) else 1)


if __name__ == "__main__":
    pause = _owns_console()
    try:
        code = main()
    except SystemExit as e:  # argparse exits for --help, --version and usage errors
        code = e.code
    except KeyboardInterrupt:
        code = 130
    if pause:
        try:
            input(tr("\nPress Enter to close…", "\nNhấn Enter để đóng…"))
        except EOFError:
            pass
    sys.exit(code)
