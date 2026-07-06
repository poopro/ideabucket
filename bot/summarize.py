import json

import httpx
import yaml

from . import config

PROMPT = """你是 Ideabucket 的整理助手。以下是使用者存的一篇內容,請閱讀後輸出 JSON(繁體中文):

{{
  "tldr": "三句以內的重點總結",
  "key_points": ["關鍵點", "..."],
  "tags": ["主題標籤", "..."],
  "hashtags": ["#..."],
  "applications": ["可能的應用、可以拿來做什麼", "..."]
}}

規則:
- key_points 3-5 個、tags 3-5 個、applications 1-3 個且要具體
- hashtags 只能從下方專案清單挑(可多選);都不符合就填 ["#inbox"]

專案清單:
{projects}

內容:
{content}

只輸出 JSON,不要其他文字。"""


def load_projects() -> list[dict]:
    with open(config.PROJECTS_PATH, encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("projects", []) or []


def parse_json(text: str, valid_hashtags: set[str]) -> dict:
    text = text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"LLM 沒有回傳 JSON: {text[:200]}")
    data = json.loads(text[start : end + 1])
    hashtags = [h for h in data.get("hashtags") or [] if h in valid_hashtags]
    data["hashtags"] = hashtags or ["#inbox"]
    for key in ("key_points", "tags", "applications"):
        data[key] = data.get(key) or []
    data["tldr"] = data.get("tldr") or ""
    return data


def chat(prompt: str, timeout: int = 120) -> str:
    """通用 OpenRouter 呼叫,回傳純文字"""
    r = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"},
        json={
            "model": config.MODEL,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def summarize(content: str) -> dict:
    projects = load_projects()
    plist = "\n".join(
        f"- {p['hashtag']}: {p.get('description', '')}" for p in projects
    ) or "(尚未定義專案)"
    text = chat(
        PROMPT.format(projects=plist, content=content[: config.MAX_CONTENT_CHARS])
    )
    return parse_json(text, {p["hashtag"] for p in projects})
