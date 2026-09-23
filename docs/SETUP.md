# 從零施工與操作

## 0. 準備清單

| 項目 | 規格／用途 |
|---|---|
| Raspberry Pi 4 | 使用現有設備即可；1080p 相片與網頁看板為第一階段 |
| 電源 | Pi 4 適用 USB-C 5.1V / 3A，避免螢幕 USB 供電不足 |
| microSD | 建議 32GB 以上耐寫卡；大量照片另用 USB SSD |
| HDMI 螢幕 | 先用既有 1080p HDMI 螢幕；確認斷電恢復後會自動開機 |
| micro-HDMI → HDMI 線 | Pi 4 接近 USB-C 的 HDMI0 接頭優先 |
| 散熱外殼 | 長時間運轉用散熱片／風扇，保留通風 |
| 暫用鍵盤滑鼠 | 首次桌面設定、確認畫面用 |
| Mac mini | Google 授權、照片資料源、Agent 與 SSH 控制端 |
| Wi-Fi | 同網段且關閉 AP client isolation；能用 5GHz 就先用 5GHz |

螢幕不必有觸控、相機、麥克風。第一版先完成穩定顯示，再加語音。

## 1. Pi OS 與網路

1. Raspberry Pi Imager 選 Raspberry Pi 4、**Raspberry Pi OS 64-bit Desktop**（不是 Lite）。燒錄會清除選定卡片，請確認卡片。
2. 自訂 hostname `smartdisplay`、帳號 `display`（也可自訂）、Wi-Fi SSID／密碼、時區 Asia/Taipei；啟用 SSH，優先配置公鑰。
3. 啟動 Pi、接螢幕。在路由器為 Pi 設 DHCP reservation；無需手改固定 IP。
4. 在 Pi 的 `sudo raspi-config` 設定 Desktop Auto Login、關閉 Screen Blanking。以實際版本選單名稱為準。
5. 確認桌面 compositor 是 labwc，`ls /etc/xdg/labwc`；其他桌面不套用本安裝腳本。

## 2. Mac SSH

```bash
ssh-keygen -t ed25519 -f ~/.ssh/smartdisplay_ed25519
```

若該 key 已存在不要覆寫。可用 passphrase 加 macOS ssh-agent；背景同步前確認 agent 可使用。

第一次先在 Pi 本機確認 host key：

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Mac 首次連線 `ssh display@smartdisplay.local`，核對指紋後接受。若 Imager 尚未放入 key，手動把 Mac `.pub` 那一行加入 Pi `~/.ssh/authorized_keys`；目錄權限 700、檔案 600。**私鑰留在 Mac。**

將 `config/ssh.example` 合併到 Mac `~/.ssh/config`，修改 User。測試：

```bash
ssh -o BatchMode=yes smartdisplay 'hostname; uname -m'
```

mDNS 無法解析時，將 HostName 改成路由器分配的 Pi IP。不要關閉 host key 檢查。

## 3. Pi 安裝

