import hmac
import json
import logging
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from . import config, db, night, summarize, validation

log = logging.getLogger("ideabucket.capture")

DASHBOARD = config.BASE_DIR / "dashboard.html"


def _parse(s: str) -> list:
    try:
        return json.loads(s or "[]")
    except Exception:  # noqa: BLE001
        return []


def _norm_tag(tag: str) -> str:
    return validation.normalize_tag(tag)


def _timeline(goals: dict) -> dict:
    """每個目標的合併時間軸:夜間推進紀錄 + 該 hashtag 存入的 item。"""
    out = {}
    for tag in goals:
        events = []
        for entry in night.progress_entries(tag):
            events.append(
                {
                    "date": entry["date"],
                    "ts": entry["date"] + "T03:00",
                    "kind": "progress",
                    "text": entry["text"][:1500],
                }
            )
        for it in db.items_by_hashtag(tag, limit=60):
            created_at = it.get("created_at") or ""
            events.append(
                {
                    "date": created_at[:10],
                    "ts": created_at or "0000",
                    "kind": "item",
                    "title": it.get("title") or it["url"],
                    "url": it["url"],
                    "source": it.get("source") or "web",
                    "text": (it.get("tldr") or "")[:220],
                }
            )
        events.sort(key=lambda x: x["ts"], reverse=True)
        out[tag] = events
    return out


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
        "item_total": db.count_items(),
        "connection_total": db.count_connections(),
        "goals": goals,
        "progress": progress,
        "timeline": _timeline(goals),
        "projects": summarize.load_projects(),
    }


