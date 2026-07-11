import sqlite3
from datetime import datetime, timedelta, timezone

from bot import config, db


def use_temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "ideabucket-test.db"))


def test_delete_item_removes_connections(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    db.save_item(
        "https://example.com/a",
        "web",
        "A",
        "raw",
        {"hashtags": ["#demo"], "tags": [], "key_points": [], "applications": []},
    )
    db.save_connections(
        "https://example.com/a",
        [{"url": "https://example.com/b", "reason": "related", "combo_idea": "ship"}],
    )

    item = db.delete_item("1")

    assert item["title"] == "A"
    assert db.count_items() == 0
    assert db.all_connections() == []


def test_pick_resurface_marks_old_items(monkeypatch, tmp_path):
    use_temp_db(monkeypatch, tmp_path)
    db.save_item(
        "https://example.com/old",
        "web",
        "Old",
        "raw",
        {"hashtags": ["#demo"], "tags": [], "key_points": [], "applications": []},
    )
    old_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    conn = sqlite3.connect(config.DB_PATH)
    with conn:
        conn.execute(
            "UPDATE items SET created_at = ? WHERE url = ?",
            (old_date, "https://example.com/old"),
        )
    conn.close()

    items = db.pick_resurface(1, min_age_days=14)

    assert [it["title"] for it in items] == ["Old"]
    conn = sqlite3.connect(config.DB_PATH)
    row = conn.execute("SELECT last_surfaced FROM items").fetchone()
    conn.close()
    assert row[0]
