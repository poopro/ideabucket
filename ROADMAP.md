# Ideabucket 長期改進清單

排序原則:先讓「丟進去的東西更有價值」,再讓「系統更主動」,最後才是「更漂亮」。

## 近期(1-2 週,提升核心品質)

1. ~~**YouTube 支援**~~ ✅ 已完成(字幕 json3/vtt 解析,語言優先繁中>中>英)
2. **arXiv 全文摘要** — 現在只抓 abstract;下載 PDF 抽全文,論文摘要品質會差很多
3. **來源客製 prompt** — repo 問「能不能直接拿來用、跟什麼可組合」、論文問「方法核心、能否復現」、文章問「觀點是什麼」
4. **失敗重試與狀態欄** — items 加 `status`(ok/failed/pending),抓取失敗自動重試 2 次,`/retry` 重跑全部失敗項
5. **Whisper 語音轉錄** — IG Reels/短影片的資訊多半在語音不在文案
6. ~~**pytest + GitHub Actions**~~ ✅ 已完成(Windows/Linux、Python 3.10/3.12、安全回歸測試)

## 中期(1-2 月,讓系統更主動)

7. **Embedding 語意關連** — sqlite-vec 存 embedding,語意相似度選候選再給 LLM 判斷
8. **Dashboard 操作化** — 已讀/收藏/封存、手動改 hashtag、SQLite FTS5 全文搜尋
9. ~~**關連圖視覺化**~~ ✅ 已完成 v1(點 idea 看同專案 + 直接關連圖)
10. **真・overnight agent** — 讓夜間推進真的在 git 分支上寫 code/筆記,早上 review diff
11. **24/7 運行** — 工作排程器開機自啟,或丟到樹莓派/便宜 VPS
12. ~~**Resurfacing**~~ ✅ 已完成 v1(每天 12:30 撈 2 個 14 天以上舊 item + `/resurface`)

## 長期(願景級)

13. **主動覓食 agent** — 根據 goals 每天自動搜 arXiv/HN/GitHub trending,篩 top 3 丟進 bucket
14. **知識圖譜 → 專案孵化** — connections cluster 自動提議:「這 7 個 item 聚成一團,要開新專案嗎?」
15. **Android 懸浮球** — 等日均 capture > 10 再說
16. **模型路由** — 便宜模型初篩打標,重要 item 才用貴模型深度分析

## 工程債

- `.env` 驗證與友善錯誤訊息
- log 寫檔(RotatingFileHandler)
- DB migration 機制(sqlite `user_version`)
- `ideabucket.db` 每週自動備份
- raw_content 超過 N 個月壓縮或清掉
