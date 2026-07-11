import json

from bot import summarize


def test_parse_json_keeps_only_valid_hashtags():
    raw = json.dumps(
        {
            "tldr": "Readable summary",
            "key_points": ["a"],
            "tags": ["agent"],
            "hashtags": ["#keep", "#drop"],
            "applications": ["use it"],
        }
    )

    data = summarize.parse_json(raw, {"#keep"})

    assert data["hashtags"] == ["#keep"]
    assert data["tldr"] == "Readable summary"


def test_parse_json_falls_back_to_inbox():
    raw = '{"hashtags":["#unknown"],"key_points":[],"tags":[],"applications":[]}'

    data = summarize.parse_json(raw, {"#known"})

    assert data["hashtags"] == ["#inbox"]
