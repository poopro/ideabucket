import json
import logging
import re
from datetime import date

from . import config, db
from .summarize import chat

log = logging.getLogger("ideabucket.night")

DATE_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$", re.M)

PROMPT = """你是夜間專案推進助手。使用者給了一個(可能很模糊的)目標,請根據他存的素材做增量推進。

目標:{goal}
專案:{tag}

素材(使用者存過的相關內容):
{items}

之前的進度紀錄(最近一段,可能為空):
{prev}

輸出(繁體中文,精簡,不要跟之前的進度重複):
1. 把目標翻成本週可完成的具體子目標(一句)
2. 三個可直接動手的下一步(具體到工具/檔案/段落層級)
3. 素材裡最該先讀的 1-2 個(附一句為什麼)
4. 主要風險或卡點(一句)"""


def get_goals() -> dict:
    return json.loads(db.get_setting("goals") or "{}")


def set_goal(tag: str, goal: str) -> None:
    goals = get_goals()
    goals[tag] = goal
    db.set_setting("goals", json.dumps(goals, ensure_ascii=False))


def delete_goal(tag: str) -> str | None:
    goals = get_goals()
    if tag not in goals:
        return None
    goal = goals.pop(tag)
    db.set_setting("goals", json.dumps(goals, ensure_ascii=False))
    return goal


def progress_path(tag: str):
    return config.BASE_DIR / f"PROGRESS-{tag.lstrip('#')}.md"


def progress_entries(tag: str) -> list[dict]:
    """把 PROGRESS-<tag>.md 依 `## YYYY-MM-DD` 拆成 [{date, text}](新到舊)。"""
    path = progress_path(tag)
    if not path.exists():
        return []
    parts = DATE_RE.split(path.read_text(encoding="utf-8"))
    entries = [
        {"date": parts[i], "text": parts[i + 1].strip()}
        for i in range(1, len(parts) - 1, 2)
    ]
    entries.reverse()
    return entries


def _parse_list(value: str | None) -> list[str]:
    try:
        data = json.loads(value or "[]")
    except Exception:  # noqa: BLE001
        return []
    return data if isinstance(data, list) else []


def _goal_terms(goal: str) -> set[str]:
    return {
        t.lower()
        for t in re.findall(r"[\w\u4e00-\u9fff]{2,}", goal)
        if not t.startswith("#")
    }


def suggest_materials(tag: str, goal: str, limit: int = 5) -> list[dict]:
    """Find existing bucket items that may help a newly created goal."""
    terms = _goal_terms(goal)
    scored = []
    for it in db.all_items_full():
        tags = _parse_list(it.get("tags"))
        hashtags = _parse_list(it.get("hashtags"))
        applications = _parse_list(it.get("applications"))
        haystack = " ".join(
            [
                it.get("title") or "",
                it.get("tldr") or "",
                " ".join(tags),
                " ".join(hashtags),
                " ".join(applications),
            ]
        ).lower()
        matched = sorted(t for t in terms if t in haystack)
        score = len(matched)
        reasons = []
        if tag in hashtags:
            score += 5
            reasons.append(f"已在 {tag}")
        if matched:
            reasons.append("符合: " + ", ".join(matched[:4]))
        if score <= 0:
            continue
        scored.append(
            (
                score,
                it.get("created_at") or "",
                {
                    "id": it["id"],
                    "title": it.get("title") or it["url"],
                    "url": it["url"],
                    "hashtags": hashtags,
                    "reason": "；".join(reasons),
                },
            )
        )

    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [item for _, _, item in scored[:limit]]


def run(tag: str, goal: str) -> str:
    items = db.items_by_hashtag(tag)
    lines = [
        f"- {it['title']} | {(it['tldr'] or '')[:100]}" for it in items
    ] or ["(這個 hashtag 下還沒有素材,先給通用建議)"]

    path = progress_path(tag)
    prev = "(第一次推進)"
    if path.exists():
        prev = path.read_text(encoding="utf-8")[-2000:]

    text = chat(
        PROMPT.format(goal=goal, tag=tag, items="\n".join(lines), prev=prev)
    )
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n\n## {date.today().isoformat()}\n\n{text}\n")
    return text
