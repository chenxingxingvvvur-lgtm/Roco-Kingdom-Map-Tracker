"""Cross‑platform helpers for overlay‑style tool windows.

Windows 用 Win32 API 设置窗口扩展样式，
macOS 用 Qt 属性实现等效行为。
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

_IS_MAC = sys.platform == "darwin"
_IS_WIN = sys.platform.startswith("win")


def set_click_through(qwidget: QWidget, enabled: bool) -> None:
    """Enable or disable mouse click‑through."""
    if _IS_WIN:
        _win_set_click_through(qwidget, enabled)
    elif _IS_MAC:
        _mac_set_click_through(qwidget, enabled)


def apply_overlay_flags(qwidget: QWidget) -> None:
    """Keep the window hidden from Alt‑Tab／App Switcher without blocking focus."""
    if _IS_WIN:
        _win_apply_overlay_flags(qwidget)
    elif _IS_MAC:
        _mac_apply_overlay_flags(qwidget)


# ── macOS ──────────────────────────────────────────────────────────────

def _mac_set_click_through(qwidget: QWidget, enabled: bool) -> None:
    qwidget.setAttribute(Qt.WA_TransparentForMouseEvents, enabled)


def _mac_apply_overlay_flags(qwidget: QWidget) -> None:
    qwidget.setAttribute(Qt.WA_ShowWithoutActivating, True)
    qwidget.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)


# ── Windows ────────────────────────────────────────────────────────────

if _IS_WIN:
    import ctypes

    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_TOOLWINDOW = 0x00000080

    def _get_hwnd(qwidget) -> int | None:
        try:
            return int(qwidget.winId())
        except Exception:
            return None

    def _set_style_bits(hwnd: int, bits: int, enabled: bool) -> None:
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enabled:
            style |= bits
        else:
            style &= ~bits
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    def _win_set_click_through(qwidget, enabled: bool) -> None:
        hwnd = _get_hwnd(qwidget)
        if hwnd is None:
            return
        _set_style_bits(hwnd, WS_EX_LAYERED, True)
        _set_style_bits(hwnd, WS_EX_TRANSPARENT, enabled)

    def _win_apply_overlay_flags(qwidget) -> None:
        hwnd = _get_hwnd(qwidget)
        if hwnd is None:
            return
        _set_style_bits(hwnd, WS_EX_LAYERED | WS_EX_TOOLWINDOW, True)
