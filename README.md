# Ideabucket 🪣

> Drop a link into Telegram → AI summary + project classification + connections to everything you've saved → set a fuzzy goal and let it push your projects forward every night.

**[English](#english)** | **[繁體中文](#繁體中文)**

---

## English

### What is this?

Ideabucket is a Telegram-first **idea operating system**. Most bookmark tools are graveyards: you save things and never look at them again. Ideabucket is built around the opposite premise — everything you capture should *work for you*:

- 📥 **Capture from anywhere** — share to your Telegram bot from your phone, click the Chrome extension on desktop, or just paste a URL into the chat
- 🧠 **LLM summary + auto classification** — every link gets a TL;DR, key points, possible applications, and a project hashtag based on *your* project definitions
- 🔗 **Connection analysis** — each new item is compared against your existing bucket: *"this relates to X you saved last month — combined, you could build Z"*
- 🌙 **Goals + nightly advancement** — set a fuzzy goal per project (`/goal #rag-demo build an eval demo`); every night at 03:00 it reviews your materials and writes an incremental progress log to `PROGRESS-*.md`
- 📋 **Agent briefs** — `/plan #hashtag` generates an `AGENT_BRIEF-*.md` you can paste straight into a coding agent (Claude Code / Codex): curated materials, milestones, acceptance criteria, and boundaries
- 📊 **Web dashboard** — cards with search/filter, a force-layout connection graph, goal timelines, and a paste-to-capture box

Supported sources: **GitHub repos, arXiv papers, YouTube** (metadata + captions via yt-dlp), **general web pages** (via Jina Reader), **Instagram Reels** (caption extraction).

### Why Telegram?

Telegram **is** the app. No APK to build, no share-sheet plumbing per platform — the bot process runs on your PC and every device you own can already talk to it. Summaries come back into the same chat where you dropped the link.

### Architecture

```
  phone (share sheet) ─┐
  Chrome extension ────┤                       ┌── adapters/ (github / arxiv /
  paste in chat ───────┴─► Telegram bot ───────┤   youtube / instagram / web)
                           (bot/main.py,       │
                            polling)           ├── summarize.py ── OpenRouter LLM
                                │              ├── relate.py    ── connection analysis
       localhost:8787 ◄────────┤              └── SQLite (ideabucket.db)
       dashboard + capture     │
       server (HTTP)           ├── night.py  nightly goal advancement (03:00)
                               ├── plan.py   AGENT_BRIEF generation
                               └── digest.py weekly review (Sun 20:00)
```

One shared pipeline (`process_url`) serves every entry point — Telegram messages, the Chrome extension, and the dashboard paste box all flow through the same fetch → summarize → classify → relate → store sequence.

### Quick start (Windows, one-click)

1. **Double-click `setup.bat`** — installs Python if missing, creates the venv, installs dependencies, then opens `.env`
2. **Fill in two keys** and save:
   - `TELEGRAM_BOT_TOKEN` — message `@BotFather` on Telegram → `/newbot` → copy the token
   - `OPENROUTER_API_KEY` — <https://openrouter.ai/keys> (top up a few dollars)
3. **Double-click `run.bat`** (after updates use `restart.bat`, which also kills stale processes) → send `/start` to your bot

That's it. Drop a link at the bot, then open **<http://127.0.0.1:8787>** for the dashboard.

### Manual setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env    # fill in the two keys
python -m bot.main
```

**Define your projects** in `projects.yaml` — one hashtag + one description per project. The clearer the description, the better the auto classification. Items matching no project land in `#inbox`.

Send `/start` once so the bot remembers your chat, then just throw links at it.

### Telegram commands

| Command | What it does |
|---|---|
| `/projects` | list your project definitions |
| `/recent` | last 5 saved items (with ids) |
| `/stats` | item count |
| `/digest` | review of the past 7 days (also auto-sent Sundays 20:00) |
| `/resurface` | pull 2 old items back up (also auto-runs daily 12:30) |
| `/goal #tag description` | set a nightly-advancement goal; scans the bucket for usable materials. No args = list goals |
| `/night` | run nightly advancement now (auto-runs 03:00; results go to Telegram + `PROGRESS-*.md`) |
| `/plan #tag` | generate an agent-ready work package (`AGENT_BRIEF-*.md`) |
| `/delete <id or URL>` | delete a stale item |
| `/delete_goal #tag` | delete a goal (its `PROGRESS-*.md` history is kept) |

### Models & cost

Two model slots in `.env`, both served through OpenRouter:

| Slot | Used by | Default | Rationale |
|---|---|---|---|
| `MODEL` | summaries, classification, connection analysis | `google/gemini-2.5-flash` | high volume, cheap task — under NT$0.1 per summary |
| `MODEL_SMART` | `/plan` briefs, `/night` advancement | falls back to `MODEL` | runs a few times a day at most; planning quality compounds downstream, so a stronger model here costs pennies and pays for itself. Suggested: `deepseek/deepseek-v4-pro` (planning) or `qwen/qwen3.5-plus` (best Traditional Chinese prose) |

The brief prompt asks the model to **calibrate its own depth**: simple goals get a ~300-character brief, complex ones (many materials, existing progress history) expand with extra "Risks & unknowns" and "Trade-offs" sections — length driven by need, not padding.

`:free` models on OpenRouter work for zero-cost testing, but note they are rate-limited and your prompts (i.e. the full text of everything you save) may be logged by the provider — avoid them once private content enters your bucket.

API calls retry automatically on 429/5xx/connection errors (3 attempts with backoff).

### Chrome extension

1. Open `chrome://extensions` → enable **Developer mode**
2. **Load unpacked** → select the `extension/` folder
3. Pin the Ideabucket icon

With the bot running, click the icon on any page: green ✓ = captured (summary arrives in Telegram), red ✗ = bot not running or page not capturable.

### Design decisions

- **Adapter per source** (`bot/adapters/`) — each source is an independent module returning `(title, content)`; one breaking doesn't affect the others, and adding a source is a one-file change
- **One shared pipeline** — Telegram, extension, and dashboard all call the same `process_url`, so behavior never diverges between entry points
- **Graceful degradation** — LLM/network failures log and fall back (e.g. connection analysis returns empty rather than failing the save; unreachable IG Reels are stored to `#inbox` with just the URL)
- **SQLite + additive migrations** — schema changes are applied as idempotent `ALTER TABLE` checks on startup; no migration tooling needed at this scale
- **Local-first trust model** — the capture server binds to `127.0.0.1` and is intentionally auth-less as a single-user local tool. A multi-user version would need a shared-secret header on `/capture` and tightened CORS before anything else

### Project structure

```
bot/
  main.py            # Telegram bot (polling) + shared pipeline
  capture_server.py  # local HTTP port: dashboard + extension capture endpoint
  router.py          # URL → source type
  adapters/          # github / arxiv / youtube / instagram / web — independent modules
  summarize.py       # OpenRouter chat + summary/classification prompt
  relate.py          # cross-item connection analysis
  goalnlp.py         # natural-language goal → hashtag/goal
  night.py           # goals, progress log, nightly advancement
  plan.py            # AGENT_BRIEF work packages
  digest.py          # weekly review
  db.py              # SQLite (ideabucket.db)
extension/           # Chrome extension (one-click capture)
dashboard.html       # single-file web dashboard
projects.yaml        # your project hashtag definitions
ROADMAP.md           # long-term improvement list
```

### Known limitations & what's next

Honest list: no tests/CI yet, no retry status column for failed fetches, arXiv summaries use the abstract only, `raw_content` is stored unbounded, and URL dedup is exact-match (UTM variants create duplicates). The longer-term direction — embedding-based semantic connections, an MCP server so coding agents can query the bucket directly, and true overnight agent runs on git branches — lives in [ROADMAP.md](ROADMAP.md).

---

## 繁體中文

### 這是什麼?

Ideabucket 是一個以 Telegram 為入口的**想法作業系統**。大部分書籤工具是墳場:存進去就再也不會看。Ideabucket 反過來——你存的每個東西都應該**替你工作**:

- 📥 **隨處捕捉** — 手機分享給 Telegram bot、電腦點 Chrome extension、或直接在對話貼 URL
- 🧠 **LLM 摘要 + 自動分類** — 每個連結產生重點總結、關鍵點、可能應用,並依**你自己定義的專案**打上 hashtag
- 🔗 **關連分析** — 每個新 item 會跟你存過的東西比對:「跟你上個月存的 X 有關,結合起來可以做 Z」
- 🌙 **目標 + 夜間推進** — 每個專案設一個模糊目標(`/goal #rag-demo 做出 eval demo`),每晚 03:00 自動根據素材做增量推進,寫進 `PROGRESS-*.md`
- 📋 **開工包** — `/plan #hashtag` 產生 `AGENT_BRIEF-*.md`,可直接貼給 coding agent(Claude Code / Codex):篩選過的素材、milestones、驗收標準、邊界
- 📊 **Web dashboard** — 卡片搜尋/篩選、關連網絡圖、目標時間軸、貼 URL 直接存的輸入框

支援來源:**GitHub repo、arXiv、YouTube**(yt-dlp 抓 metadata + 字幕)、**一般網頁**(走 Jina Reader)、**IG Reels**(抓文案)。

### 為什麼用 Telegram?

**Telegram 就是你的 app**。不用做 APK、不用處理各平台的分享機制——bot 程式在你電腦上跑著,你的每個裝置本來就能跟它說話,摘要結果直接回到你丟連結的那個對話裡。

### 快速開始(Windows 一鍵版)

1. **雙擊 `setup.bat`** — 自動裝 Python(如果沒有)、建環境、裝套件,結束會自動打開 `.env`
2. **填兩個金鑰**進 `.env` 後存檔:
   - `TELEGRAM_BOT_TOKEN`:Telegram 搜 `@BotFather` → 傳 `/newbot` → 拿 token
   - `OPENROUTER_API_KEY`:<https://openrouter.ai/keys>(儲值幾美金)
3. **雙擊 `run.bat`** 啟動(重啟或更新後改用 `restart.bat`,會自動清掉舊進程)→ 對你的 bot 傳 `/start`

就這樣。丟連結給 bot 試試,然後開 **<http://127.0.0.1:8787>** 看 dashboard。

### 手動安裝

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   (填入兩個金鑰)
python -m bot.main
```

**定義你的專案**:編輯 `projects.yaml`,每個專案一個 hashtag + 一句描述(描述越清楚,自動分類越準)。配不到任何專案的 item 自動進 `#inbox`。

跑起來後**先對 bot 傳一次 `/start`**(讓它記住你的 chat),之後丟任何連結即可。

### Telegram 指令

| 指令 | 功能 |
|---|---|
| `/projects` | 專案清單 |
| `/recent` | 最近存的 5 個(含 id)|
| `/stats` | 目前數量 |
| `/digest` | 過去 7 天回顧(每週日 20:00 也會自動發)|
| `/resurface` | 撈兩個舊 item 回來看(每天 12:30 也會自動提醒)|
| `/goal #hashtag 目標描述` | 設定夜間推進目標,並掃 bucket 找可用素材;不帶參數 = 列出目前目標 |
| `/night` | 立刻執行夜間推進(每晚 03:00 自動跑,結果發 Telegram + 寫 `PROGRESS-*.md`)|
| `/plan #hashtag` | 產生可直接貼給 coding agent 的開工包(`AGENT_BRIEF-*.md`)|
| `/delete <id或URL>` | 刪掉過期 item |
| `/delete_goal #hashtag` | 刪掉過期目標(`PROGRESS-*.md` 紀錄保留)|

### 模型與成本

`.env` 裡有兩個模型欄位,都走 OpenRouter:

| 欄位 | 用在 | 預設 | 理由 |
|---|---|---|---|
| `MODEL` | 摘要、分類、關連分析 | `google/gemini-2.5-flash` | 量大、任務簡單——一篇摘要 < NT$0.1 |
| `MODEL_SMART` | `/plan` 開工包、`/night` 夜間推進 | 沒設就跟 `MODEL` 一樣 | 一天只跑幾次,但規劃品質會被下游放大——用強模型每月多花不到一杯咖啡。推薦 `deepseek/deepseek-v4-pro`(規劃強)或 `qwen/qwen3.5-plus`(繁中文筆好)|

開工包的 prompt 會讓模型**自行判斷該寫多深**:簡單目標精簡到 300 字內,複雜目標(素材多、有進度歷史)自動展開「風險與未知」「方案取捨」段落——長度由需要決定,不靠廢話撐。

OpenRouter 的 `:free` 模型可以零成本測試,但注意有速率限制、而且你的 prompt(= 你存的所有內容全文)可能被記錄——bucket 開始有私人內容後就別用免費層。

API 呼叫遇到 429/5xx/連線錯誤會自動重試(最多 3 次,含退避)。

### Chrome extension 安裝

1. Chrome 開 `chrome://extensions` → 右上角打開「開發人員模式」
2. 「載入未封裝項目」→ 選這個資料夾裡的 `extension/`
3. 把 Ideabucket 圖示釘選到工具列

bot 跑著的時候,任何頁面點一下圖示:綠色 ✓ = 已送出(摘要會出現在 Telegram),紅色 ✗ = bot 沒開或該頁面存不了。

### 設計決策

- **每個來源一個 adapter**(`bot/adapters/`)— 各自獨立回傳 `(title, content)`,壞一個不影響其他,加新來源只要加一個檔案
- **共用 pipeline** — Telegram、extension、dashboard 都走同一個 `process_url`,行為永遠一致
- **優雅降級** — LLM/網路失敗只記 log 不炸流程(關連分析失敗回空、IG 抓不到就把 URL 存進 `#inbox`)
- **SQLite + 增量 migration** — schema 變更用啟動時的冪等 `ALTER TABLE` 檢查,這個規模不需要 migration 框架
- **Local-first 信任模型** — capture server 綁 `127.0.0.1`,單人本機工具刻意不做認證;要做多人版,第一件事是幫 `/capture` 加 shared-secret header 並收緊 CORS

### 結構

```
bot/
  main.py            # Telegram bot(polling)+ 共用 pipeline
  capture_server.py  # 本機 HTTP 端口:dashboard + extension capture
  router.py          # URL → 來源類型
  adapters/          # github / arxiv / youtube / instagram / web 各自獨立
  summarize.py       # OpenRouter 呼叫 + 摘要/分類 prompt
  relate.py          # 跨 item 關連分析
  goalnlp.py         # 自然語言目標 → hashtag/goal
  night.py           # 目標、進度紀錄、夜間推進
  plan.py            # AGENT_BRIEF 開工包
  digest.py          # 週報
  db.py              # SQLite(ideabucket.db)
extension/           # Chrome extension(一鍵 capture)
dashboard.html       # 單檔 web dashboard
projects.yaml        # 你的專案 hashtag 定義
ROADMAP.md           # 長期改進清單
ideabucket-規劃.md   # 完整規劃
```

### 已知限制與下一步

誠實清單:還沒有測試/CI、抓取失敗沒有重試狀態欄、arXiv 只摘要 abstract、`raw_content` 無上限累積、URL 去重是完全比對(UTM 參數會造成重複)。長期方向——embedding 語意關連、讓 coding agent 直接查 bucket 的 MCP server、真・在 git branch 上動工的 overnight agent——見 [ROADMAP.md](ROADMAP.md)。
