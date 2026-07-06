from urllib.parse import urlparse


def classify(url: str) -> str:
    """URL → 來源類型: github / arxiv / instagram / web"""
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host == "github.com":
        return "github"
    if host in ("arxiv.org", "export.arxiv.org"):
        return "arxiv"
    if host in ("instagram.com", "instagr.am"):
        return "instagram"
    return "web"
