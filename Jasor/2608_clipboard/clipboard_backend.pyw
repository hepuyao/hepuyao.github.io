#!/usr/bin/env python3
"""Clipboard 本地后台（单文件）：监控剪切板并提供 HTTP API。"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import mimetypes
import platform
import socket
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

try:
    from PIL import Image, ImageGrab
except ImportError:
    print("请先安装依赖: pip install Pillow", file=sys.stderr)
    sys.exit(1)

HOST = "127.0.0.1"
SERVER_PORT = 8765
LAUNCHER_PORT = 8764
POLL_INTERVAL_SEC = 0.8
DEFAULT_IDLE_TIMEOUT_SEC = 90
BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / ".clipboard_cache"
_START_SERVER_LOCK = threading.Lock()
_LAST_START_ATTEMPT = 0.0

if sys.platform == "win32":
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0


# ---------------------------------------------------------------------------
# 剪切板读取
# ---------------------------------------------------------------------------


@dataclass
class ClipboardContent:
    text: str
    source: str
    is_empty: bool


@dataclass
class ClipboardSnapshot:
    content_type: str
    text: str = ""
    image: Optional[Image.Image] = None
    source: str = ""


@dataclass
class ClipboardState:
    text: str = ""
    image: Optional[Image.Image] = None
    text_source: str = ""
    image_source: str = ""


def build_text_fingerprint(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"text:{digest}"


def build_image_fingerprint(image: Image.Image) -> str:
    normalized = image.convert("RGB")
    buffer = io.BytesIO()
    normalized.save(buffer, format="PNG")
    digest = hashlib.sha256(buffer.getvalue()).hexdigest()
    return f"image:{digest}"


def _normalize_text(value: str) -> str:
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    return text.rstrip("\n")


def _looks_like_binary_text(text: str) -> bool:
    if not text:
        return False
    if "\x00" in text:
        return True
    sample = text[:64]
    non_printable = sum(1 for ch in sample if ord(ch) < 32 and ch not in "\n\t")
    return non_printable > 8


def _run_subprocess(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """运行子进程；Windows 下隐藏控制台窗口，避免反复弹窗。"""
    if sys.platform == "win32":
        kwargs.setdefault("creationflags", CREATE_NO_WINDOW)
    return subprocess.run(args, **kwargs)


def _read_text_with_platform_command() -> Optional[ClipboardContent]:
    system = platform.system()
    if system == "Darwin":
        result = _run_subprocess(["pbpaste"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return None
        normalized = _normalize_text(result.stdout)
        if _looks_like_binary_text(normalized):
            return ClipboardContent(text="", source="pbpaste", is_empty=True)
        return ClipboardContent(text=normalized, source="pbpaste", is_empty=normalized == "")
    if system == "Windows":
        command = ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", "Get-Clipboard -Raw"]
        result = _run_subprocess(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return None
        normalized = _normalize_text(result.stdout)
        return ClipboardContent(text=normalized, source="powershell", is_empty=normalized == "")
    return None


def _read_clipboard_image() -> Optional[Image.Image]:
    image = ImageGrab.grabclipboard()
    if isinstance(image, Image.Image):
        return image.convert("RGB")
    if isinstance(image, list) and image:
        first = Path(str(image[0]))
        if first.exists() and first.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}:
            return Image.open(first).convert("RGB")
    return None


def read_clipboard_text() -> ClipboardContent:
    platform_content = _read_text_with_platform_command()
    if platform_content is not None and not platform_content.is_empty:
        return platform_content
    return ClipboardContent(text="", source="empty", is_empty=True)


def read_clipboard_state() -> ClipboardState:
    text_content = read_clipboard_text()
    image = _read_clipboard_image()
    return ClipboardState(
        text=text_content.text if not text_content.is_empty else "",
        image=image,
        text_source=text_content.source,
        image_source="imagegrab" if image is not None else "",
    )


def clear_system_clipboard() -> None:
    """清空操作系统剪切板（其他软件粘贴将为空）。"""
    system = platform.system()
    if system == "Darwin":
        result = _run_subprocess(["pbcopy"], input="", text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError("macOS 清空剪切板失败")
        return
    if system == "Windows":
        command = [
            "powershell",
            "-NoProfile",
            "-WindowStyle",
            "Hidden",
            "-Command",
            "Set-Clipboard -Value $null",
        ]
        result = _run_subprocess(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            # 兼容旧系统：用 clip 写入空内容
            fallback = _run_subprocess(
                ["cmd", "/c", "echo.|clip"],
                capture_output=True,
                text=True,
                check=False,
            )
            if fallback.returncode != 0:
                message = result.stderr.strip() or fallback.stderr.strip() or "未知错误"
                raise RuntimeError(f"Windows 清空剪切板失败: {message}")
        return
    raise RuntimeError(f"当前平台暂不支持清空系统剪切板: {system}")


# ---------------------------------------------------------------------------
# 历史存储
# ---------------------------------------------------------------------------


@dataclass
class HistoryEntry:
    entry_id: str
    content_type: str
    preview: str
    created_at: str
    text: str = ""
    image_path: str = ""
    source: str = ""
    width: int = 0
    height: int = 0


class HistoryStore:
    INDEX_FILE = "index.json"

    def __init__(self, cache_dir: Path, max_items: int = 200) -> None:
        self.cache_dir = cache_dir
        self.images_dir = cache_dir / "images"
        self.max_items = max_items
        self.entries: list[HistoryEntry] = []
        self._fingerprints: set[str] = set()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    def add_snapshot(self, snapshot: ClipboardSnapshot) -> Optional[HistoryEntry]:
        if snapshot.content_type == "empty":
            return None
        fingerprint = self._build_fingerprint(snapshot)
        if fingerprint in self._fingerprints:
            return None
        entry = self._create_entry(snapshot)
        self.entries.insert(0, entry)
        self._fingerprints.add(fingerprint)
        self._trim()
        self._save()
        return entry

    def get_entry(self, entry_id: str) -> Optional[HistoryEntry]:
        for entry in self.entries:
            if entry.entry_id == entry_id:
                return entry
        return None

    def clear(self) -> None:
        self.entries.clear()
        self._fingerprints.clear()
        for image_file in self.images_dir.glob("*.png"):
            image_file.unlink(missing_ok=True)
        index_path = self.cache_dir / self.INDEX_FILE
        if index_path.exists():
            index_path.unlink()

    def _create_entry(self, snapshot: ClipboardSnapshot) -> HistoryEntry:
        entry_id = uuid.uuid4().hex[:12]
        created_at = datetime.now().isoformat(timespec="seconds")
        if snapshot.content_type == "text":
            preview = snapshot.text.replace("\n", " ")[:80]
            return HistoryEntry(
                entry_id=entry_id,
                content_type="text",
                preview=preview or "（空文本）",
                created_at=created_at,
                text=snapshot.text,
                source=snapshot.source,
            )
        if snapshot.content_type == "image" and snapshot.image is not None:
            image_path = self.images_dir / f"{entry_id}.png"
            snapshot.image.save(image_path, format="PNG")
            width, height = snapshot.image.size
            return HistoryEntry(
                entry_id=entry_id,
                content_type="image",
                preview=f"截图 {width}×{height}",
                created_at=created_at,
                image_path=str(image_path),
                source=snapshot.source,
                width=width,
                height=height,
            )
        raise ValueError(f"unsupported snapshot: {snapshot.content_type}")

    def _build_fingerprint(self, snapshot: ClipboardSnapshot) -> str:
        if snapshot.content_type == "text":
            return build_text_fingerprint(snapshot.text)
        if snapshot.content_type == "image" and snapshot.image is not None:
            return build_image_fingerprint(snapshot.image)
        return f"empty:{uuid.uuid4().hex}"

    def _entry_fingerprint(self, entry: HistoryEntry) -> str:
        if entry.content_type == "text":
            return build_text_fingerprint(entry.text)
        if entry.content_type == "image" and entry.image_path:
            path = Path(entry.image_path)
            if path.exists():
                return build_image_fingerprint(Image.open(path).convert("RGB"))
        return f"unknown:{entry.entry_id}"

    def _trim(self) -> None:
        if len(self.entries) <= self.max_items:
            return
        removed = self.entries[self.max_items :]
        self.entries = self.entries[: self.max_items]
        alive_ids = {entry.entry_id for entry in self.entries}
        for entry in removed:
            if entry.content_type == "image" and entry.image_path:
                Path(entry.image_path).unlink(missing_ok=True)
        self._fingerprints = {self._entry_fingerprint(entry) for entry in self.entries}
        for image_file in self.images_dir.glob("*.png"):
            if image_file.stem not in alive_ids:
                image_file.unlink(missing_ok=True)

    def _load(self) -> None:
        index_path = self.cache_dir / self.INDEX_FILE
        if not index_path.exists():
            return
        try:
            raw = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for item in raw:
            entry = HistoryEntry(**item)
            if entry.content_type == "image":
                if not entry.image_path or not Path(entry.image_path).exists():
                    continue
            self.entries.append(entry)
            self._fingerprints.add(self._entry_fingerprint(entry))

    def _save(self) -> None:
        index_path = self.cache_dir / self.INDEX_FILE
        payload = [asdict(entry) for entry in self.entries]
        index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def entry_to_summary(entry: HistoryEntry) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": entry.entry_id,
        "contentType": entry.content_type,
        "preview": entry.preview,
        "createdAt": entry.created_at,
        "source": entry.source,
    }
    if entry.content_type == "text":
        payload["text"] = entry.text
    if entry.content_type == "image":
        payload["width"] = entry.width
        payload["height"] = entry.height
        payload["imageUrl"] = f"/api/image/{entry.entry_id}"
    return payload


def entry_to_detail(entry: HistoryEntry) -> dict[str, Any]:
    payload = entry_to_summary(entry)
    if entry.content_type == "image" and entry.image_path:
        image_path = Path(entry.image_path)
        if image_path.exists():
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            payload["imageDataUrl"] = f"data:image/png;base64,{encoded}"
    return payload


# ---------------------------------------------------------------------------
# 监控 & HTTP 服务
# ---------------------------------------------------------------------------


class ClipboardMonitor:
    def __init__(self, store: HistoryStore) -> None:
        self.store = store
        self.is_running = False
        self.last_text_fingerprint = ""
        self.last_image_fingerprint = ""
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self.is_running:
                return
            self.is_running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self.is_running = False

    @property
    def running(self) -> bool:
        return self.is_running

    def _loop(self) -> None:
        while self.is_running:
            try:
                self._poll_once()
            except Exception:
                pass
            time.sleep(POLL_INTERVAL_SEC)

    def _poll_once(self) -> None:
        state = read_clipboard_state()
        if state.text:
            text_fp = build_text_fingerprint(state.text)
            if text_fp != self.last_text_fingerprint:
                self.store.add_snapshot(ClipboardSnapshot("text", text=state.text, source=state.text_source))
                self.last_text_fingerprint = text_fp
        if state.image is not None:
            image_fp = build_image_fingerprint(state.image)
            if image_fp != self.last_image_fingerprint:
                self.store.add_snapshot(ClipboardSnapshot("image", image=state.image, source=state.image_source))
                self.last_image_fingerprint = image_fp


class ServerState:
    def __init__(self) -> None:
        self.store = HistoryStore(cache_dir=CACHE_DIR)
        self.monitor = ClipboardMonitor(self.store)
        self.last_request_at = time.time()
        self.idle_timeout_sec = DEFAULT_IDLE_TIMEOUT_SEC
        self.httpd: Optional[ThreadingHTTPServer] = None


STATE = ServerState()


def touch_request() -> None:
    """刷新最近一次网页请求时间，用于空闲超时判断。"""
    STATE.last_request_at = time.time()


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "ClipboardBackend/1.0"

    def do_OPTIONS(self) -> None:
        touch_request()
        self.send_response(204)
        self._send_cors()
        self.end_headers()

    def do_GET(self) -> None:
        touch_request()
        path = urlparse(self.path).path
        if path == "/api/health":
            idle_left = max(0, int(STATE.idle_timeout_sec - (time.time() - STATE.last_request_at)))
            self._json(
                {
                    "ok": True,
                    "monitoring": STATE.monitor.running,
                    "historyCount": len(STATE.store.entries),
                    "idleTimeoutSec": STATE.idle_timeout_sec,
                    "idleLeftSec": idle_left,
                },
            )
            return
        if path == "/api/history":
            self._json({"entries": [entry_to_summary(e) for e in STATE.store.entries]})
            return
        if path.startswith("/api/entry/"):
            entry = STATE.store.get_entry(path.split("/")[-1])
            if entry is None:
                self._json({"error": "not found"}, 404)
                return
            self._json(entry_to_detail(entry))
            return
        if path.startswith("/api/image/"):
            entry = STATE.store.get_entry(path.split("/")[-1])
            if entry is None or entry.content_type != "image":
                self.send_error(404)
                return
            image_path = Path(entry.image_path)
            if not image_path.exists():
                self.send_error(404)
                return
            content = image_path.read_bytes()
            self.send_response(200)
            self._send_cors()
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        touch_request()
        path = urlparse(self.path).path
        if path == "/api/monitor/start":
            STATE.monitor.start()
            self._json({"ok": True, "monitoring": True})
            return
        if path == "/api/monitor/stop":
            STATE.monitor.stop()
            self._json({"ok": True, "monitoring": False})
            return
        if path == "/api/history/clear":
            STATE.store.clear()
            STATE.monitor.last_text_fingerprint = ""
            STATE.monitor.last_image_fingerprint = ""
            self._json({"ok": True})
            return
        if path == "/api/clipboard/clear":
            try:
                clear_system_clipboard()
                STATE.monitor.last_text_fingerprint = ""
                STATE.monitor.last_image_fingerprint = ""
            except Exception as exc:  # noqa: BLE001
                self._json({"ok": False, "error": str(exc)}, 500)
                return
            self._json({"ok": True})
            return
        self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._send_cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((HOST, port)) == 0


def start_server_process(port: int = SERVER_PORT) -> bool:
    global _LAST_START_ATTEMPT
    if is_port_open(port):
        return True
    with _START_SERVER_LOCK:
        if is_port_open(port):
            return True
        now = time.time()
        if now - _LAST_START_ATTEMPT < 5.0:
            return is_port_open(port)
        _LAST_START_ATTEMPT = now
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--server",
            "--port",
            str(port),
            "--no-banner",
            "--idle-timeout",
            str(DEFAULT_IDLE_TIMEOUT_SEC),
        ]
        popen_kwargs: dict[str, Any] = {"cwd": str(BASE_DIR), "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
            popen_kwargs["close_fds"] = True
        else:
            popen_kwargs["start_new_session"] = True
        subprocess.Popen(command, **popen_kwargs)
    for _ in range(25):
        if is_port_open(port):
            return True
        time.sleep(0.2)
    return False


class LauncherHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_cors()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"ok": True, "serverRunning": is_port_open(SERVER_PORT)})
            return
        if self.path == "/start":
            started = start_server_process()
            self._json({"ok": started, "serverRunning": is_port_open(SERVER_PORT)})
            return
        self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    def _json(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self._send_cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _watch_idle_timeout(httpd: ThreadingHTTPServer, idle_timeout_sec: int, show_banner: bool) -> None:
    """一段时间无网页请求后自动关闭 server。"""
    while True:
        time.sleep(2.0)
        idle_for = time.time() - STATE.last_request_at
        if idle_for < idle_timeout_sec:
            continue
        if show_banner:
            print(f"\n已空闲 {int(idle_for)} 秒，自动退出 server")
        STATE.monitor.stop()
        threading.Thread(target=httpd.shutdown, daemon=True).start()
        return


def run_server(
    port: int = SERVER_PORT,
    auto_monitor: bool = True,
    show_banner: bool = True,
    idle_timeout_sec: int = DEFAULT_IDLE_TIMEOUT_SEC,
) -> None:
    if auto_monitor:
        STATE.monitor.start()
    STATE.idle_timeout_sec = idle_timeout_sec
    STATE.last_request_at = time.time()
    httpd = ThreadingHTTPServer((HOST, port), ApiHandler)
    STATE.httpd = httpd
    if idle_timeout_sec > 0:
        threading.Thread(
            target=_watch_idle_timeout,
            args=(httpd, idle_timeout_sec, show_banner),
            daemon=True,
        ).start()
    if show_banner:
        print(f"Clipboard 后台已启动: http://{HOST}:{port}")
        if idle_timeout_sec > 0:
            print(f"网页关闭后约 {idle_timeout_sec} 秒无请求将自动退出")
        print("按 Ctrl+C 停止")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        if show_banner:
            print("\n已停止")
    finally:
        STATE.monitor.stop()
        httpd.server_close()


def run_launcher(port: int = LAUNCHER_PORT) -> None:
    httpd = HTTPServer((HOST, port), LauncherHandler)
    print(f"Clipboard 唤醒器已启动: http://{HOST}:{port}")
    print("网页可通过 /start 拉起后台；server 空闲后会自动退出，launcher 常驻")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        httpd.server_close()


def is_pythonw() -> bool:
    """判断是否由 pythonw 启动（无控制台）。"""
    return Path(sys.executable).stem.lower() == "pythonw"


def is_pyw_script() -> bool:
    """判断当前脚本是否为 .pyw。"""
    return Path(sys.argv[0]).suffix.lower() == ".pyw"


def main() -> int:
    parser = argparse.ArgumentParser(description="Clipboard 本地后台（单文件）")
    parser.add_argument("--server", action="store_true", help="启动 API 后台")
    parser.add_argument("--launcher", action="store_true", help="启动唤醒器，供在线网页拉起后台")
    parser.add_argument("--port", type=int, default=SERVER_PORT, help="后台端口，默认 8765")
    parser.add_argument("--no-monitor", action="store_true", help="启动时不自动监控剪切板")
    parser.add_argument("--no-banner", action="store_true", help="不打印启动信息")
    parser.add_argument(
        "--idle-timeout",
        type=int,
        default=DEFAULT_IDLE_TIMEOUT_SEC,
        help="无网页请求多少秒后自动退出，默认 90；0 表示永不因空闲退出",
    )
    args = parser.parse_args()
    # 双击 .pyw / 用 pythonw 运行时：默认启动 launcher（轻量常驻）
    # 命令行 python clipboard_backend.py：默认启动 server
    use_launcher = args.launcher
    use_server = args.server
    if not use_launcher and not use_server:
        use_launcher = is_pythonw() or is_pyw_script()
        use_server = not use_launcher
    if use_launcher:
        run_launcher()
        return 0
    run_server(
        port=args.port,
        auto_monitor=not args.no_monitor,
        show_banner=not args.no_banner,
        idle_timeout_sec=max(0, args.idle_timeout),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
