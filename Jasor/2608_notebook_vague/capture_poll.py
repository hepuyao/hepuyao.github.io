#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""截获中轮询前台应用输入框文字（支持中文，不读剪贴板）。"""

from __future__ import annotations

import os
import sys
import traceback
from typing import Optional


def selfPid() -> int:
    return os.getpid()


def frontmostPid(excludePid: Optional[int] = None) -> Optional[int]:
    if sys.platform != "darwin":
        return None
    try:
        from AppKit import NSWorkspace

        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return None
        pid = int(app.processIdentifier())
        if excludePid is not None and pid == excludePid:
            return None
        return pid
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return None


def axGetFocusedInputText(pid: int) -> Optional[str]:
    if sys.platform != "darwin":
        return None
    try:
        from ApplicationServices import (
            AXUIElementCopyAttributeValue,
            AXUIElementCreateApplication,
            kAXFocusedUIElementAttribute,
            kAXSelectedTextAttribute,
            kAXValueAttribute,
        )

        appRef = AXUIElementCreateApplication(pid)
        err, focused = AXUIElementCopyAttributeValue(
            appRef, kAXFocusedUIElementAttribute, None
        )
        if err != 0 or focused is None:
            return None
        err, selected = AXUIElementCopyAttributeValue(
            focused, kAXSelectedTextAttribute, None
        )
        if err == 0 and selected:
            chunk = str(selected).strip()
            if chunk:
                return chunk
        err, value = AXUIElementCopyAttributeValue(focused, kAXValueAttribute, None)
        if err == 0 and value is not None:
            return str(value)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
    return None


def deltaFromFieldChange(previous: str, current: str) -> str:
    """输入框内容变化 → 应追加到笔记的增量。"""
    if current == previous:
        return ""
    if current.startswith(previous):
        return current[len(previous) :]
    if previous.startswith(current):
        return ""
    return current
