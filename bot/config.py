import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_OWNER_USER_ID_RAW = os.getenv("TELEGRAM_OWNER_USER_ID", "").strip()
TELEGRAM_OWNER_USER_ID = (
    int(TELEGRAM_OWNER_USER_ID_RAW) if TELEGRAM_OWNER_USER_ID_RAW.isdigit() else 0
)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("MODEL", "google/gemini-2.5-flash")
# 高價值低頻任務(開工包 /plan、夜間推進 /night)用的強模型;沒設就退回 MODEL
MODEL_SMART = os.getenv("MODEL_SMART", "") or MODEL
JINA_API_KEY = os.getenv("JINA_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "ideabucket.db"))
PROJECTS_PATH = BASE_DIR / "projects.yaml"

MAX_CONTENT_CHARS = 12000
CAPTURE_PORT = int(os.getenv("CAPTURE_PORT", "8787"))
CAPTURE_TOKEN = os.getenv("CAPTURE_TOKEN", "").strip()
# Only used by tests and explicit local development. Production startup requires
# a persistent token so the extension and dashboard can authenticate reliably.
if not CAPTURE_TOKEN and os.getenv("IDEABUCKET_TESTING") == "1":
    CAPTURE_TOKEN = secrets.token_urlsafe(32)
OPEN_DASHBOARD = os.getenv("OPEN_DASHBOARD", "1").strip().lower() not in (
    "0",
    "false",
    "no",
    "",
)

try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo(os.getenv("TZ_NAME", "Asia/Taipei"))
except Exception:  # noqa: BLE001
    from datetime import timezone

    TZ = timezone.utc
