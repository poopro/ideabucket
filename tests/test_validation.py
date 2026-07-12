from pathlib import Path

import pytest

from bot import validation


def test_hashtag_and_output_path_are_contained(isolated_app: Path) -> None:
    assert validation.normalize_tag("demo-測試") == "#demo-測試"
    path = validation.safe_markdown_path("PROGRESS-", "#demo")
    assert path == isolated_app / "PROGRESS-demo.md"


@pytest.mark.parametrize("tag", ["#/../README", "#foo/bar", "#a:b", "#", "#a b"])
def test_rejects_unsafe_hashtags(isolated_app: Path, tag: str) -> None:
    with pytest.raises(ValueError):
        validation.safe_markdown_path("PROGRESS-", tag)


@pytest.mark.parametrize("url", ["javascript:alert(1)", "http-not-a-url", "file:///tmp/x"])
def test_rejects_non_http_urls(url: str) -> None:
    with pytest.raises(ValueError):
        validation.validate_http_url(url)

