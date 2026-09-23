# SmartDisplayRPI

Raspberry Pi 4 + HDMI 螢幕的智慧相框／家庭資訊看板，由 Mac mini 上的 ChatGPT Work／Codex 協助管理，透過同一區域網路的 Wi-Fi + SSH 部署與控制。

**版本：v0.1 原型。已提供可執行程式與部署步驟；尚未在 George 的 Mac / Pi 硬體或 Google 帳號實測。**

## 先從這裡開始

1. [完整施工與操作教學](docs/SETUP.md)：硬體、燒錄、SSH、Mac、Google 日曆、照片與部署。
2. [系統架構與分期驗收](docs/ARCHITECTURE.md)：分工、限制、後續功能。
3. [給 Mac 上 AI Agent 的施工指令](docs/AGENT_PROMPT.md)：在實際連得上 Pi 的 Mac 執行。
4. [Google 整合方案與官方資料](docs/GOOGLE.md)。

## 第一版功能狀態

| 功能 | 狀態 |
|---|---|
| 本機照片輪播、時鐘、留言、未來七日行程 | 已實作 |
| 相框／日曆／混合／黑畫面模式 | 已實作；黑畫面不等於 HDMI 電源關閉 |
| Mac → Pi SSH / rsync 完整快照部署 | 已實作；原子切換、保留前版 |
| Raspberry Pi OS Desktop / labwc kiosk | 安裝腳本已提供，待硬體驗證 |
| Google Calendar 多日曆 OAuth 唯讀同步 | 已實作，需本人授權與帳號驗證 |
| Google 相簿下載照片後匯入 | 可用，本機 JPG/PNG/WebP |
| Google Photos Picker 選取匯入 | 設計完成，API connector 待 v0.2 |
| Google 相簿新增照片自動追蹤 | 第一版不支援；Ambient API 需合作夥伴資格 |
| ChatGPT 自然語言管理 | 透過 Mac 本機 Agent 操作 CLI；不是常駐聊天 API |
| 語音、HDMI 關閉、天氣、觸控、無人值守 AI | 後續規劃 |

## 不需要 Google 帳號的本機試跑

需要 Python 3.10+。在 repo 根目錄：

```bash
python3 smartdisplay.py init
python3 smartdisplay.py import-photos /你的照片目錄
python3 smartdisplay.py set --mode dashboard --message '歡迎回家' --interval 20
python3 smartdisplay.py build
python3 smartdisplay.py serve
```

瀏覽器開啟 http://127.0.0.1:8765 。修改資料後重新 `build`；網頁每 10 秒讀取設定。

## 專案結構

```text
smartdisplay.py          Mac CLI + Pi 本機 HTTP server
web/index.html           不依賴 CDN 的顯示頁
scripts/install-pi.sh    Pi systemd 使用者服務 + labwc 自啟動
scripts/kiosk.sh         Chromium 全螢幕與重啟
requirements.txt        Mac Google Calendar 選用依賴
AGENTS.md               Agent 的操作邊界
config/ssh.example      Mac SSH 設定範本
docs/                   安裝、設計、Google、Agent prompt
tests/                  離線播放部署的核心測試
data/                   本機照片與行程快取，不提交
secrets/                Google OAuth 憑證，不提交
runtime/                顯示快照，不提交
```

預設時區 Asia/Taipei，橫向 1080p、照片完整顯示。可用 `set --fit cover` 改為裁切填滿。

安全設計：Pi HTTP 只監聽 localhost；Google OAuth 留在 Mac；不開放 HTTP shell endpoint。照片與行程不因顯示而自動送给 AI，只有你交給 Agent 的內容才會進入其工作流程。
