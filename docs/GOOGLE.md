# Google 串接決策（查核 2026-09-23）

## 相簿方案比較

| 方案 | 對本專案的用途 | 限制／決定 |
|---|---|---|
| 網站下載 → 本機匯入 | 今天就能跑起來 | 手動更新；v0.1 採用 |
| Google Photos Picker API | 在 Google 官方頁面挑選照片後由 Mac 下載 | 每次加入新照片需使用者選取；v0.2 目標 |
| Library API | 管理應用程式建立的內容 | 2025-03-31 後權限變更，不能當成任意既有全相簿讀取方案 |
| Ambient API | 原生智慧相框／ambient slideshow | 需先獲准加入 Partner Program；DIY 不保證取得資格 |
| 非官方相簿爬蟲／複製 cookies | 本案不採用 | 易受登入、網頁變動影響，不作長期維護基礎 |

Picker 不是「選定相簿後永久追蹤更新」。baseUrl 是短效連結，官方文件描述有效期 60 分鐘且可能因撤權提早失效，不能永久塞進 Pi 輪播清單。下載需帶 bearer token，由 Mac 完成，Pi 只拿已匯入的圖檔。

## v0.2 Picker connector 實作規格（尚未實作）

1. Google Cloud 啟用 Photos Picker API；另存 `secrets/photos-token.json`，scope `https://www.googleapis.com/auth/photospicker.mediaitems.readonly`。
2. Mac 建立 session（POST `https://photospicker.googleapis.com/v1/sessions`）。
3. 將回傳 pickerUri 開在本人瀏覽器／提供 QR code，本人挑照片；不代替本人選取或輸入 Google 密碼。
4. 依每次回傳 pollingConfig 的 pollInterval / timeoutIn 等待；超時、取消、session 失效須可重新開始，不能無限緊密輪詢。
5. mediaItemsSet=true 後 GET `/v1/mediaItems?sessionId=...`，處理 nextPageToken 直到完成。
6. 使用 `mediaFile.baseUrl` 加 `=w2560-h1440`，OAuth bearer header 下載；依 MIME 解碼與轉為 JPEG，修正方向、移除不需要的 EXIF、以內容雜湊去重。
7. 先驗證 HTTP status、content type、檔案大小／磁碟空間，下載至暫存再原子移入。失敗重試有上限，401/403 要重新授權，429/5xx 用退避；不得把 token 或短效 URL 印進 log。
8. 整批完成後更新 manifest、清理 session、部署。未完成批次不取代現有相片清單。
9. 新增「匯入的照片」管理：來源、選取日期、刪除、磁碟限制、Mac/Pi/備份一併清除的選項。長期保存與再散布須遵守當時 Photos API policy 及使用者同意。
10. 驗收：超過一頁、取消、逾時、token 失效、非圖片、損壞檔、磁碟滿、100 張下載、重複匯入、刪除與斷線恢復。

不把尚未完成的 Picker 程式列為可用功能。

## Calendar v0.1

使用 Calendar API + Desktop OAuth，唯讀 scope `calendar.readonly`。token 僅留 Mac，Pi 拿必要 title / start / end。支援明確指定多個 calendar ID；不修改日曆、不發邀請。事件用 singleEvents 展開 recurring instances；取消事件排除，全天日期保留 date。

首次授權互動在 Mac 進行；後續 refresh 可重用 token。Google consent screen 設定與測試模式可能影響長期 refresh；無人值守部署前需實帳號連續驗收。

## 官方參考

- [Photos API 更新](https://developers.google.com/photos/support/updates)
- [Picker 流程](https://developers.google.com/photos/picker/guides/get-started-picker)
- [Picker 媒體下載與 baseUrl](https://developers.google.com/photos/picker/guides/media-items)
- [Ambient API 與合作夥伴資格](https://developers.google.com/photos/partner-program/overview)
- [Google Calendar Python quickstart](https://developers.google.com/workspace/calendar/api/quickstart/python)
- [Raspberry Pi 官方 kiosk 教學](https://www.raspberrypi.com/tutorials/how-to-use-a-raspberry-pi-in-kiosk-mode/)
- [OpenAI 官方登入方式](https://learn.chatgpt.com/docs/auth)

OpenAI 官方支援本機 Codex 使用 ChatGPT 登入或 API key；這不表示本專案可以把 ChatGPT session 轉成任意 REST API。第一版採互動 Agent 控制；程式化服務另用正式支援的身份驗證與計費方式。
