import json
import logging
from datetime import date

from . import config, db
from .summarize import chat

log = logging.getLogger("ideabucket.night")

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


def progress_path(tag: str):
    return config.BASE_DIR / f"PROGRESS-{tag.lstrip('#')}.md"


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
