# CDC AI Agent (疾管署新聞監控機器人)

這是一個自動化 AI 代理程式，能定期抓取台灣衛生福利部疾病管制署 (CDC) 的會議紀錄或重點新聞稿 (PDF格式)，透過 Google Gemini AI 進行重點摘要，並自動發送 Email 通知。

## 目錄結構
- `main.py`: 爬蟲、AI 摘要與 Email 寄送的主程式。
- `requirements.txt`: Python 依賴套件。
- `history.json` (執行後產生): 紀錄已經成功發送過的新聞網址。
- `.github/workflows/schedule.yml`: GitHub Actions 每日定時執行的部署檔。

---

## 🚀 步驟一：本地端測試 (Local Testing)

1. **準備環境變數**：
   將目錄下的 `.env.example` 複製一份並命名為 `.env`（或是直接在終端機中設定環境變數）：
   ```bash
   export GEMINI_API_KEY="你的_Gemini_API_Key"
   export GMAIL_USER="你的_Gmail_信箱@gmail.com"
   export GMAIL_PASSWORD="你的_Gmail_應用程式專用密碼"
   export EMAIL_RECIPIENT="收件者信箱"
   ```

2. **安裝套件與執行**：
   ```bash
   cd ~/Desktop/cdc_ai_agent
   source venv/bin/activate
   python main.py
   ```
   *如果看到 Terminal 印出「Sending email...」並在信箱收到信，代表測試成功！*
   *注意：測試成功後，程式會建立 `history.json` 記住這些新聞。若想重新測試發送同一篇，只需打開 `history.json` 清空裡面的內容（變成 `[]`）即可。*

---

## ☁️ 步驟二：雲端部署 (GitHub Actions)

因為已經寫好 `.github/workflows/schedule.yml`，您只需要將這個資料夾推送到您個人的 GitHub 即可達成「每天早上 8 點自動執行」：

1. 到 GitHub 網站上建立一個全新的 Repository (例如命名為 `cdc-ai-agent`)。
2. 在您的本機終端機執行：
   ```bash
   cd ~/Desktop/cdc_ai_agent
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/您的帳號/cdc-ai-agent.git
   git push -u origin main
   ```
3. **設定 GitHub Secrets (非常重要)**：
   到該 GitHub Repository 的 `Settings` -> `Secrets and variables` -> `Actions`。
   點擊 `New repository secret`，依序把以下四個環境變數加進去：
   - `GEMINI_API_KEY`
   - `GMAIL_USER`
   - `GMAIL_PASSWORD`
   - `EMAIL_RECIPIENT`

4. 設定完成後，GitHub 每天早上 8 點 (台灣時間) 就會自動幫您跑這個程式囉！您也可以在 GitHub 的 `Actions` 頁籤手動點擊 `Run workflow` 測試。
