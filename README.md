# 苓雅通 V1.1｜Heroku / Python

苓雅區活動、公告、補助與生活消息整合網站。保留原始來源連結、發布日期、活動日期、來源單位及同步時間。手機版、搜尋、分類、機關篩選、範圍篩選、分頁與來源健康狀態已完成。

## 從 V1 更新到 V1.1

本版新增首頁「全部單位／區公所／衛生所／戶政／市政府／旅遊網／文化部」直接點選篩選，與原本下拉選單同步。僅需覆蓋 GitHub 的三個檔案，再 Deploy Branch：

- templates/index.html
- static/app.js
- static/style.css

資料庫、Config Vars、web 和 worker 維持現況，不需要刪除或重建資料庫。本版沒有更動爬蟲來源或繞過文化部限制。

## 先讀這段

這是可自行上傳 GitHub、部署 Heroku 的第一版程式，不是已上線網站。首批六個來源設定並不代表已涵蓋所有機關與活動；文化部來源在本次驗證被 robots.txt 限制，程式會顯示失敗且不繞過。這版不抓 Facebook、LINE、登入內容或圖片內的文字，也未回補各站所有歷史分頁。公告擷取優先讀首頁與指定消息欄目，單來源每輪最多40篇；可增加但會拉長同步週期。沒有資料不等於沒有活動。

## Heroku 網頁操作部署（GitHub）

1. 解壓縮 ZIP，把裡面的檔案直接上傳到 GitHub repository 根目錄。根目錄要看得到 `app.py`、`requirements.txt`、`Procfile`，不要再包一層資料夾。`.python-version` 也要上傳。
2. Heroku 建立新 App；本包採 Heroku-24。到 Resources 加入 **Heroku Postgres**。這是需要持久儲存的服務，請依 Dashboard 顯示確認方案費用；不要用 SQLite 當 Heroku 正式資料庫。
3. Settings → Config Vars 設定：

   | 名稱 | 值 |
   |---|---|
   | `DATABASE_URL` | Postgres 附加元件自動產生，保留原值 |
   | `CRAWLER_CONTACT` | 你的聯絡 Email，會放在爬蟲 User-Agent |
   | `SYNC_SECONDS` | `300`（預設每5分鐘開始一輪；前輪較久時不重疊） |
   | `MAX_ARTICLES_PER_SOURCE` | `40`（選填） |

4. Deploy → Deployment method 選 GitHub，連接 repository，選分支 → Deploy Branch。需要時設定 Python buildpack `heroku/python`。
5. 部署的 release 階段會自動建資料表。部署成功後到 Resources，**同時啟用 `web` 和 `worker`，各1個**。web 用來顯示網站，worker 負責持續抓資料。持續更新需使用適合常駐的 dyno 方案；web、worker、Postgres 分別計費。
6. 按 Open App。首次同步可能需要數分鐘；下方「資料來源與同步狀態」會顯示結果。若沒有資訊，先看 worker Logs，而非反覆刷新。
7. 未來更新程式後重新 Deploy；不需要刪資料庫。此版 `create_all` 僅建立缺少的表，未來若修改既有欄位應加入資料庫 migration。

**注意：** 從 GitHub 手動部署不會自動套用 app.json 的 addons、env 或 formation，請確實執行上述步驟。app.json 是相容部署範本。程式不會替你開通任何付費資源。

## Heroku CLI（替代操作）

```bash
heroku addons:create heroku-postgresql:essential-0 -a YOUR_APP
heroku config:set CRAWLER_CONTACT=YOUR_EMAIL SYNC_SECONDS=300 -a YOUR_APP
heroku ps:scale web=1 worker=1 -a YOUR_APP
heroku logs --tail --dyno worker -a YOUR_APP
```

請將 YOUR_APP / YOUR_EMAIL 換成實際資料。若 App 已有 Postgres，不要再次新增。建立附加元件前依 Heroku 顯示確認費用與方案可用性。

## 首批來源

