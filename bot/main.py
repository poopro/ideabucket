import asyncio
import datetime as dt
import json
import logging
import re

from telegram import Bot, Update
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)

from . import (
    capture_server,
    config,
    db,
    digest,
    night,
    plan,
    relate,
    router,
    summarize,
    validation,
)
from .adapters import FETCHERS

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
log = logging.getLogger("ideabucket")

HELP = (
    "丟 URL 給我(GitHub / arXiv / YouTube / Medium / blog / IG Reels),"
    "我會摘要、打上專案 hashtag、找出跟你存過的東西的關連。\n"
    "Chrome extension 按一下也會送到這裡。\n\n"
    "/projects 專案清單\n"
    "/recent 最近存的\n"
    "/stats 目前數量\n"
    "/digest 過去 7 天回顧\n"
    "/resurface 撈兩個舊 item 回來看\n"
    "/goal #hashtag 目標描述 — 設定夜間推進目標(不帶參數則列出)\n"
    "/delete <id或URL> 刪掉過期 idea\n"
    "/delete_goal #hashtag 刪掉過期目標\n"
    "/night 立刻執行一次夜間推進\n"
    "/plan #hashtag — 產生可直接貼給 coding agent 的開工包\n\n"
    "排程:每晚 03:00 自動推進有目標的專案、每天 12:30 resurface、每週日 20:00 發週報"
)


