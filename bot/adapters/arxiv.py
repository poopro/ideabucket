import re
from urllib.parse import quote, urlparse

import httpx
from defusedxml import ElementTree as ET

NS = {"a": "http://www.w3.org/2005/Atom"}


def fetch(url: str) -> tuple[str, str, str | None]:
    path = urlparse(url).path
    candidate = re.sub(r"^/(?:abs|pdf)/", "", path, flags=re.IGNORECASE)
    candidate = re.sub(r"\.pdf$", "", candidate, flags=re.IGNORECASE)
    m = re.fullmatch(r"((?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)", candidate, re.IGNORECASE)
    if not m:
        raise ValueError("無法解析 arXiv ID")
    arxiv_id = m.group(1)

    r = httpx.get(
        f"https://export.arxiv.org/api/query?id_list={quote(arxiv_id, safe='/')}",
        timeout=30,
        follow_redirects=True,
    )
    r.raise_for_status()

    entry = ET.fromstring(r.text).find("a:entry", NS)
    if entry is None or entry.findtext("a:title", "", NS).strip() == "Error":
        raise ValueError(f"arXiv 查無 {arxiv_id}")

    title = " ".join(entry.findtext("a:title", "", NS).split())
    abstract = " ".join(entry.findtext("a:summary", "", NS).split())
    authors = ", ".join(
        a.findtext("a:name", "", NS) for a in entry.findall("a:author", NS)
    )
    # Atom API 不含 license 資訊,先回 None(之後可走 OAI-PMH 補)
    return title, f"arXiv 論文: {title}\n作者: {authors}\n\nAbstract:\n{abstract}", None
