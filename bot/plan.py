import logging
from datetime import date
from pathlib import Path

from . import config, db, night
from .summarize import chat

log = logging.getLogger("ideabucket.plan")

PROMPT = """你是專案規劃助手。使用者有一個目標和一堆收集的素材,請產出一份「可以直接交給 coding agent(如 Claude Code / Codex)執行」的計畫。

目標({tag}):{goal}

素材(使用者存的相關內容):
{items}

素材之間已知的關連:
{connections}

之前的進度紀錄(節錄,可能為空):
{prev}

輸出格式(繁體中文,Markdown,精簡):

## 子目標
(把模糊目標翻成一週可完成、可驗收的具體子目標,一句)

## Milestones
(3-5 個,每個一行,附驗收標準)

## Agent 任務指令
(這一節要寫成「可以整段複製貼給 coding agent 的 prompt」:
- 明確說要建什麼、建議的檔案結構與技術選型
- 列出要參考的素材 URL,各自說明要看什麼、取什麼
- 驗收標準與測試方式
- 邊界:明確說不要做什麼、不要越出範圍)

## 需要人工決定的事
(agent 做不了、需要使用者自己選擇的 1-3 件事)"""


def build(tag: str, goal: str) -> tuple[str, Path]:
    """產生 agent 執行計畫,寫入 AGENT_BRIEF-<tag>.md,回傳 (內容, 檔案路徑)。"""
    items = db.items_by_hashtag(tag, limit=30)
    item_lines = [
        f"- {it['title']} {it['url']}\n  {(it['tldr'] or '')[:120]}" for it in items
    ] or ["(這個 hashtag 下還沒有素材,請基於目標本身規劃,並建議該收集什麼素材)"]

    urls = {it["url"] for it in items}
    conns = [
        c
        for c in db.all_connections()
        if c["item_url"] in urls or c["related_url"] in urls
    ][:15]
    conn_lines = [
        f"- {c['item_url']} ↔ {c['related_url']}:{c['combo_idea'] or c['reason']}"
        for c in conns
    ] or ["(還沒有)"]

    prev = "(無)"
    ppath = night.progress_path(tag)
    if ppath.exists():
        prev = ppath.read_text(encoding="utf-8")[-1500:]

    text = chat(
        PROMPT.format(
            tag=tag,
            goal=goal,
            items="\n".join(item_lines),
            connections="\n".join(conn_lines),
            prev=prev,
        ),
        timeout=180,
    )

    path = config.BASE_DIR / f"AGENT_BRIEF-{tag.lstrip('#')}.md"
    path.write_text(
        f"# Agent Brief — {tag}\n\n"
        f"> 目標:{goal}\n> 產生時間:{date.today().isoformat()}"
        f"(素材 {len(items)} 個、關連 {len(conns)} 條)\n\n{text}\n",
        encoding="utf-8",
    )
    return text, path
