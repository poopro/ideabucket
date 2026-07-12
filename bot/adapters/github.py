import httpx
from urllib.parse import urlparse

from .. import config

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "ideabucket",
    "X-GitHub-Api-Version": "2022-11-28",
}
if config.GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"


def fetch(url: str) -> tuple[str, str, str | None]:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if (parsed.hostname or "").lower() not in {"github.com", "www.github.com"} or len(parts) < 2:
        raise ValueError("無法解析 GitHub repo URL")
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        r = client.get(f"https://api.github.com/repos/{owner}/{repo}", headers=HEADERS)
        r.raise_for_status()
        meta = r.json()

        readme_headers = {**HEADERS, "Accept": "application/vnd.github.raw+json"}
        readme = client.get(
            f"https://api.github.com/repos/{owner}/{repo}/readme",
            headers=readme_headers,
        )
        if readme.status_code == 200:
            readme_text = readme.text[: config.MAX_CONTENT_CHARS]
        elif readme.status_code == 404:
            readme_text = "(無 README)"
        else:
            readme.raise_for_status()

    title = meta.get("full_name", f"{owner}/{repo}")
    # SPDX id(MIT / Apache-2.0 / GPL-3.0…);沒有 license 或 NOASSERTION 都視為未知
    license_ = (meta.get("license") or {}).get("spdx_id")
    if license_ == "NOASSERTION":
        license_ = None
    header = (
        f"GitHub repo: {title}\n"
        f"描述: {meta.get('description') or '(無)'}\n"
        f"Stars: {meta.get('stargazers_count')} | 語言: {meta.get('language')} | "
        f"License: {license_ or '(未標)'} | "
        f"Topics: {', '.join(meta.get('topics') or [])}\n\n"
        f"README:\n"
    )
    return title, (header + readme_text)[: config.MAX_CONTENT_CHARS], license_
