import httpx

from .. import config


def fetch(url: str) -> tuple[str, str, str | None]:
    """一般網頁走 Jina Reader:r.jina.ai/<url> 回傳 markdown"""
    headers = {"X-Return-Format": "markdown"}
    if config.JINA_API_KEY:
        headers["Authorization"] = f"Bearer {config.JINA_API_KEY}"

    chunks = []
    total = 0
    with httpx.stream(
        "GET", f"https://r.jina.ai/{url}", headers=headers, timeout=60
    ) as r:
        r.raise_for_status()
        for chunk in r.iter_bytes():
            total += len(chunk)
            if total > 1_000_000:
                raise ValueError("網頁內容過大（超過 1 MB）")
            chunks.append(chunk)
    text = b"".join(chunks).decode("utf-8", errors="replace")

    title = ""
    for line in text.splitlines()[:5]:
        if line.startswith("Title:"):
            title = line[len("Title:"):].strip()
            break
    return title or url, text[: config.MAX_CONTENT_CHARS], None
