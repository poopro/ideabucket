import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("MODEL", "google/gemini-2.5-flash")
JINA_API_KEY = os.getenv("JINA_API_KEY", "")

DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "ideabucket.db"))
PROJECTS_PATH = BASE_DIR / "projects.yaml"

MAX_CONTENT_CHARS = 12000
CAPTURE_PORT = int(os.getenv("CAPTURE_PORT", "8787"))
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