在 Pi 執行：

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/pcpcchen-coder/SmartDisplayRPI.git ~/SmartDisplayRPI
cd ~/SmartDisplayRPI
bash scripts/install-pi.sh
```

完成 Desktop Auto Login 後，手動重新開機。安裝腳本不主動 reboot。

確認：

```bash
systemctl --user status smartdisplay --no-pager
curl -f http://127.0.0.1:8765/state.json
journalctl --user -u smartdisplay -n 50 --no-pager
```

服務使用 `systemd --user`，桌面登入時啟動。labwc autostart 只新增一行，保留既有設定。

## 4. Mac 程式準備

使用 Python 3.10+；若沒有，安裝 python.org 的 macOS Python 3。然後：

```bash
git clone https://github.com/pcpcchen-coder/SmartDisplayRPI.git ~/SmartDisplayRPI
cd ~/SmartDisplayRPI
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python smartdisplay.py init
```

Mac 必須有 `ssh`、`rsync`。第一版只用相片不需要安裝 Google 套件。

## 5. 照片先跑起來

在 Google Photos 網站選擇自己要顯示的照片，下載並解壓縮到本機專用資料夾，例如 `~/Pictures/SmartDisplayImport`。這是手動匯入，不是持續同步相簿。

```bash
python smartdisplay.py import-photos ~/Pictures/SmartDisplayImport
python smartdisplay.py set --mode dashboard --interval 20 --fit contain
python smartdisplay.py deploy --host smartdisplay
```

支援 JPG、JPEG、PNG、WebP；HEIC/RAW 請先在 Mac 預覽程式匯出 JPEG。v0.1 不處理影片、Live Photo 或 EXIF 自動分類；建議先用 20–100 張 1920×1080～2560×1440 級別照片驗收，避免大量原圖佔滿 SD。匯入會複製、以 SHA256 去重，不改原始照片。

Pi 每 10 秒讀取設定，新照片最晚在下一個更新／輪播週期出現。

## 6. Google Calendar

1. Google Cloud 建立個人專案，啟用 Google Calendar API。
2. 設定 OAuth consent screen；測試模式加入自己的 Google 帳號為 test user。
3. 建立 **Desktop app** OAuth client，下載 JSON，存為 Mac repo 的 `secrets/google-client.json`。不要放進 web 或 data。
4. 在 Mac 的互動桌面 terminal 執行：

```bash
python smartdisplay.py calendar
python smartdisplay.py deploy
```

第一次瀏覽器跳出 Google 授權，只讀取行程。多日曆：

```bash
python smartdisplay.py calendar --calendar-id primary --calendar-id 'YOUR_FAMILY_CALENDAR_ID'
python smartdisplay.py deploy
```

日曆 ID 從 Google Calendar 設定／整合日曆取得。所有行程先合併顯示，最多呈現接下來 5 筆；時間範圍為同步當下起七天。取消事件不顯示、全天事件不做 UTC 轉換、end.date 是不含結束日。同步任一日曆失敗會保留舊快取，不發布半套更新。

OAuth Testing 模式可能需要重新授權；以 Google Cloud 當時政策與 consent screen 狀態為準。若 refresh 失敗，先備份並移走 `secrets/calendar-token.json`，再互動授權；不要把 token 貼給 Agent。

## 7. 平常怎麼用

你對 Mac 上 Agent 說：「小克，把智慧相框改為全螢幕相片，每 30 秒一張。」Agent 可執行：

```bash
python smartdisplay.py set --mode photos --interval 30
python smartdisplay.py deploy
```

顯示日曆／留言／黑畫面：

```bash
python smartdisplay.py set --mode calendar
python smartdisplay.py set --mode dashboard --message '今晚七點吃飯'
python smartdisplay.py set --mode blank
```

每次完成設定後執行 `deploy`。`blank` 只是黑色網頁，不保證背光熄滅或節電。真正關螢幕待確認 Wayland output、螢幕 DDC/CI/CEC 能力再做，不預設使用舊版 `tvservice`。

## 8. 自動刷新與 Mac 休眠

第一版預設手動同步，先用真實帳號跑通。在 Mac 排程工具／launchd 建立每 300 秒呼叫的工作，命令使用絕對路徑：

```text
/Users/YOUR_USER/SmartDisplayRPI/.venv/bin/python /Users/YOUR_USER/SmartDisplayRPI/smartdisplay.py calendar
/Users/YOUR_USER/SmartDisplayRPI/.venv/bin/python /Users/YOUR_USER/SmartDisplayRPI/smartdisplay.py deploy
```

第二個命令僅在第一個成功後執行；同時只允許一個同步工作（launchd 同一 job 不重疊啟動）。多日曆需帶上相同 IDs。排程不呼叫 AI，無每五分鐘的模型成本。排程安裝與 Mac 防睡眠設置留到实機連線階段；repo 目前沒有自動建立排程。

Mac 休眠：Pi 繼續播放快取照片／時鐘；過期日曆事件會移除、更新時間保留。新行程與 AI 指令等 Mac 恢復後才更新。

## 9. 更新、回滾、排錯

- `deploy` 只傳網頁與資料快照，**不會更新遠端 Python / scripts**。
- 更新程式：確認 Pi git 沒有使用者修改後，在 Pi `git pull --ff-only`，再 `systemctl --user restart smartdisplay`。
- 檢查快照：`ssh smartdisplay 'ls -lt ~/SmartDisplayRPI/runtime/releases'`。
- 回滾：在 Pi repo 目錄執行 `python3 scripts/rollback-pi.py RELEASE_NAME`（從上面的清單選一個已驗證版本），會驗證照片並原子切換；不要覆寫某個已發布 release 內的檔案。網頁十秒內重新讀取。
- 照片刪除：本版本保留舊快照；從 Mac data 刪除並重新建立照片清單後發布，舊 release 仍含照片。真正刪除須同時清除相關 Mac / Pi 快照與備份，先確認使用者要刪哪些。v0.2 增加 prune 與刪除介面。
- 黑畫面：查電源、HDMI0、desktop autologin、labwc autostart、服務及 Chromium。
- stale：查 Mac 是否睡眠、Google OAuth、SSH key、Wi-Fi隔離。
- 遠端檢視用 SSH tunnel：`ssh -N -L 8766:127.0.0.1:8765 smartdisplay`，Mac 開 http://127.0.0.1:8766 。不要將 8765 開放到 LAN／Internet。
- 多次大量部署會累积完整照片快照；v0.1 刻意不自動刪，需人工管理容量。設定階段不要排程大量照片部署。

## 10. 驗收清單

- [ ] Pi 斷電重開後，在桌面自動登入後 60 秒內進入相框。
- [ ] 20 張照片連播一小時，無停止或失敗提示；方向／比例符合需求。
- [ ] Mac 發布新留言與模式後 15 秒內生效。
- [ ] 停掉 Mac / Wi-Fi 30 分鐘，Pi 照片與時鐘不中斷。
- [ ] Google 多日曆、跨午夜、全天、取消、重複事件符合原 Calendar。
- [ ] Pi 與 web 公開目錄沒有 OAuth token；外部無法直接連 8765。
- [ ] 部署中途 SSH 中斷仍保留前版；回滾一次成功。
- [ ] 24 小時燒機，檢查溫度、欠壓、SD 容量與 service logs。

這些是實機驗收工作，不代表本次已通過。
