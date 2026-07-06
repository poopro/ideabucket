import json
import sqlite3
from datetime import datetime, timedelta, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    title TEXT,
    raw_content TEXT,
    tldr TEXT,
    key_points TEXT,
    tags TEXT,
    hashtags TEXT,
    applications TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_url TEXT NOT NULL,
    related_url TEXT NOT NULL,
    reason TEXT,
    combo_idea TEXT,
    created_at TEXT NOT NULL
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def set_setting(key: str, value: str) -> None:
    conn = get_conn()
    with conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
    conn.close()


def get_setting(key: str) -> str | None:
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def save_item(url: str, source: str, title: str, raw_content: str, summary: dict) -> None:
    conn = get_conn()
    with conn:
        conn.execute(
            """
            INSERT INTO items
                (url, source, title, raw_content, tldr, key_points, tags,
                 hashtags, applications, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title = excluded.title,
                raw_content = excluded.raw_content,
                tldr = excluded.tldr,
                key_points = excluded.key_points,
                tags = excluded.tags,
                hashtags = excluded.hashtags,
                applications = excluded.applications
            """,
            (
                url,
                source,
                title,
                raw_content,
                summary.get("tldr", ""),
                json.dumps(summary.get("key_points", []), ensure_ascii=False),
                json.dumps(summary.get("tags", []), ensure_ascii=False),
                json.dumps(summary.get("hashtags", []), ensure_ascii=False),
                json.dumps(summary.get("applications", []), ensure_ascii=False),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    conn.close()


def recent_items(limit: int = 5) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT title, url, hashtags, created_at FROM items ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_items() -> int:
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    conn.close()
    return n


def all_items_brief(exclude_url: str = "", limit: int = 200) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT url, title, tags, hashtags, tldr FROM items "
        "WHERE url != ? ORDER BY id DESC LIMIT ?",
        (exclude_url, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def items_since(days: int) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = get_conn()
    rows = conn.execute(
        "SELECT url, title, tags, hashtags, tldr FROM items "
        "WHERE created_at >= ? ORDER BY id DESC",
        (cutoff,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def items_by_hashtag(hashtag: str, limit: int = 30) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT url, title, tags, hashtags, tldr FROM items "
        "WHERE hashtags LIKE ? ORDER BY id DESC LIMIT ?",
        (f'%"{hashtag}"%', limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def all_items_full(limit: int = 500) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT url, source, title, tldr, key_points, tags, hashtags, applications, "
        "created_at FROM items ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def all_connections(limit: int = 1000) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT item_url, related_url, reason, combo_idea, created_at "
        "FROM connections ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_connections(item_url: str, conns: list[dict]) -> None:
    conn = get_conn()
    with conn:
        for c in conns:
            conn.execute(
                "INSERT INTO connections (item_url, related_url, reason, combo_idea, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    item_url,
                    c.get("url", ""),
                    c.get("reason", ""),
                    c.get("combo_idea", ""),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
    conn.close()
