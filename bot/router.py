from urllib.parse import urlparse


def classify(url: str) -> str:
    """URL → 來源類型: github / arxiv / instagram / youtube / web"""
    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("不是有效的 http/https URL")
    host = parsed.hostname.lower()
    if host.startswith("www."):
        host = host[4:]
    if host == "github.com":
        return "github"
    if host in ("arxiv.org", "export.arxiv.org"):
        return "arxiv"
    if host in ("instagram.com", "instagr.am"):
        return "instagram"
    if host in ("youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"):
        return "youtube"
    return "web"
