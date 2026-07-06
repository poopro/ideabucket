# Ideabucket

> 記錄日期:2026-07-06 · 狀態:構想 → 規劃

## 一句話

隨手把「有興趣但沒時間讀」的東西(GitHub repo、arXiv、Medium、blog、IG Reels)丟進一個桶子,AI 自動抓內容、總結、按專案 hashtag 自動分類歸檔、找出 idea 之間的關連與應用可能;另外可以設一個模糊目標,agent 在你睡覺時根據桶裡的素材自動推進專案。

## 兩個子系統

### A. Capture + 消化(Ingest pipeline)

```
懸浮球/分享/extension → URL 進 queue → 抓內容 → LLM 總結+hashtag 分類 → 歸檔到專案 bucket → embedding → 關連分析
```

1. **Capture 入口**(按實作成本排序)
   - Telegram bot:貼 URL 就存,手機/電腦通用,一天可做完 ← MVP 首選
   - 瀏覽器 extension / PWA share target:桌面閱讀情境
   - Android 懸浮球:原生 overlay(`SYSTEM_ALERT_WINDOW`),體驗最好但成本最高,iOS 做不到(只能 share sheet / 捷徑)
2. **內容抓取**(依來源分流)
   - GitHub → REST API 抓 README + metadata(stars、語言、topics)
   - arXiv → arXiv API 抓 abstract,必要時抓 PDF 全文
   - 一般網頁(Medium/blog)→ Jina Reader(`r.jina.ai/` 前綴即可,free tier 夠用)或 Firecrawl(輸出較乾淨,免費 1,000 credits)
   - **IG Reels** → IG 官方 API 不開放抓任意 Reels,實務走法:IG app 分享 URL 給 bot → `yt-dlp` 下載影片+caption → Whisper 轉錄語音 → 餵 LLM。注意:需要登入 cookies、IG 改版會壞,是最脆的來源,獨立成一個 adapter 隔離失敗
3. **LLM 處理**:每篇產出結構化 JSON——TL;DR(3 句)、關鍵點、標籤、「可能的應用」、「跟我現有 idea 的關連」
4. **專案 hashtag 自動分類(distribute)**
   - 你定義專案清單,每個專案一個 hashtag(例:`#rag-demo`、`#sideproject-x`),附一句描述
   - 每個 item 進來時 LLM 對照專案描述自動打 hashtag(可多個),歸檔到對應專案 bucket;配不到的進 `#inbox`,累積夠多同主題 item 時建議你開新專案
   - 專案 bucket 就是 overnight agent 的素材來源——agent 推進 `#rag-demo` 時只讀該 hashtag 下的 item
5. **儲存**:SQLite + embedding(sqlite-vec 或直接存 vector 欄位)。單人使用不需要 Postgres/pgvector
6. **關連分析**:新 item 進來時對全庫做 embedding 相似度搜尋,把 top-k 相關 item 一起丟給 LLM 問「這些之間有什麼可以組合的應用?」→ 存成 connection 紀錄

### B. 夜間自主推進(Overnight agent)

- 你設一個模糊目標(例:「用桶裡關於 RAG 的東西做個 demo」)
- 排程(cron / Claude scheduled task)在夜間喚醒 agent session
- Agent 讀取:目標 + bucket 裡相關 item 的總結 + 上次進度筆記
- 每晚做**增量進度**,結束時寫 `PROGRESS.md`(做了什麼、卡在哪、下一步)——這正是 Anthropic 建議的 long-running agent 模式:initializer + 每 session 增量推進、留下 artifacts 給下一個 session
- 實作選項:Claude Agent SDK(Python/TS)自建 loop,或直接用 Cowork/Claude Code 的 scheduled task。訂閱方案已含 Agent SDK credit(Pro $20/月額度)
- **安全邊界**:夜間 agent 只能寫在專案資料夾內、不能亂裝套件亂發請求;早上人工 review PROGRESS.md 再決定方向

## 現有工具(別重造的輪子 / 差異化在哪)

| 工具 | 有的 | 沒有的 |
|---|---|---|
| [Karakeep](https://github.com/karakeep-app/karakeep)(self-host) | 存全部+AI 自動標籤+全文搜尋 | 跨 item 關連分析、應用建議 |
| Raindrop.io Pro | AI 摘要、問答 | 關連分析、自主 agent |
| Recally | AI 摘要、semantic search | 自主 agent |
| [daily-arXiv-ai-enhanced](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced) | arXiv 每日爬+摘要 | 只限 arXiv |

**差異化 = 「關連分析 + 應用建議」和「夜間自主推進」**。前半段(存+摘要)已是紅海,可以考慮直接 self-host Karakeep 當儲存層,自己只寫關連分析和 overnight agent。

## MVP 切法(建議順序)

1. **Week 1 — Capture + 摘要**:Telegram bot + Jina Reader + LLM 摘要 → 存 SQLite。丟 URL 進去,回你一份 TL;DR
2. **Week 2 — hashtag 分類 + 關連**:定義專案清單,item 自動歸檔;加 embedding,新 item 自動回報「跟你之前存的 X、Y 有關,可能可以做 Z」
2.5. **Week 2.5 — IG Reels adapter**:yt-dlp + Whisper,獨立模組,壞了不影響主 pipeline
3. **Week 3 — 週報**:scheduled task 每週產出 digest:「這週你存了什麼、浮現了什麼主題」
4. **之後 — Overnight agent**:等 bucket 有料了再做,不然 agent 沒素材可推進
5. **最後 — 懸浮球**:UI 糖衣,價值驗證後再做

## 開放問題

- 平台優先序?(手機 capture 為主 → Telegram bot 就夠;桌面為主 → extension)
- 夜間 agent 的產出形式:程式碼 prototype?研究筆記?兩者?
- LLM 成本:每篇摘要很便宜(Haiku 級即可),關連分析用好一點的 model
- 「模糊目標」怎麼防止 agent 越跑越歪 → 每晚產出要小、可 review、可回滾(git)

## Sources

- [Karakeep](https://github.com/karakeep-app/karakeep) · [daily-arXiv-ai-enhanced](https://github.com/dw-dengwei/daily-arxiv-ai-enhanced) · [Best Read-It-Later Apps 2026](https://beemind.app/blog/best-read-it-later-apps)
- [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) · [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)
- [Jina AI vs Firecrawl](https://blog.apify.com/jina-ai-vs-firecrawl/) · [Firecrawl vs Jina Reader 2026](https://use-apify.com/blog/firecrawl-vs-jina-reader-2026)
