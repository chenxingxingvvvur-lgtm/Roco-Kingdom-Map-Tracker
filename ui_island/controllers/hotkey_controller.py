"""Hotkey listener management for island window.

macOS 和 Windows 统一使用 pynput 实现全局快捷键。
"""

from __future__ import annotations

import time

import config

from ..services.hotkey_config import (
    key_vk,
    modifier_names,
    normalize_action_hotkeys,
    normalize_hotkey_payload,
)

try:
    from pynput import keyboard
except ImportError:  # pragma: no cover
    keyboard = None


class HotkeyController:
    def __init__(self, window) -> None:
        self.window = window

    def configured_hotkeys(self) -> list[tuple[str, dict]]:
        hotkeys: list[tuple[str, dict]] = [
            ("toggle_lock", normalize_hotkey_payload(getattr(config, "TOGGLE_LOCK_HOTKEY", None)))
        ]
        for action, payload in normalize_action_hotkeys(getattr(config, "ACTION_HOTKEYS", None)).items():
            if payload is not None:
                hotkeys.append((action, payload))
        return hotkeys

    def set_suspended(self, suspended: bool) -> None:
        self.window._hotkeys_suspended = bool(suspended)

    def start_listener(self) -> None:
        if keyboard is None:
            return

        hotkeys = [
            (action, modifier_names(payload), key_vk(payload))
            for action, payload in self.configured_hotkeys()
        ]
        pressed_modifiers: set[str] = set()

        def on_press(key):
            modifier = self._pynput_modifier_name(key)
            if modifier is not None:
                pressed_modifiers.add(modifier)
                return
            vk = self._pynput_vk(key)
            for action, required_modifiers, target_vk in hotkeys:
                if vk == target_vk and set(required_modifiers) == pressed_modifiers:
                    self.request_action(action)
                    return

        def on_release(key):
            modifier = self._pynput_modifier_name(key)
            if modifier is not None:
                pressed_modifiers.discard(modifier)

        self.window._hotkey_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.window._hotkey_listener.daemon = True
        self.window._hotkey_listener.start()

    def request_action(self, action: str) -> None:
        if self.window._hotkeys_suspended:
            return
        now = time.monotonic()
        if now - self.window._last_hotkey_at < self.window._HOTKEY_DEBOUNCE_SEC:
            return
        self.window._last_hotkey_at = now
        self.window._hotkey_action_requested.emit(str(action))

    @staticmethod
    def _pynput_vk(key) -> int | None:
        value = getattr(key, "vk", None)
        if value is not None:
            return int(value)
        nested = getattr(key, "value", None)
        value = getattr(nested, "vk", None)
        if value is not None:
            return int(value)
        return None

    @staticmethod
    def _pynput_modifier_name(key) -> str | None:
        if keyboard is None:
            return None
        if key in HotkeyController._pynput_keys("ctrl", "ctrl_l", "ctrl_r"):
            return "Ctrl"
        if key in HotkeyController._pynput_keys("alt", "alt_l", "alt_r"):
            return "Alt"
        if key in HotkeyController._pynput_keys("shift", "shift_l", "shift_r"):
            return "Shift"
        if key in HotkeyController._pynput_keys("cmd", "cmd_l", "cmd_r"):
            return "Meta"
        return None

    @staticmethod
    def _pynput_keys(*names: str) -> tuple:
        if keyboard is None:
            return ()
        return tuple(value for name in names if (value := getattr(keyboard.Key, name, None)) is not None)

    def stop_listener(self) -> None:
        if self.window._hotkey_listener is not None:
            self.window._hotkey_listener.stop()
            self.window._hotkey_listener = None
