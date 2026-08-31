from __future__ import annotations

from typing import Optional

_PASS = frozenset(
    {
        "cmd",
        "cmd_l",
        "cmd_r",
        "ctrl",
        "ctrl_l",
        "ctrl_r",
        "alt",
        "alt_l",
        "alt_r",
        "shift",
        "shift_l",
        "shift_r",
        "esc",
        "tab",
        "up",
        "down",
        "left",
        "right",
        "home",
        "end",
        "page_up",
        "page_down",
        "caps_lock",
        "f1",
        "f2",
        "f3",
        "f4",
        "f5",
        "f6",
        "f7",
        "f8",
        "f9",
        "f10",
        "f11",
        "f12",
    }
)


def applyCaptureKey(text: str, keyName: str, char: Optional[str]) -> Optional[str]:
    name = (keyName or "").lower()
    if name in _PASS:
        return None
    if name == "backspace" or name == "\x08":
        return text[:-1] if text else ""
    if name in ("enter", "return"):
        return text + "\n"
    if name == "space":
        return text + " "
    if char is not None and len(char) == 1 and char.isprintable():
        return text + char
    return None
