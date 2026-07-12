import json

from . import db
from .summarize import chat

PROMPT = """以下是使用者過去 {days} 天存進 Ideabucket 的內容清單。用繁體中文寫一份簡短 digest:
1. 存了什麼(依主題歸納,不要逐條列)
2. 浮現的主題或趨勢
3. 1-2 個「接下來可以動手做」的具體建議
直接輸出內文,精簡,不要大標題。

清單:
{items}"""


def build(days: int = 7) -> str:
    items = db.items_since(days)
    if not items:
        return f"過去 {days} 天沒有存任何東西,bucket 在等你餵食"
    lines = [
        f"- {it['title']} {' '.join(json.loads(it['hashtags'] or '[]'))} | "
        f"{(it['tldr'] or '')[:80]}"
        for it in items[:200]
    ]
    omitted = max(0, len(items) - len(lines))
    suffix = f"\n（另有 {omitted} 筆因篇幅限制未列入）" if omitted else ""
    return f"📋 過去 {days} 天({len(items)} 個 item)\n\n" + chat(
        PROMPT.format(days=days, items="\n".join(lines)[:20000] + suffix)
    )
