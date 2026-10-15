# Windows 語音輸入小工具

點一下 Caps Lock 開始說話，再點一下停止，自動把**潤飾過的繁體中文**貼到目前游標位置。
適合寫公文、寫信、打字很慢或想少打字的人。全部用免費額度，**只需要一把 Groq 金鑰**。

- 語音辨識：Groq Whisper（`whisper-large-v3-turbo`，免費額度每日約 2000 次請求）
- 語意潤飾：Groq LLM（預設 `openai/gpt-oss-20b`，補標點、修語病與同音錯字）
- 錄音時右上角會跳出音量條，綠色條會跟著聲音跳 ＝ 有收到聲音

## ⚠️ 隱私說明（請先閱讀）
**錄下來的聲音與辨識出的文字都會傳送到 Groq 的雲端伺服器處理。**
請不要用來口述含學生姓名、身分證號、病歷、IEP 等個資的內容。
要處理敏感內容，請改用離線方案（例如本機安裝的 faster-whisper）。

## 安裝
1. 申請免費金鑰（約 5 分鐘）：到 https://console.groq.com 註冊 → 左側 **API Keys** → **Create API Key**，複製 `gsk_...` 開頭那串。
2. 安裝與設定：
```powershell
pip install -r requirements.txt
copy .env.example .env
# 用記事本開啟 .env，把金鑰貼到 GROQ_API_KEY= 後面存檔
# 或執行 python set_key.py，會跳出視窗讓你貼上（金鑰不會顯示在畫面上）
```

## 使用
```powershell
$env:PYTHONUTF8="1"
python voice_input.py                          # 常駐：點一下 Caps Lock 開始，再點一下停止並貼上
python voice_input.py --once --enter-mode      # 備用：用 Enter 取代熱鍵（熱鍵沒反應時用）
python voice_input.py --wav 錄音.wav --no-paste  # 測試：辨識指定音檔，只印文字
python voice_input.py --once --no-polish --no-paste  # 測試：跳過潤飾與貼上
python voice_input.py --mics                   # 列出麥克風裝置編號
```

### 設定（.env）
| 變數 | 說明 |
|---|---|
| `GROQ_API_KEY` | 你的 Groq 金鑰（必填） |
| `POLISH_MODEL` | 潤飾用模型，中文品質不滿意可換 `qwen/qwen3-32b` 等 |
| `VOICE_MODE` | `tap`（預設，點一下開始／再點停止）或 `hold`（按住說話、放開停止） |
| `VOICE_HOTKEY` | 熱鍵，預設 `caps lock` |
| `VOICE_DEVICE` | 麥克風編號，空白＝系統預設；音量條不動時先用 `--mics` 查編號 |
| `VOICE_MAX_SECONDS` | 單次最長錄音秒數，預設 120 |

### 開機自動啟動（可選）
按 `Win+R` 輸入 `shell:startup`，在資料夾放 `語音輸入.bat`：
```bat
cd /d <你放這個專案的資料夾>
python voice_input.py
```

## 注意事項
- **程式執行期間，Caps Lock 被保留給錄音使用**（不會再切換大小寫）；要打英文大寫請先 `Ctrl+C` 關掉程式。
- Whisper 對中文標點較弱，靠 Groq 潤飾補上；人名、地名等專有名詞第一次要人工校對。
- 音量條完全不動：先確認 Windows 右下角喇叭的輸入裝置，再用 `--mics` 查編號填進 `.env`。
- 跑 `.py` 即可，不包成 exe（避免防毒誤報）。
- 金鑰只放 `.env`，**不要上傳 GitHub**（`.gitignore` 已擋住）。
