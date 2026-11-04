"""Windows keyboard shortcut sender for the configured Codex Voice action."""

from __future__ import annotations

import ctypes
import platform
import re
from dataclasses import dataclass


class InvalidShortcut(ValueError):
    """Raised when a configured keyboard shortcut is not supported."""


class UnsupportedShortcutPlatform(RuntimeError):
    """Raised when the Windows keyboard shortcut sender is used elsewhere."""


_MODIFIER_KEYS = {
    "CTRL": 0x11,
    "CONTROL": 0x11,
    "ALT": 0x12,
    "SHIFT": 0x10,
    "WIN": 0x5B,
    "WINDOWS": 0x5B,
}
_NAMED_KEYS = {
    "BACKSPACE": 0x08,
    "DELETE": 0x2E,
    "DOWN": 0x28,
    "END": 0x23,
    "ENTER": 0x0D,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "HOME": 0x24,
    "INSERT": 0x2D,
    "LEFT": 0x25,
    "PAGEDOWN": 0x22,
    "PAGEUP": 0x21,
    "RIGHT": 0x27,
    "SPACE": 0x20,
    "TAB": 0x09,
    "UP": 0x26,
}


@dataclass(frozen=True, slots=True)
class KeyboardShortcut:
    """A supported modifier chord and one virtual key."""

    modifiers: tuple[int, ...]
    key: int
    display: str

    @classmethod
    def parse(cls, value: str) -> KeyboardShortcut:
        parts = [part.strip().upper() for part in value.split("+")]
        if len(parts) < 2 or any(not part for part in parts):
            raise InvalidShortcut("Use a shortcut such as CTRL+SHIFT+V.")

        *modifier_names, key_name = parts
        try:
            modifiers = tuple(_MODIFIER_KEYS[name] for name in modifier_names)
        except KeyError as error:
            raise InvalidShortcut(
                f"Unsupported shortcut modifier: {error.args[0]}"
            ) from error

        if len(set(modifiers)) != len(modifiers):
            raise InvalidShortcut("A shortcut cannot repeat a modifier.")

        key = _key_code(key_name)
        if key in modifiers:
            raise InvalidShortcut("The final shortcut key must not be a modifier.")

        display = "+".join(
            _canonical_modifier(name) for name in modifier_names + [key_name]
        )
        return cls(modifiers=modifiers, key=key, display=display)


def _canonical_modifier(name: str) -> str:
    return {"CONTROL": "CTRL", "WINDOWS": "WIN"}.get(name, name)


def _key_code(name: str) -> int:
    if name in _NAMED_KEYS:
        return _NAMED_KEYS[name]
    if re.fullmatch(r"[A-Z]", name):
        return ord(name)
    if re.fullmatch(r"[0-9]", name):
        return ord(name)
    function_key = re.fullmatch(r"F([1-9]|1[0-9]|2[0-4])", name)
    if function_key:
        return 0x70 + int(function_key.group(1)) - 1
    raise InvalidShortcut(f"Unsupported shortcut key: {name}")


class WindowsKeyboardShortcut:
    """Send one configured key chord with the Windows SendInput API."""

    def __init__(self, shortcut: KeyboardShortcut) -> None:
        self.shortcut = shortcut

    def trigger(self) -> None:
        if platform.system() != "Windows":
            raise UnsupportedShortcutPlatform(
                "Codex voice keyboard shortcuts are supported on Windows only."
            )

        from ctypes import wintypes

        class KeyboardInput(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_size_t),
            ]

        class InputUnion(ctypes.Union):
            _fields_ = [("ki", KeyboardInput)]

        class Input(ctypes.Structure):
            _fields_ = [("type", wintypes.DWORD), ("union", InputUnion)]

        key_up = 0x0002
        key_down_events = [*self.shortcut.modifiers, self.shortcut.key]
        events = [(vk, 0) for vk in key_down_events]
        events.extend((vk, key_up) for vk in reversed(key_down_events))
        inputs = (Input * len(events))(
            *(
                Input(
                    type=1,
                    union=InputUnion(
                        ki=KeyboardInput(
                            wVk=vk,
                            wScan=0,
                            dwFlags=flags,
                            time=0,
                            dwExtraInfo=0,
                        )
                    ),
                )
                for vk, flags in events
            )
        )

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.SendInput.argtypes = (
            wintypes.UINT,
            ctypes.POINTER(Input),
            ctypes.c_int,
        )
        user32.SendInput.restype = wintypes.UINT
        sent = user32.SendInput(len(inputs), inputs, ctypes.sizeof(Input))
        if sent != len(inputs):
            raise ctypes.WinError(ctypes.get_last_error())


def create_voice_shortcut(value: str) -> WindowsKeyboardShortcut:
    """Parse the configured chord and create its Windows sender."""
    return WindowsKeyboardShortcut(KeyboardShortcut.parse(value))
