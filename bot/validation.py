import re
from pathlib import Path
from urllib.parse import urlparse

from . import config

HASHTAG_RE = re.compile(r"^#[0-9A-Za-z_\-\u4e00-\u9fff]{1,64}$")


def normalize_tag(tag: str) -> str:
    """Normalize and validate a project hashtag used in data and filenames."""
    value = (tag or "").strip()
    if value and not value.startswith("#"):
        value = "#" + value
    if not HASHTAG_RE.fullmatch(value):
        raise ValueError("hashtag 只能包含中英文、數字、底線或連字號，長度最多 64 字")
    return value


def safe_markdown_path(prefix: str, tag: str) -> Path:
    """Return a contained Markdown path for a validated hashtag."""
    slug = normalize_tag(tag)[1:]
    base = config.BASE_DIR.resolve()
    path = (base / f"{prefix}{slug}.md").resolve()
    if path.parent != base:
        raise ValueError("不安全的輸出路徑")
    return path


def validate_http_url(url: str) -> str:
    value = (url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("需要完整的 http 或 https URL")
    return value