| ID | 單位 | 方式 | 收錄規則 |
|---|---|---|---|
| lingya-office | 苓雅區公所 | HTML | 區公所發布的公告 |
| lingya-health | 苓雅區衛生所 | HTML | 在地單位公告 |
| lingya-household | 苓雅戶政事務所 | HTML | 在地單位公告 |
| kaohsiung-city | 高雄市政府 | HTML | 文章內容提及苓雅或明確全市適用 |
| kaohsiung-travel | 高雄旅遊網 | 官方XML | 活動地址、內容提及苓雅或全市適用 |
| culture-events | 文化部藝文資料 | 官方JSON | 苓雅相關；目前 robots.txt 阻擋，未成功接入 |

高雄旅遊網原始 Website 欄位常為空白，已依官方活動 ID 對應官方 `event/calendardetail/<id>/` 頁面；7904及7952的對應已核對。來源欄位變動時仍需維護。

新增單位：編輯 `sources.json`，加入唯一 id、name、kind、url、scope、selectors、license_url、enabled。HTML adapter 支援目前常見 News_Content / CityNews_Detail 版型；其他版型需新增 adapter。`selectors` 是要追蹤的消息欄目連結文字。

## 同步與篩選

- 不同來源並行，同站序列請求，至少間隔1秒，另尊重 robots crawl-delay。
- 每輪讀取首頁及指定消息欄目，新文章立即抓內容；既有文章詳細頁快取30分鐘後重新驗證。API/feed支援 ETag / Last-Modified 條件請求。
- 5分鐘是目標輪詢間隔，不保證官方發布後5分鐘內一定收錄；網路延遲、來源限速、故障和來源自身延遲都會影響。
- 同來源按原文網址去重並更新；不同機關轉貼同一公告仍可能重複。本版沒有 AI 判讀，也沒有跨機關內容合併。
- `local`：苓雅機關發布，或正文/地點提及苓雅。`citywide`：正文提及高雄市民、全市等適用描述，是規則推定，實際資格以原文為準。
- 不使用政府網站頁尾地址來判斷活動位置。圖片海報、僅寫場館俗名、未寫行政區的活動可能漏收。後續可補場館地址字典與OCR。
- 文章移除不會自動刪除本地紀錄；活動改期或取消會在可解析的原文更新後重新擷取，無法保證即時辨識，請核對原文。
- 發布日期若來源缺少則顯示未提供，不拿抓取日期假冒發布日期。部分資料源只提供修改日期，需依來源欄位進一步區分。
- 目前顯示文字節錄與原文入口，不下載海報/圖片/附件。不代表來源所有素材均已授權；新增來源或擴大轉載前須檢查該站使用與資料授權條款。
- 抓取失敗保留既有資料，來源狀態會公開顯示。robots.txt 讀取失敗暫停該次來源；未繞過驗證或登入。

## API

這些是「苓雅通自行整合 API」，不是政府官方 API。

- `GET /api/news`：全部資訊，24筆一頁。
- `GET /api/news?q=親子&scope=local&category=活動課程&page=1`
- `GET /api/agencies/lingya-office/news`：各單位 API。
- `GET /api/sources`：來源與成功/失敗/部分成功狀態。
- `GET /health`：程式與資料庫健康檢查。

公開唯讀，沒有可被未登入使用者觸發的爬蟲或寫入 API。

## 本機啟動

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m flask --app app init-db
python app.py
# 另一個終端機：
python worker.py
```

瀏覽 http://127.0.0.1:5000 。本機未設定 DATABASE_URL 時使用 instance/ 下的 SQLite，不包含在部署包。

## 驗證

```bash
python -m unittest -v
# 僅同步一輪，方便檢查網路：
# Windows PowerShell: $env:SYNC_ONCE="1"; python worker.py
# macOS/Linux:
SYNC_ONCE=1 python worker.py
```

已驗證日期轉換、原始連結、苓雅判定、活動XML解析、API搜尋/篩選/分頁參數與首頁回應。實際連線驗證範圍及結果見 LIVE_CHECK.json。尚未在你的 Heroku 帳號完成部署，瀏覽器視覺驗證未執行。

## 官方參考

- https://lingya.kcg.gov.tw/cp.aspx?n=1AE5097C483D7DF8
- https://data.gov.tw/dataset/138185
- https://khh.travel/zh-tw/OpenData/EventNgisXML
- https://devcenter.heroku.com/articles/python-support
- https://devcenter.heroku.com/articles/github-integration
- https://devcenter.heroku.com/articles/heroku-postgresql
- https://devcenter.heroku.com/articles/dynos
