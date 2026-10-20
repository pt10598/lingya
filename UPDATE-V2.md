# 苓雅通 V2 更新說明

這次只提供苓雅通一站；沒有建立其他區網站、沒有替您新增Heroku App或開通付費服務。

## 這版增加什麼

- 全新首頁：消息總數、七日內已取得日期的活動數、在地資訊數。
- 保留來源單位直接點選、搜尋、範圍與分類篩選。
- 日期篩選：未來七天、本週末、進行中／即將開始、日期待確認、已結束。僅限已取得結構化日期的資料，海報內的日期仍可能漏收。
- 每則資訊有獨立網址，包含資料欄位、原文節錄與參加前檢查提醒，仍保留官方原文連結。
- 三篇本站實用指南：週末安排、補助公告閱讀、來源與時間判讀。內容是一般方法，不是人工採訪或在地實測報導。
- 關於、聯絡與更正、隱私權政策、資料來源說明。
- sitemap.xml、robots.txt、AdSense驗證meta及ads.txt支援。廣告功能預設關閉。

## 您目前的苓雅通如何更新

1. 把整包解壓後的程式檔覆蓋到原本GitHub repository的根目錄。這次不只三個前端檔案，新增的settings.py、guides.py與templates內容也要一起上傳。
2. 保留原Heroku App、Postgres、DATABASE_URL、CRAWLER_CONTACT與web／worker設定，不要刪資料庫。
3. Heroku → Deploy → Deploy Branch。release階段會建立缺少的表，不刪除既有資料；本版沿用原Item資料表格式及苓雅資料ID，無須手動修改資料表。
4. Open App，必要時Ctrl+F5。確認首頁新導覽、單位按鈕與生活指南頁正常。worker會依原設定繼續更新。
5. 聯絡頁預設公開信箱為irataieddie@gmail.com，營運者名稱為Eddie；可透過Config Vars的CONTACT_EMAIL、SITE_OPERATOR修改。

## AdSense設定：先申請，預設不載入廣告

沒有設定真實發布商ID時，不會載入Google廣告，也不會產生假的ads.txt。

| Config Var | 用途 |
|---|---|
| ADSENSE_CLIENT | 您的發布商ID，格式ca-pub-加16位數字 |
| ADSENSE_SLOT | 您建立的響應式展示廣告單元ID |
| ADSENSE_ENABLED | 預設0；完成審核及必要設定後才改為1 |

建議流程：

1. 在AdSense新增網站，填入Google接受的站點網址。如herokuapp子網域無法加入，需改用自己可驗證的正式網域；此母版不保證任何網址一定通過驗證。
2. 將真正的ADSENSE_CLIENT填入Heroku Config Vars。首頁會自動輸出Google帳戶meta驗證標記，/ads.txt會輸出相應發布商紀錄。ADSENSE_ENABLED仍保持0，不需要為驗證先載入廣告。
3. 依Google後台完成網站驗證及申請審核。本站有指南和資料整理功能，但不保證審核通過；單純大量複製相同內容的分區網站仍可能不符合政策。
4. 完成隱私與訊息設定。若向歐洲經濟區、英國、瑞士使用者放送個人化廣告，依Google政策使用其認證CMP；本版沒有自行實作或假冒CMP。請在AdSense後台完成適用的Google同意管理設定，必要時再依其指示加入訊息程式碼。
5. 建立響應式展示廣告單元，填ADSENSE_SLOT。網站就緒並完成適用政策設定後，才將ADSENSE_ENABLED設成1。
6. 本版僅在生活指南文章底部放一個有「廣告」標示的手動版位；首頁、搜尋結果、公告節錄、聯絡及隱私頁不主動載入廣告腳本。建議保持自動廣告關閉，避免Google在其他頁面另插版位；真實展示結果由Google帳戶與審核狀態決定。

Google官方：
- https://support.google.com/adsense/answer/12169212?hl=zh-Hant
- https://support.google.com/adsense/answer/13554116?hl=zh-Hant
- https://support.google.com/publisherpolicies/answer/11190248

## 未來分區各自部署

本次沒有建立其他區，也沒有加入其他區公所來源。往後由這份母版複製：

- 每一區建立獨立Heroku App、自己的Postgres資料庫、web與worker。
- 修改SITE_NAME、DISTRICT_NAME、DISTRICT_KEYWORDS，以及sources.json中該區實際可用且授權適當的來源。
- 不要只改網站名稱，仍指向苓雅區的資料庫與機關。請勿在已有苓雅資料的同一資料庫改成另一區，此架構依「每站獨立資料庫」隔離資料，不是多租戶平台。
- 不同區應補充自己的在地內容、活動與服務價值。共用外觀不代表可以用同樣內容大量複製並保證通過AdSense。
- 各站分別設定網域、聯絡、來源、授權與廣告審核。另站新增也會有自己的Heroku運作費用。

## 測試與限制

11項測試驗證搜尋、日期篩選、網址、資料保留、頁面回應、Google驗證與廣告開關；JavaScript語法檢查通過。本版爬蟲核心來源不變，沒有新增尚未驗證的其他區來源。

本次瀏覽器無法連到本機預覽環境（connection refused），因此未完成瀏覽器視覺驗證；已以Flask測試用戶端檢查各頁與API。本包不含測試資料或本機資料庫。尚未替您更新Heroku，需自行重新部署。

文化部來源仍依robots與連線狀態處理，本版未繞過限制。資料授權及商業利用詢問尚待機關回覆；增加政策頁不等於取得官方同意或律師審核。
