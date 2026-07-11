from bot import router


def test_classify_known_sources():
    assert router.classify("https://github.com/poopro/ideabucket") == "github"
    assert router.classify("https://arxiv.org/abs/2501.00001") == "arxiv"
    assert router.classify("https://www.instagram.com/reel/abc/") == "instagram"
    assert router.classify("https://youtu.be/abc123") == "youtube"
    assert router.classify("https://example.com/post") == "web"
