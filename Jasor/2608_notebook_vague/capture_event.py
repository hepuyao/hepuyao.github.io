#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""macOS 键盘事件 → 笔记字符（含输入法上屏 Unicode）。"""

from __future__ import annotations

import ctypes
import sys
from typing import Optional

# macOS 虚拟键码
_VK_SPACE = 49
_VK_RETURN = 36
_VK_DELETE = 51
_VK_FORWARD_DELETE = 117


def isChineseOrImeInputActive() -> bool:
    if sys.platform != "darwin":
        return False
    try:
        from Quartz import (
            kTISPropertyInputSourceID,
            kTISPropertyInputSourceIsASCIICapable,
            TISCopyCurrentKeyboardInputSource,
            TISGetInputSourceProperty,
        )

        source = TISCopyCurrentKeyboardInputSource()
        if source is None:
            return False
        asciiCap = TISGetInputSourceProperty(
            source, kTISPropertyInputSourceIsASCIICapable
        )
        if asciiCap is not None and not bool(asciiCap):
            return True
        sourceId = TISGetInputSourceProperty(source, kTISPropertyInputSourceID)
        if sourceId is None:
            return False
        sid = str(sourceId).lower()
        if "com.apple.keylayout.abc" in sid or sid.endswith(".abc"):
            return False
        if "inputmethod" in sid or "pinyin" in sid or "wubi" in sid or "itabc" in sid:
            return True
        return True
    except Exception:  # noqa: BLE001
        return False


def unicodeFromCgEvent(event: object) -> str:
    if sys.platform != "darwin":
        return ""
    from Quartz import CGEventKeyboardGetUnicodeString

    buf = (ctypes.c_uint16 * 8)()
    length = CGEventKeyboardGetUnicodeString(event, 8, buf)
    if length <= 0:
        return ""
    return "".join(chr(buf[i]) for i in range(length))


def hasCommandOrControl(event: object) -> bool:
    from Quartz import CGEventGetFlags, kCGEventFlagMaskCommand, kCGEventFlagMaskControl

    flags = CGEventGetFlags(event)
    return bool(flags & (kCGEventFlagMaskCommand | kCGEventFlagMaskControl))


def vkFromCgEvent(event: object) -> int:
    from Quartz import CGEventGetIntegerValueField, kCGKeyboardEventKeycode

    return int(CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode))


def keyNameFromVk(vk: int) -> str:
    if vk == _VK_SPACE:
        return "space"
    if vk == _VK_RETURN:
        return "enter"
    if vk in (_VK_DELETE, _VK_FORWARD_DELETE):
        return "backspace"
    if 0 <= vk <= 50:
        return "letter"
    return ""


# US ANSI 小写（截获英文备用；正常情况 Unicode 事件已覆盖）
_VK_TO_CHAR: dict[int, str] = {
    0: "a",
    1: "s",
    2: "d",
    3: "f",
    4: "h",
    5: "g",
    6: "z",
    7: "x",
    8: "c",
    9: "v",
    11: "b",
    12: "q",
    13: "w",
    14: "e",
    15: "r",
    16: "y",
    17: "t",
    31: "o",
    32: "u",
    34: "i",
    35: "p",
    37: "l",
    38: "j",
    40: "k",
    45: "n",
    46: "m",
}


def charFromVk(vk: int, shifted: bool = False) -> Optional[str]:
    ch = _VK_TO_CHAR.get(vk)
    if ch is None:
        return None
    return ch.upper() if shifted else ch


def isShifted(event: object) -> bool:
    from Quartz import CGEventGetFlags, kCGEventFlagMaskShift

    return bool(CGEventGetFlags(event) & kCGEventFlagMaskShift)


def shouldPassThroughForIme(vk: int, unicodeText: str) -> bool:
    """拼音组合阶段：无 Unicode、字母键 → 放行给输入法，不截获。"""
    if unicodeText:
        return False
    if not isChineseOrImeInputActive():
        return False
    return vk <= 50