#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local notebook vague sync helper — HTTP API + hover capture ball.
"""

from __future__ import annotations

import json
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

_DIR = Path(__file__).resolve().parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

HOST = "127.0.0.1"
PORT = 18766
DATA_PATH = Path.home() / ".culinux" / "notebook_sync.json"

_store_lock = threading.Lock()
_store: dict[str, Any] = {
    "text": "",
    "rev": 0,
    "updatedAt": 0,
}
_persist_lock = threading.Lock()
_persistTimer: Optional[threading.Timer] = None
_PERSIST_DELAY_SEC = 0.3


def loadStore() -> None:
    global _store
    if not DATA_PATH.is_file():
        return
    try:
        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            with _store_lock:
                _store["text"] = str(raw.get("text", ""))
                _store["rev"] = int(raw.get("rev", 0))
                _store["updatedAt"] = float(raw.get("updatedAt", 0))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        traceback.print_exc()


def persistStore() -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _store_lock:
        payload = dict(_store)
    DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def setNoteMemory(text: str) -> dict[str, Any]:
    """更新内存仓库（rev / updatedAt），不写磁盘。供截获热路径使用。"""
    with _store_lock:
        _store["text"] = text
        _store["rev"] = int(_store["rev"]) + 1
        _store["updatedAt"] = time.time()
        return dict(_store)


def schedulePersist() -> None:
    """合并 0.3s 内的多次更新，在后台线程调用 persistStore。"""
    global _persistTimer
    with _persist_lock:
        if _persistTimer is not None:
            _persistTimer.cancel()
        _persistTimer = threading.Timer(_PERSIST_DELAY_SEC, persistStore)
        _persistTimer.daemon = True
        _persistTimer.start()


def flushPersist() -> None:
    global _persistTimer
    with _persist_lock:
        if _persistTimer is not None:
            _persistTimer.cancel()
            _persistTimer = None
    persistStore()


def getNote() -> dict[str, Any]:
    with _store_lock:
        return dict(_store)


def setNote(text: str) -> dict[str, Any]:
    result = setNoteMemory(text)
    persistStore()
    return result


def appendNote(text: str, newline: bool = True) -> dict[str, Any]:
    chunk = text if text else ""
    with _store_lock:
        current = str(_store["text"])
        if newline and current and not current.endswith("\n") and chunk:
            current = current + "\n"
        _store["text"] = current + chunk
        _store["rev"] = int(_store["rev"]) + 1
        _store["updatedAt"] = time.time()
        result = dict(_store)
    persistStore()
    return result


class NoteHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _corsHeaders(self) -> None:
        origin = self.headers.get("Origin", "*") or "*"
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Max-Age", "86400")

    def _send(self, code: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._corsHeaders()
        self.end_headers()
        self.wfile.write(body)

    def _readJson(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._corsHeaders()
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send(200, {"ok": True, "port": PORT})
            return
        if path == "/api/note":
            self._send(200, getNote())
            return
        self._send(404, {"error": "not found"})

    def do_PUT(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/note":
            self._send(404, {"error": "not found"})
            return
        data = self._readJson()
        text = str(data.get("text", ""))
        self._send(200, setNote(text))

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        data = self._readJson()
        if path == "/api/note/append":
            text = str(data.get("text", ""))
            newline = bool(data.get("newline", True))
            self._send(200, appendNote(text, newline=newline))
            return
        if path == "/api/note":
            text = str(data.get("text", ""))
            self._send(200, setNote(text))
            return
        self._send(404, {"error": "not found"})


def isLocalApiAlive() -> bool:
    try:
        from urllib.request import Request, urlopen

        req = Request(f"http://{HOST}:{PORT}/api/health", method="GET")
        with urlopen(req, timeout=1.0) as resp:
            return int(getattr(resp, "status", 200)) == 200
    except Exception:  # noqa: BLE001
        return False


def startHttpServer() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((HOST, PORT), NoteHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def runHoverAssistant() -> None:
    from PyQt6.QtCore import QEvent, QTimer, Qt
    from PyQt6.QtGui import QFont, QGuiApplication
    from PyQt6.QtWidgets import QApplication, QLineEdit, QVBoxLayout, QWidget

    _STYLE_IDLE = (
        "QLineEdit{background:#242424;color:#fff;border-radius:28px;"
        "border:2px solid #57bf7d;font-weight:600;padding:0 4px;}"
        "QLineEdit::placeholder{color:#fff;}"
    )
    _STYLE_CAPTURE = (
        "QLineEdit{background:#57bf7d;color:transparent;border-radius:28px;"
        "border:2px solid #57bf7d;padding:0 4px;}"
        "QLineEdit::placeholder{color:transparent;}"
    )

    class QuickNoteBall(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self._sessionBase = ""
            self._syncing = False
            self._capturing = False
            self._stopTimer = QTimer(self)
            self._stopTimer.setSingleShot(True)
            self._stopTimer.setInterval(280)
            self._stopTimer.timeout.connect(self._stopCapture)
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Window
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setMouseTracking(True)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            self.input = QLineEdit()
            self.input.setPlaceholderText("·")
            self.input.setFixedSize(56, 56)
            self.input.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.input.setFont(QFont("PingFang SC", 11))
            self.input.setStyleSheet(_STYLE_IDLE)
            self.input.setMouseTracking(True)
            self.input.textChanged.connect(self._onInputChanged)
            self.input.installEventFilter(self)
            layout.addWidget(self.input)
            self.setFixedSize(56, 56)
            screen = QGuiApplication.primaryScreen()
            if screen is not None:
                geo = screen.availableGeometry()
                self.move(geo.right() - 80, geo.bottom() - 120)

        def eventFilter(self, watched: object, event: object) -> bool:
            if watched is self.input:
                if event.type() == QEvent.Type.FocusIn:
                    self._stopTimer.stop()
                    self._startCapture()
                elif event.type() == QEvent.Type.FocusOut:
                    self._stopTimer.start()
            return super().eventFilter(watched, event)

        def enterEvent(self, event: object) -> None:
            self._stopTimer.stop()
            self.input.setFocus(Qt.FocusReason.MouseFocusReason)
            super().enterEvent(event)  # type: ignore[arg-type]

        def leaveEvent(self, event: object) -> None:
            self._stopTimer.start()
            super().leaveEvent(event)  # type: ignore[arg-type]

        def _startCapture(self) -> None:
            if self._capturing:
                return
            self._capturing = True
            self._sessionBase = str(getNote().get("text", ""))
            self._syncing = True
            self.input.clear()
            self._syncing = False
            self.input.setStyleSheet(_STYLE_CAPTURE)

        def _stopCapture(self) -> None:
            if self.input.hasFocus():
                return
            if not self._capturing:
                return
            self._capturing = False
            self.input.setStyleSheet(_STYLE_IDLE)
            self._syncing = True
            self.input.clear()
            self._syncing = False
            flushPersist()

        def _onInputChanged(self, text: str) -> None:
            if self._syncing or not self._capturing:
                return
            setNoteMemory(self._sessionBase + text)
            schedulePersist()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.aboutToQuit.connect(flushPersist)
    ball = QuickNoteBall()
    ball.show()
    print(
        "\n".join(
            [
                f"API: http://{HOST}:{PORT}",
                "Web: https://hepuyao.github.io/Jasor/2608_notebook_vague/",
                "Hover the bottom-right dot to type; syncs to the page.",
                "If the page stays offline, allow Local Network access in the browser.",
            ]
        ),
        flush=True,
    )
    raise SystemExit(app.exec())


def main() -> int:
    loadStore()
    try:
        startHttpServer()
    except OSError as err:
        if isLocalApiAlive():
            print(f"助手已在运行（API 正常）: http://{HOST}:{PORT}", flush=True)
            print("无需重复启动。刷新网页应显示「本地：已连接」。", flush=True)
            print(
                "若仍显示未连接：在浏览器中允许本站访问「本地网络 / Local Network」，然后点「重试连接」。",
                flush=True,
            )
            return 0
        print(f"无法监听 {HOST}:{PORT}: {err}", file=sys.stderr)
        print("端口被占用且无法识别为本助手，请先结束占用进程再启动。", file=sys.stderr)
        return 1
    print(f"HTTP API: http://{HOST}:{PORT}/api/note", flush=True)
    try:
        runHoverAssistant()
    except ImportError:
        print("请安装: pip3 install PyQt6", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