def start_server(port: int, on_url) -> ThreadingHTTPServer:
    """背景 thread 跑極簡 HTTP server:
    GET  /          → dashboard 頁面
    GET  /api/data  → items/connections/goals/progress JSON
    POST /capture   → 收 Chrome extension / dashboard 丟來的 URL
    POST /api/delete-item → 刪除舊 idea
    POST /api/delete-goal → 刪除舊 goal
    POST /api/goal-parse → 自然語言目標解析
    POST /api/goal → 設定 goal
    POST /api/plan → 產生 AGENT_BRIEF 開工包"""

    work_slots = threading.BoundedSemaphore(4)

    class Handler(BaseHTTPRequestHandler):
        def _origin_allowed(self) -> bool:
            origin = self.headers.get("Origin", "")
            local = {
                f"http://127.0.0.1:{port}",
                f"http://localhost:{port}",
            }
            return not origin or origin in local or origin.startswith("chrome-extension://")

        def _host_allowed(self) -> bool:
            host = self.headers.get("Host", "").lower()
            return host in {f"127.0.0.1:{port}", f"localhost:{port}"}

        def _authorized(self) -> bool:
            supplied = self.headers.get("X-Ideabucket-Token", "")
            return bool(config.CAPTURE_TOKEN) and hmac.compare_digest(
                supplied, config.CAPTURE_TOKEN
            )

        def _cors(self) -> None:
            origin = self.headers.get("Origin", "")
            if origin.startswith("chrome-extension://"):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header(
                "Access-Control-Allow-Headers", "Content-Type, X-Ideabucket-Token"
            )

        def _send(self, status: int, body: bytes, ctype: str) -> None:
            self.send_response(status)
            self._cors()
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self' data:; script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:
            if not self._host_allowed() or not self._origin_allowed():
                self._send(403, b"{}", "application/json")
                return
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            try:
                if not self._host_allowed() or not self._origin_allowed():
                    self._send(403, b"{}", "application/json")
                    return
                if path in ("/", "/index.html"):
                    html = DASHBOARD.read_text(encoding="utf-8").replace(
                        "__IDEABUCKET_CAPTURE_TOKEN__",
                        json.dumps(config.CAPTURE_TOKEN),
                    ).encode()
                    self._send(200, html, "text/html; charset=utf-8")
                elif path == "/api/data":
                    if not self._authorized():
                        self._send(401, b'{"error":"unauthorized"}', "application/json")
                        return
                    body = json.dumps(_payload(), ensure_ascii=False).encode()
                    self._send(200, body, "application/json; charset=utf-8")
                else:
                    self._send(404, b"{}", "application/json")
            except Exception as e:  # noqa: BLE001
                log.exception("GET %s 失敗", path)
                self._send(500, json.dumps({"error": str(e)}).encode(), "application/json")

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > 64 * 1024:
                raise ValueError("請求內容大小不合法")
            if "application/json" not in self.headers.get("Content-Type", ""):
                raise ValueError("Content-Type 必須是 application/json")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("JSON 必須是 object")
            return data

        def _handle_capture(self) -> tuple[int, dict]:
            data = self._read_json()
            url = validation.validate_http_url(data.get("url") or "")
            if not on_url(url):
                return 409, {
                    "ok": False,
                    "error": "尚未設定 Telegram 對話，請先對 bot 傳送 /start",
                }
            return 202, {"ok": True, "status": "queued"}

        def _handle_delete_item(self) -> tuple[int, dict]:
            data = self._read_json()
            ref = str(data.get("ref") or data.get("id") or data.get("url") or "").strip()
            item = db.delete_item(ref)
            if item is None:
                return 404, {"ok": False, "error": "找不到 item"}
            return 200, {"ok": True, "item": item}

        def _handle_delete_goal(self) -> tuple[int, dict]:
            data = self._read_json()
            tag = _norm_tag(data.get("tag") or data.get("hashtag") or "")
            goal = night.delete_goal(tag)
            if goal is None:
                return 404, {"ok": False, "error": "找不到 goal"}
            return 200, {"ok": True, "tag": tag, "goal": goal}

        def _handle_goal_parse(self) -> tuple[int, dict]:
            from . import goalnlp

            data = self._read_json()
            return 200, {"ok": True, **goalnlp.parse_goal(data.get("text") or "")}

        def _handle_goal(self) -> tuple[int, dict]:
            data = self._read_json()
            tag = _norm_tag(data.get("tag") or data.get("hashtag") or "")
            goal = (data.get("goal") or "").strip()
            if not tag or not goal:
                raise ValueError("需要 hashtag 和目標描述")
            night.set_goal(tag, goal)
            return 200, {
                "ok": True,
                "tag": tag,
                "goal": goal,
                "suggestions": night.suggest_materials(tag, goal),
            }

        def _handle_plan(self) -> tuple[int, dict]:
            from . import plan

            data = self._read_json()
            tag = _norm_tag(data.get("tag") or data.get("hashtag") or "")
            goals = night.get_goals()
            if tag not in goals:
                return 404, {"ok": False, "error": f"{tag} 還沒設定目標"}
            text, path = plan.build(tag, goals[tag])
            return 200, {"ok": True, "tag": tag, "text": text, "file": path.name}

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            try:
                if not self._host_allowed() or not self._origin_allowed():
                    self._send(403, b"{}", "application/json")
                    return
                if not self._authorized():
                    self._send(401, b'{"error":"unauthorized"}', "application/json")
                    return
                if not work_slots.acquire(blocking=False):
                    self._send(429, b'{"error":"too many requests"}', "application/json")
                    return
                try:
                    if path == "/capture":
                        status, body = self._handle_capture()
                    elif path == "/api/delete-item":
                        status, body = self._handle_delete_item()
                    elif path == "/api/delete-goal":
                        status, body = self._handle_delete_goal()
                    elif path in ("/api/goal-parse", "/goal/parse"):
                        status, body = self._handle_goal_parse()
                    elif path in ("/api/goal", "/goal"):
                        status, body = self._handle_goal()
                    elif path in ("/api/goal-delete", "/goal/delete"):
                        status, body = self._handle_delete_goal()
                    elif path in ("/api/plan", "/plan"):
                        status, body = self._handle_plan()
                    else:
                        status, body = 404, {"ok": False, "error": "not found"}
                finally:
                    work_slots.release()
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
    url = f"http://127.0.0.1:{port}"
    log.info("Capture server + dashboard: %s", url)
    if config.OPEN_DASHBOARD:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            log.debug("開瀏覽器失敗,略過", exc_info=True)
    return server
