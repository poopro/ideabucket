import pytest

from bot.summarize import parse_json


def test_parse_json_validates_field_types() -> None:
    malformed = (
        '{"tldr":"ok","hashtags":["#demo"],"key_points":"wrong",'
        '"tags":[],"applications":1}'
    )
    with pytest.raises(ValueError):
        parse_json(malformed, {"#demo"})


def test_parse_json_filters_unknown_hashtags() -> None:
    raw = (
        '{"tldr":"ok","hashtags":["#unknown"],"key_points":[],"tags":[],'
        '"applications":[]}'
    )
    assert parse_json(raw, {"#demo"})["hashtags"] == ["#inbox"]