async def enforce_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop every update that does not come from the configured owner."""
    user_id = update.effective_user.id if update.effective_user else None
    if user_id != config.TELEGRAM_OWNER_USER_ID:
        log.warning("拒絕未授權 Telegram user_id=%s", user_id)
        raise ApplicationHandlerStop


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db.set_setting("chat_id", str(update.effective_chat.id))
    await update.message.reply_text(HELP)


async def projects_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ps = summarize.load_projects()
    text = "\n".join(f"{p['hashtag']} — {p.get('description', '')}" for p in ps)
    await update.message.reply_text(text or "還沒定義專案,編輯 projects.yaml 後重丟即可")


async def recent_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    items = db.recent_items(5)
    if not items:
        await update.message.reply_text("bucket 還是空的")
        return
    lines = []
    for it in items:
        tags = " ".join(json.loads(it["hashtags"] or "[]"))
        lines.append(f"#{it['id']} • {it['title']}\n  {tags} {it['url']}")
    await update.message.reply_text("\n".join(lines), disable_web_page_preview=True)


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"bucket 裡目前有 {db.count_items()} 個 item")


async def digest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("🧠 整理中…")
    try:
        text = await asyncio.to_thread(digest.build, 7)
        await msg.edit_text(text[:4000])
    except Exception as e:  # noqa: BLE001
        log.exception("digest 失敗")
        await msg.edit_text(f"❌ digest 失敗:{e}")


def _resurface_text(items: list[dict]) -> str | None:
    if not items:
        return None
    lines = ["⏰ 來自過去的你,這些存了一陣子了:"]
    now = dt.datetime.now(dt.timezone.utc)
    for it in items:
        try:
            age = (
                now
                - dt.datetime.fromisoformat(it.get("updated_at") or it["created_at"])
            ).days
        except ValueError:
            age = "?"
        tags = " ".join(json.loads(it["hashtags"] or "[]"))
        lines.append(
            f"\n• {it['title']}({age} 天前){tags}\n"
            f"  {(it['tldr'] or '')[:150]}\n  {it['url']}"
        )
    lines.append("\n還有價值就今天讀掉,沒價值就刪掉讓它安息")
    return "\n".join(lines)[:4000]


async def resurface_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    items = db.select_resurface(2)
    text = _resurface_text(items)
    await update.message.reply_text(
        text or "沒有存超過 14 天的 item,bucket 還很新鮮",
        disable_web_page_preview=True,
    )
    if text:
        db.mark_surfaced([it["url"] for it in items])


async def goal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args:
        goals = night.get_goals()
        if not goals:
            await update.message.reply_text(
                "還沒設定目標。用法:/goal #hashtag 目標描述\n"
                "例:/goal #ideabucket 做出關連分析的 demo"
            )
            return
        lines = [f"{tag} → {g}" for tag, g in goals.items()]
        await update.message.reply_text("\n".join(lines))
        return
    if not args[0].startswith("#") or len(args) < 2:
        await update.message.reply_text("用法:/goal #hashtag 目標描述")
        return
    try:
        tag = validation.normalize_tag(args[0])
    except ValueError as e:
        await update.message.reply_text(f"hashtag 不合法：{e}")
        return
    goal = " ".join(args[1:])
    night.set_goal(tag, goal)
    materials = await asyncio.to_thread(night.suggest_materials, tag, goal)
    await update.message.reply_text(
        format_goal_created(tag, goal, materials),
        disable_web_page_preview=True,
    )


def format_goal_created(tag: str, goal: str, materials: list[dict]) -> str:
    lines = [
        f"已設定 {tag} 的目標:{goal}",
        "每晚 03:00 自動推進,或 /night 立刻跑一次",
        "",
        "我先掃了一下素材池:",
    ]
    if not materials:
        lines.append("• 目前沒有明顯可用的既有 item,可以先丟幾個相關 URL 進來")
        return "\n".join(lines)
    for it in materials:
        tags = " ".join(it.get("hashtags") or [])
        lines.append(f"• #{it['id']} {it['title']}")
        lines.append(f"  {it.get('reason', '')} {tags}".strip())
        lines.append(f"  {it['url']}")
    return "\n".join(lines)[:4000]


async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "用法:/delete <id或URL>\n先用 /recent 看 item id"
        )
        return
    ref = args[0].rstrip(".,)>]")
    item = db.delete_item(ref)
    if item is None:
        await update.message.reply_text(f"找不到可刪除的 item:{ref}")
        return
    await update.message.reply_text(f"已刪除 #{item['id']} {item['title']}")


async def delete_goal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args or not args[0].startswith("#"):
        await update.message.reply_text("用法:/delete_goal #hashtag")
        return
    try:
        tag = validation.normalize_tag(args[0])
    except ValueError as e:
        await update.message.reply_text(f"hashtag 不合法：{e}")
        return
    goal = night.delete_goal(tag)
    if goal is None:
        await update.message.reply_text(f"找不到目標:{tag}")
        return
    await update.message.reply_text(f"已刪除 {tag} 的目標:{goal}")


async def plan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    goals = night.get_goals()
    if not goals:
        await update.message.reply_text("先用 /goal #hashtag 目標描述 設定目標")
        return
    args = context.args or []
    if args and args[0].startswith("#"):
        try:
            target_tag = validation.normalize_tag(args[0])
        except ValueError as e:
            await update.message.reply_text(f"hashtag 不合法：{e}")
            return
        if target_tag not in goals:
            await update.message.reply_text(f"{target_tag} 沒有設定目標(/goal 查看)")
            return
        targets = {target_tag: goals[target_tag]}
    else:
        targets = goals
    for tag, goal in targets.items():
        msg = await update.message.reply_text(f"📋 產生 {tag} 的開工包中…")
        try:
            text, path = await asyncio.to_thread(plan.build, tag, goal)
            await msg.edit_text(
                f"📋 {tag} 開工包(完整檔案:{path.name},在專案資料夾,"
                f"「Agent 任務指令」那段可直接貼給 Codex / Claude Code)\n\n{text}"[:4000],
                disable_web_page_preview=True,
            )
        except Exception as e:  # noqa: BLE001
            log.exception("plan 失敗: %s", tag)
            await msg.edit_text(f"❌ {tag} 開工包產生失敗:{e}")


async def night_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    goals = night.get_goals()
    if not goals:
        await update.message.reply_text("先用 /goal #hashtag 目標描述 設定目標")
        return
    for tag, goal in goals.items():
        msg = await update.message.reply_text(f"🌙 推進 {tag} 中…")
        try:
            text = await asyncio.to_thread(night.run, tag, goal)
            await msg.edit_text(f"🌙 {tag}\n\n{text}"[:4000])
        except Exception as e:  # noqa: BLE001
            log.exception("夜間推進失敗: %s", tag)
            await msg.edit_text(f"❌ {tag} 推進失敗:{e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    urls = URL_RE.findall(update.message.text or "")
    if not urls:
        await update.message.reply_text("沒看到 URL,丟連結給我就好(/start 看用法)")
        return
    for url in urls:
        cleaned = validation.validate_http_url(url.rstrip(".,)>]"))
        await process_url(context.bot, update.effective_chat.id, cleaned)


async def process_url(bot: Bot, chat_id: int, url: str) -> None:
    """共用 pipeline:Telegram 訊息和 Chrome extension 都走這裡"""
    source = router.classify(url)
    msg = await bot.send_message(chat_id, f"🔎 抓取中…({source})\n{url}")

    try:
        title, content, license = await asyncio.to_thread(FETCHERS[source], url)
    except Exception as e:  # noqa: BLE001
        log.exception("抓取失敗: %s", url)
        if source == "instagram":
            db.mark_capture_failed(
                url,
                source,
                "(IG Reels,抓取失敗)",
                str(e),
            )
            await msg.edit_text(
                f"IG 抓不到內容({e})，已記錄失敗；既有的成功資料不會被覆蓋"
            )
        else:
            await msg.edit_text(f"❌ 抓取失敗:{e}")
        return

    try:
        await msg.edit_text("🧠 摘要中…")
        data = await asyncio.to_thread(summarize.summarize, content)
        db.save_item(
            url=url, source=source, title=title, raw_content=content,
            summary=data, license=license,
        )
        related = await asyncio.to_thread(relate.find_related, url, title, data)
        goal_hits = set(night.get_goals()) & set(data.get("hashtags") or [])
        await msg.edit_text(
            format_reply(title, data, related, goal_hits), disable_web_page_preview=True
        )
    except Exception as e:  # noqa: BLE001
        log.exception("處理失敗: %s", url)
        await msg.edit_text(f"❌ 失敗:{e}")


def format_reply(
    title: str,
    d: dict,
    related: list[dict] | None = None,
    goal_hits: set | None = None,
) -> str:
    lines = [f"📌 {title}", "", d.get("tldr", "")]
    if d.get("key_points"):
        lines += [""] + [f"• {k}" for k in d["key_points"]]
    if d.get("applications"):
        lines += ["", "💡 可能應用:"] + [f"• {a}" for a in d["applications"]]
    if related:
        lines += ["", "🔗 跟你存過的有關:"]
        for r in related:
            lines.append(f"• {r['title']}:{r['reason']}")
            if r.get("combo_idea"):
                lines.append(f"  ↳ {r['combo_idea']}")
    if goal_hits:
        tags = "、".join(sorted(goal_hits))
        first = next(iter(sorted(goal_hits)))
        lines += ["", f"⚡ 對你的目標有幫助:{tags} — 用 /plan {first} 更新開工包"]
    lines += ["", " ".join(d.get("hashtags", []))]
    return "\n".join(lines)[:4000]


async def _get_chat_id() -> int | None:
    chat_id = db.get_setting("chat_id")
    return int(chat_id) if chat_id else None


async def nightly_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = await _get_chat_id()
    if not chat_id:
        return
    for tag, goal in night.get_goals().items():
        try:
            text = await asyncio.to_thread(night.run, tag, goal)
            await context.bot.send_message(chat_id, f"🌙 {tag} 夜間推進\n\n{text}"[:4000])
        except Exception:  # noqa: BLE001
            log.exception("夜間排程失敗: %s", tag)


async def resurface_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = await _get_chat_id()
    if not chat_id:
        return
    items = db.select_resurface(2)
    text = _resurface_text(items)
    if text:
        await context.bot.send_message(chat_id, text, disable_web_page_preview=True)
        db.mark_surfaced([it["url"] for it in items])


async def weekly_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    # 只在週日發(run_daily 每天觸發,這裡自己判斷,避免各版本 days 定義不一致)
    if dt.datetime.now(config.TZ).weekday() != 6:
        return
    chat_id = await _get_chat_id()
    if not chat_id:
        return
    try:
        text = await asyncio.to_thread(digest.build, 7)
        await context.bot.send_message(chat_id, text[:4000])
    except Exception:  # noqa: BLE001
        log.exception("週報排程失敗")


async def post_init(app: Application) -> None:
    """bot 啟動後:開本機 capture 端口 + 掛排程"""
    loop = asyncio.get_running_loop()

    async def capture(url: str, chat_id: int) -> None:
        await process_url(app.bot, chat_id, url)

    def on_url(url: str) -> bool:  # 在 server thread 上執行
        chat_id_raw = db.get_setting("chat_id")
        if not chat_id_raw:
            log.warning("收到 capture 但還不知道 chat_id,請先在 Telegram 對 bot /start")
            return False
        future = asyncio.run_coroutine_threadsafe(capture(url, int(chat_id_raw)), loop)

        def report_result(done) -> None:
            try:
                done.result()
            except Exception:  # noqa: BLE001
                log.exception("背景 capture 執行失敗: %s", url)

        future.add_done_callback(report_result)
        return True

    capture_server.start_server(config.CAPTURE_PORT, on_url)

    if app.job_queue is None:
        log.warning('沒裝 job-queue extra,排程功能停用(pip install "python-telegram-bot[job-queue]")')
        return
    app.job_queue.run_daily(nightly_job, dt.time(hour=3, minute=0, tzinfo=config.TZ))
    app.job_queue.run_daily(resurface_job, dt.time(hour=12, minute=30, tzinfo=config.TZ))
    app.job_queue.run_daily(weekly_job, dt.time(hour=20, minute=0, tzinfo=config.TZ))
    log.info("排程已掛:每晚 03:00 夜間推進、每天 12:30 resurface、週日 20:00 週報")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("請先把 .env.example 複製成 .env 並填 TELEGRAM_BOT_TOKEN")
    if not config.OPENROUTER_API_KEY:
        raise SystemExit("請在 .env 填 OPENROUTER_API_KEY")
    if not config.TELEGRAM_OWNER_USER_ID:
        raise SystemExit("請在 .env 填 TELEGRAM_OWNER_USER_ID（你的 Telegram 數字 user ID）")
    if len(config.CAPTURE_TOKEN) < 24:
        raise SystemExit("請在 .env 填至少 24 字元的 CAPTURE_TOKEN，並同步到 extension/config.js")

    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(TypeHandler(Update, enforce_owner), group=-1)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("projects", projects_cmd))
    app.add_handler(CommandHandler("recent", recent_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("digest", digest_cmd))
    app.add_handler(CommandHandler("resurface", resurface_cmd))
    app.add_handler(CommandHandler("goal", goal_cmd))
    for command in ("delete", "del", "remove"):
        app.add_handler(CommandHandler(command, delete_cmd))
    for command in ("delete_goal", "delgoal", "remove_goal"):
        app.add_handler(CommandHandler(command, delete_goal_cmd))
    app.add_handler(CommandHandler("plan", plan_cmd))
    app.add_handler(CommandHandler("night", night_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("Ideabucket bot 啟動,polling 中…")
    app.run_polling()


if __name__ == "__main__":
    main()
