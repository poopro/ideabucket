import json
import logging
import re

from . import db, summarize, validation

log = logging.getLogger("ideabucket.goalnlp")

TAG_RE = re.compile(r"#([0-9A-Za-z_\-\u4e00-\u9fff]+)")

PROMPT = """你是目標解析助手。使用者用自然語言描述一個想推進的專案目標,請把它對應到一個 hashtag。

現有專案:
{projects}

現有目標(已設定):
{goals}

使用者輸入:
{text}

規則:
- 若輸入明顯屬於某個現有專案,hashtag 就用那個現有的(要一字不差)。
- 若都不合適,提議一個新的、簡短、全小寫英文的 hashtag(例 #myapp),並把 is_new 設為 true。
- goal 欄位:把輸入整理成一句清楚、可執行的目標描述(繁體中文,句子裡不要放 hashtag)。
- reason:一句話說明為什麼選這個標籤。

只輸出 JSON,不要其他文字:
{{"hashtag": "#xxx", "goal": "...", "is_new": false, "reason": "..."}}"""


def _norm_tag(tag: str) -> str:
    return validation.normalize_tag(tag)


def parse_goal(text: str) -> dict:
    """自然語言目標 → {tag, goal, is_new, reason, source}。"""
    text = (text or "").strip()
    if not text:
        raise ValueError("請輸入目標")

    projects = summarize.load_projects()
    known = {p["hashtag"] for p in projects} | set(db.get_goals())

    m = TAG_RE.search(text)
    if m:
        tag = "#" + m.group(1)
        goal = TAG_RE.sub("", text).strip(" ,,、-—:：") or text
        return {
            "tag": tag,
            "goal": goal,
            "is_new": tag not in known,
            "reason": "你指定的標籤",
            "source": "explicit",
        }

    plist = "\n".join(
        f"- {p['hashtag']}: {p.get('description', '')}" for p in projects
    ) or "(尚未定義專案)"
    goals = db.get_goals()
    glist = "\n".join(f"- {tag}: {goal}" for tag, goal in goals.items()) or "(尚未設定)"
    raw = summarize.chat(
        PROMPT.format(projects=plist, goals=glist, text=text), timeout=60
    )

    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"LLM 沒回傳 JSON:{raw[:150]}")
    data = json.loads(raw[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("LLM JSON 必須是 object")
    tag = _norm_tag(data.get("hashtag") or "")
    raw_goal = data.get("goal") or text
    if not isinstance(raw_goal, str):
        raise ValueError("LLM goal 必須是字串")
    goal = raw_goal.strip()[:1000]
    if not tag:
        raise ValueError("LLM 沒給出 hashtag,請自己打一個 #tag")
    return {
        "tag": tag,
        "goal": goal,
        "is_new": tag not in known,
        "reason": (data.get("reason") if isinstance(data.get("reason"), str) else "")[:500],
        "source": "llm",
    }
