import httpx

from .. import config


def fetch(url: str) -> tuple[str, str]:
    """一般網頁走 Jina Reader:r.jina.ai/<url> 回傳 markdown"""
    headers = {"X-Return-Format": "markdown"}
    if config.JINA_API_KEY:
        headers["Authorization"] = f"Bearer {config.JINA_API_KEY}"

    r = httpx.get(f"https://r.jina.ai/{url}", headers=headers, timeout=60)
    r.raise_for_status()
    text = r.text

    title = ""
    for line in text.splitlines()[:5]:
        if line.startswith("Title:"):
            title = line[len("Title:"):].strip()
            break
    return title or url, text[: config.MAX_CONTENT_CHARS]
