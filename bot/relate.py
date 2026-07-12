import json
import logging

from . import db
from .summarize import chat

log = logging.getLogger("ideabucket.relate")

PROMPT = """使用者剛存了一篇新內容,以下是他之前存過的候選項目。
找出真正有關連的舊項目(最多 3 個,勉強的不要,沒有就回空陣列 []),輸出 JSON(繁體中文):
[{{"index": <候選編號>, "reason": "為什麼相關(一句)", "combo_idea": "把兩者結合可以做什麼(一句,要具體)"}}]

新內容:
標題: {title}
標籤: {tags}
摘要: {tldr}

候選:
{candidates}

只輸出 JSON array,不要其他文字。"""


def _tagset(it: dict) -> set:
    return set(json.loads(it.get("tags") or "[]")) | set(
        json.loads(it.get("hashtags") or "[]")
    )


def find_related(url: str, title: str, summary: dict) -> list[dict]:
    """回傳 [{url, title, reason, combo_idea}],同時寫進 connections 表。
    任何失敗都回空 list,不影響主流程。"""
    try:
        new_tags = set(summary.get("tags") or []) | set(summary.get("hashtags") or [])
        briefs = db.all_items_brief(exclude_url=url)
        if not briefs:
            return []

        cands = sorted(
            briefs, key=lambda it: len(new_tags & _tagset(it)), reverse=True
        )[:20]
        lines = [
            f"{i}. {it['title']} | tags: {', '.join(sorted(_tagset(it)))} | "
            f"{(it['tldr'] or '')[:100]}"
            for i, it in enumerate(cands)
        ]

        text = chat(
            PROMPT.format(
                title=title,
                tags=", ".join(sorted(new_tags)),
                tldr=summary.get("tldr", ""),
                candidates="\n".join(lines),
            )
        )
        s, e = text.find("["), text.rfind("]")
        if s == -1 or e == -1:
            return []
        arr = json.loads(text[s : e + 1])
        if not isinstance(arr, list):
            return []

        out = []
        for c in arr[:3]:
            if not isinstance(c, dict):
                continue
            i = c.get("index")
            if isinstance(i, int) and 0 <= i < len(cands):
                out.append(
                    {
                        "url": cands[i]["url"],
                        "title": cands[i]["title"],
                        "reason": c.get("reason", ""),
                        "combo_idea": c.get("combo_idea", ""),
                    }
                )
        db.save_connections(url, out)
        return out
    except Exception:  # noqa: BLE001
        log.exception("關連分析失敗(不影響主流程)")
        return []
