# Ideabucket

丟 URL 給 Telegram bot → 自動抓內容 → LLM 摘要 + 專案 hashtag 分類 + 跨 item 關連分析 → 存 SQLite,並可設定模糊目標讓它每晚自動推進專案。附 web dashboard。

支援來源:GitHub repo、arXiv、一般網頁(Medium/blog,走 Jina Reader)、IG Reels(yt-dlp 抓文案)。

## 🚀 快速開始(一鍵版)

1. **雙擊 `setup.bat`** — 自動裝 Python(如果沒有)、建環境、裝套件,結束會自動打開 `.env`
2. **填兩個金鑰**進 `.env` 後存檔:
   - `TELEGRAM_BOT_TOKEN`:Telegram 搜 `@BotFather` → 傳 `/newbot` → 拿 token
   - `OPENROUTER_API_KEY`:<https://openrouter.ai/keys>(儲值幾美金)
3. **雙擊 `run.bat`** 啟動(重啟或更新程式後改用 `restart.bat`,會自動清掉舊進程)→ Telegram 對你的 bot 傳 `/start`

就這樣。丟連結給 bot 試試,然後開 **<http://127.0.0.1:8787>** 看 dashboard。

## Dashboard

bot 跑著的時候開 <http://127.0.0.1:8787>:全部 item(摘要/應用/hashtag 篩選/搜尋)、每張卡片的 🔗 關連分析、🌙 目標與夜間推進紀錄,右上有「貼 URL 直接存」輸入框(extension 的備用入口)。

## 怎麼用(不用裝 APK)

**Telegram 就是你的 app**,bot 程式在電腦上跑著就好:

- **手機**:看到有趣的東西 → 分享 → Telegram → 選你的 bot。IG Reels、瀏覽器、任何 app 都通用
- **電腦瀏覽器**:裝下面的 Chrome extension,點一下工具列按鈕就存
- **直接聊天**:任何裝置打開 Telegram 貼連結

摘要結果都會回到 Telegram 對話裡。

## 手動安裝(不想用 .bat 的話)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   (填入兩個金鑰)
python -m bot.main
```

模型預設 `google/gemini-2.5-flash`(一篇摘要 < NT$0.1),`.env` 可換,零成本可用註解裡的 free model。

**定義你的專案**:編輯 `projects.yaml`,每個專案一個 hashtag + 一句描述(描述越清楚,自動分類越準)。

跑起來後**先對 bot 傳一次 `/start`**(讓它記住你的 chat),之後丟任何連結即可。

指令:
- `/projects` 專案清單、`/recent` 最近存的、`/stats` 數量
- `/digest` 過去 7 天回顧(每週日 20:00 也會自動發)
- `/goal #hashtag 目標描述` 設定夜間推進目標(不帶參數 = 列出目前目標)
- `/night` 立刻執行一次夜間推進(每晚 03:00 自動跑,結果發 Telegram + 寫進 `PROGRESS-*.md`)

新 item 存入時會自動跟你存過的東西做**關連分析**,回覆裡的 🔗 區塊會告訴你「跟 X 有關,可以合體做 Z」。

## Chrome extension 安裝

1. Chrome 開 `chrome://extensions` → 右上角打開「開發人員模式」
2. 「載入未封裝項目」→ 選這個資料夾裡的 `extension/`
3. 把 Ideabucket 圖示釘選到工具列

用法:bot 跑著的時候,任何頁面點一下圖示 → 綠色 ✓ = 已送出,摘要會出現在 Telegram;紅色 ✗ = bot 沒開或該頁面存不了。

## 結構

```
bot/
  main.py            # Telegram bot(polling)+ 共用 pipeline
  capture_server.py  # 本機 HTTP 端口,收 extension 丟來的 URL
  router.py          # URL → 來源類型
  adapters/          # github / arxiv / web(Jina Reader)各自獨立,壞一個不影響其他
  summarize.py       # OpenRouter 摘要 + hashtag 分類
  db.py              # SQLite(ideabucket.db)
extension/           # Chrome extension(一鍵 capture)
projects.yaml        # 你的專案 hashtag 定義
ideabucket-規劃.md   # 完整規劃
```

## Roadmap

- [x] Week 1:capture + 摘要 + hashtag 分類
- [x] Chrome extension 一鍵 capture
- [x] Week 2:關連分析(LLM 比對,「跟你存過的 X 有關,可以做 Z」)
- [x] Week 2.5:IG Reels adapter(yt-dlp 抓 caption;語音轉錄之後可加)
- [x] Week 3:每週 digest(/digest + 週日 20:00 排程)
- [x] 夜間推進(/goal + /night + 每晚 03:00 排程,寫 PROGRESS-*.md)
- [ ] 之後:語音轉錄(Whisper)、真・overnight coding agent、Android 懸浮球
