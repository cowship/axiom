# main.py — 엔트리 포인트 (Tk 루트 생성 + SRApp 실행)
from __future__ import annotations

import os
import tkinter as tk

from app import SRApp


def _hide_console_if_windows() -> None:
    """Windows에서 콘솔 창을 숨긴다 (실행 파일 배포용)."""
    if os.name == "nt":
        try:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
        except Exception:
            # 콘솔이 없거나 ctypes 사용이 불가한 환경에서는 그냥 무시
            pass


def main() -> None:
    _hide_console_if_windows()
    root = tk.Tk()
    app = SRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
