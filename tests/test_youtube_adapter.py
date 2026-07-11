from bot.adapters import youtube


def test_parse_json3_caption():
    data = {
        "events": [
            {"segs": [{"utf8": "Hello "}, {"utf8": "world"}]},
            {"segs": [{"utf8": "\n"}, {"utf8": "!"}]},
        ]
    }

    assert youtube.parse_json3(data) == "Hello world!"


def test_parse_vtt_caption_deduplicates_lines():
    text = """WEBVTT

00:00:00.000 --> 00:00:01.000
First line
First line

00:00:01.000 --> 00:00:02.000
Second line
"""

    assert youtube.parse_vtt(text) == "First line Second line"
