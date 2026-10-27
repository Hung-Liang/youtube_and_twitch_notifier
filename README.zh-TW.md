# YouTube 和 Twitch 通知系統

🌍 **語言:** [English](README.md) | [台灣繁體中文](README.zh-TW.md)

## 描述

- 這是一個專案，當 YouTube 頻道或 Twitch 主播開始直播時，會通知您。  
- 也會在 YouTube 頻道上傳新影片時通知您。  

## 如何使用

1. 在 `config` 資料夾中建立 `config.py` 檔案（可複製 `config/config.example.py`）。  
2. 本地測試時，用相同格式建立 `config/dev_config.py`，並在 `.env` 設定 `APP_ENV="dev"`。  
3. 在 config 檔案中加入以下程式碼：  

```python
youtube_groups = {
    "group1": {
        "interval": 3,
        "channel_ids": [],
        "broadcast_types": ["none", "live"],
        "notifier_types": {
            "telegram": {
                "recipient_ids": [],
                "word_list": [],
            },
            "discord": {
                "webhook_urls": [],
                "word_list": [],
            },
        },
    },
}

twitch_groups = {
    "group1": {
        "interval": 3,
        "channel_ids": [],
        "notifier_types": {
            "telegram": {
                "recipient_ids": [],
                "word_list": [],
            },
            "discord": {
                "webhook_urls": [],
                "word_list": [],
            },
        },
    },
}
```

### 配置說明

- `youtube_groups` 和 `twitch_groups` 可分別新增多個 `group`（群組）。  
- 每個群組內可新增多個 `channel_ids`（頻道 ID）。  
- `broadcast_types` 只有Youtube會使用到這個參數，可設定 `live`、`upcoming` 和 `none`。  
  - `live`：直播中。  
  - `upcoming`：即將開播。不會發通知，待機台開播後會以 `live` 通知。  
  - `none`：一般上船影片 or 結束直播的影片。
- `notifier_types`（通知類型）可設定 Telegram 和 Discord。  
- `recipient_ids` 和 `webhook_urls` 可設定多個接收者或 Webhook 連結。  
- `word_list` 為隨機選取的字詞，會顯示在通知訊息開頭。  
  - 若 `word_list` 為空，則開頭將顯示直播頻道名稱。  
- `interval` 指每次檢查的間隔時間（以分鐘計算）。  
  - 建議設定能整除 60 的數值（如 1、2、3、5、10），否則檢查間隔會不平均。  
- 執行 `python main.py --check-config` 可只檢查 config，不啟動服務。  
- 啟動時會檢查 config：缺少或錯誤的設定會讓服務無法啟動；`interval` 無法整除 60、`broadcast_types` 為空或包含 `upcoming` 只會記錄警告。  

## 設定 `.env` 檔案

1. 在專案根目錄建立 `.env` 檔案。  
2. 在 `.env` 檔案中加入以下內容：  

```env
telegram_admin_id=""

bot_token=""
youtube_api_token=""

twitch_client_id=""
twitch_client_secret=""

APP_ENV=""
```

### 參數說明

- `telegram_admin_id`：您的 Telegram ID。  
- `bot_token`：您的 Telegram 機器人 Token。  
- `youtube_api_token`：您的 YouTube API Token。  
- `twitch_client_id` 和 `twitch_client_secret`：Twitch API 的 Client ID 和 Client Secret。  
- `APP_ENV`：設為 `dev` 時讀取 `config/dev_config.py`，其他值則讀取 `config/config.py`。  

## 如何運行

1. 安裝 Python。  
2. 執行 `pip install -r requirements.txt` 安裝相依套件。  
3. 執行 `main.py` 啟動程式。  

## 運作方式

- 啟動時，每個群組會把當下看得到的內容視為已通知：YouTube 每個 playlist 最新 50 部影片（upcoming 除外），以及 Twitch 正在直播的台。  
  - 只會通知服務運行期間開台或上架的內容；停機期間錯過的不會補發。  
  - 啟動時的檢查失敗會通知 admin 一次，該群組之後每一輪會重試，成功前不會發送該 playlist 或群組的通知。  
- 每一輪檢查 YouTube 每個 playlist 最新 50 部影片，同一個群組的影片會一起查詢，每 50 部一個 request。  
- 已通知和略過的 ID 存在 `asset/ignore/{group}/{channel}.json`。這個資料夾可以是空的，搬機器時不用一起搬。  

## 使用 Docker 運行

- 把 `.env` 放在專案根目錄、`config.py` 放在 `config` 資料夾，然後執行 `scripts/deploy.sh`。  
  - 腳本會先把目前的 image 標記為 `chu_yt_notification:prev`，再 build 新 image、檢查 config，最後重啟容器。  
- `config/`、`asset/`、`log/` 都從主機 mount 進容器，重新 build 也不會遺失。新主機上的 `asset/` 可以是空的。  
- 修改 config 後執行 `docker compose restart notifier`。  
- 回滾：`docker tag chu_yt_notification:prev chu_yt_notification:latest && docker compose up -d`。  

## 如何獲取頻道 ID

### YouTube 頻道 ID

1. 前往要追蹤的 YouTube 頻道。  
2. 點擊「分享」按鈕。  
3. 選擇「複製頻道 ID」。  

### Twitch 頻道 ID

1. 前往要追蹤的 Twitch 頻道。  
2. 頻道 ID 位於網址 `twitch.tv/` 之後的部分。  

## 執行測試

- 測試使用本機的 [uv](https://docs.astral.sh/uv/) 虛擬環境，Python 版本為 3.12，與 Docker image 相同。

```bash
uv venv --python 3.12
uv pip install -r requirements-dev.txt
uv run pytest
```

## 支持我

<a href="https://www.buymeacoffee.com/hungliang" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>
