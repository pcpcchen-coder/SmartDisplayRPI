# SmartDisplayRPI agent instructions

- 回覆與操作文件使用繁體中文。先讀 README.md 與 docs/SETUP.md。
- Mac 執行控制程式；Pi 執行本機顯示；OpenAI 模型推論在雲端。
- 不得把 ChatGPT 登入 token 當作一般 OpenAI API key，或建立未經支援的 OAuth proxy。
- 先檢查 SSH、OS、桌面、路徑、服務與 git 狀態，再進行部署。
- 控制優先用 smartdisplay.py set / deploy，禁止將照片 EXIF、檔名、行程文字或模型回應拼成 shell 指令。
- Google OAuth secrets、token、Wi-Fi 密碼、私人照片、日曆資料不得提交或印出。
- SSH host key 必須驗證；不要用 StrictHostKeyChecking=no，不自動更改使用者既有 SSH 設定。
- 不自動 sudo reboot、關機、刪除照片或清空 releases。一般 set / deploy / status 可依使用者指令執行。
- deploy 只發布 data 與 web；不會部署 Python 原始碼。更新程式需先檢查遠端工作目錄，再 git pull --ff-only 並重啟服務。
- 每次交付區分：本地測試通過／Google 實帳號通過／實機驗收通過。沒有測試不得宣稱通過。
