from pathlib import Path

from bot import db


SUMMARY = {
    "tldr": "good summary",
    "key_points": ["point"],
    "tags": ["tag"],
    "hashtags": ["#demo"],
    "applications": ["app"],
}


def test_failed_instagram_refresh_preserves_good_data(isolated_app: Path) -> None:
    url = "https://instagram.com/reel/example"
    db.save_item(url, "instagram", "good title", "good body", SUMMARY)
    db.mark_capture_failed(url, "instagram", "failed title", "temporary failure")

    item = db.all_items_full()[0]
    assert item["title"] == "good title"
    assert item["tldr"] == "good summary"
    assert item["status"] == "failed"
    assert item["last_error"] == "temporary failure"


def test_relationships_are_replaced_and_deduplicated(isolated_app: Path) -> None:
    edge = [{"url": "https://old", "reason": "r", "combo_idea": "c"}]
    db.save_connections("https://new", edge)
    db.save_connections("https://new", edge)
    assert len(db.all_connections()) == 1

    db.save_connections("https://new", [])
    assert db.all_connections() == []


def test_resurface_is_marked_only_after_delivery(isolated_app: Path) -> None:
    db.save_item("https://old", "web", "old", "body", SUMMARY)
    conn = db.get_conn()
    conn.execute(
        "UPDATE items SET created_at = '2020-01-01T00:00:00+00:00', "
        "updated_at = '2020-01-01T00:00:00+00:00'"
    )
    conn.commit()
    conn.close()

    items = db.select_resurface(1)
    assert len(items) == 1
    db.mark_surfaced([items[0]["url"]])
    conn = db.get_conn()
    assert conn.execute("SELECT last_surfaced FROM items").fetchone()[0] is not None
    conn.close()
