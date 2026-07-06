import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from . import config, db, night, summarize

log = logging.getLogger("ideabucket.capture")

DASHBOARD = config.BASE_DIR / "dashboard.html"


def _parse(s: str) -> list:
    try:
        return json.loads(s or "[]")
    except Exception:  # noqa: BLE001
        return []


def _payload() -> dict:
    items = db.all_items_full()
    for it in items:
        for k in ("key_points", "tags", "hashtags", "applications"):
            it[k] = _parse(it.get(k))
    goals = night.get_goals()
    progress = {}
    for tag in goals:
        p = night.progress_path(tag)
        if p.exists():
            progress[tag] = p.read_text(encoding="utf-8")[-3000:]
    return {
        "items": items,
        "connections": db.all_connections(),
        "goals": goals,
        "progress": progress,
        "projects": summarize.load_projects(),
    }


def start_server(port: int, on_url) -> None:
    """背景 thread 跑極簡 HTTP server:
    GET  /          → dashboard 頁面
    GET  /api/data  → items/connections/goals/progress JSON
    POST /capture   → 收 Chrome extension / dashboard 丟來的 URL"""

    class Handler(BaseHTTPRequestHandler):
        def _cors(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            # Chrome Private Network Access:允許公網頁面打本機(extension 不需要,網頁端才需要)
            self.send_header("Access-Control-Allow-Private-Network", "true")

        def _send(self, status: int, body: bytes, ctype: str) -> None:
            self.send_response(status)
            self._cors()
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            try:
                if path in ("/", "/index.html"):
                    html = DASHBOARD.read_bytes()
                    self._send(200, html, "text/html; charset=utf-8")
                elif path == "/api/data":
                    body = json.dumps(_payload(), ensure_ascii=False).encode()
                    self._send(200, body, "application/json; charset=utf-8")
                else:
                    self._send(404, b"{}", "application/json")
            except Exception as e:  # noqa: BLE001
                log.exception("GET %s 失敗", path)
                self._send(500, json.dumps({"error": str(e)}).encode(), "application/json")

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/capture":
                self._send(404, b"{}", "application/json")
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(length) or b"{}")
                url = (data.get("url") or "").strip()
                if not url.startswith("http"):
                    raise ValueError("缺少 url")
                on_url(url)
                status, body = 200, {"ok": True}
            except Exception as e:  # noqa: BLE001
                status, body = 400, {"ok": False, "error": str(e)}
            self._send(
                status,
                json.dumps(body, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )

        def log_message(self, fmt: str, *args) -> None:
            log.debug(fmt, *args)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log.info("Capture server + dashboard: http://127.0.0.1:%d", port)
