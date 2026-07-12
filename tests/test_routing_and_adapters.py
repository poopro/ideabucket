from bot import router
from bot.adapters import arxiv


class FakeResponse:
    text = """<?xml version='1.0'?>
    <feed xmlns='http://www.w3.org/2005/Atom'>
      <entry><title>Legacy paper</title><summary>Abstract</summary>
      <author><name>Ada</name></author></entry>
    </feed>"""

    def raise_for_status(self) -> None:
        return None


def test_router_handles_case_and_explicit_port() -> None:
    assert router.classify("HTTPS://GitHub.com:443/owner/repo") == "github"


def test_legacy_arxiv_id(monkeypatch) -> None:
    seen = {}

    def fake_get(url, **_kwargs):
        seen["url"] = url
        return FakeResponse()

    monkeypatch.setattr(arxiv.httpx, "get", fake_get)
    title, _content, _license = arxiv.fetch("https://arxiv.org/abs/hep-th/9901001")
    assert title == "Legacy paper"
    assert "hep-th/9901001" in seen["url"]

