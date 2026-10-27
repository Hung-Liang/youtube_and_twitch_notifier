# youtube_and_twitch_notification

🌍 **Languages:** [English](README.md) | [台灣繁體中文](README.zh-TW.md)

## Description

- This is a project that will notify you when a youtube channel or twitch streamer goes live.
- It will also notify you when a new video is uploaded to a youtube channel.

## How to use

- First you need to create a file called `config.py` in the `config` folder (copy `config/config.example.py`).
- For local testing, create `config/dev_config.py` with the same format and set `APP_ENV="dev"` in `.env`.
- In the config file you need to add the following code:

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

- You can add as many groups under `youtube_groups` and `twitch_groups` as you want.
- You can add as many `channel_ids` as you want under each group.
- `broadcast_types` is only used for youtube, you can set it to `live`, `upcoming` or `none`.
  - `live`: live stream.
  - `upcoming`: upcoming stream. It is never notified; a waiting room is notified as `live` once it starts.
  - `none`: normal video or ended stream.
- You can add as many `recipient_ids` and `webhook_urls` as you want under each notifier type.
- You can add as many `word_list` as you want under each notifier type.
  - word_list is a list of words will randomly be selected and added to the top of the message.
  - if the word_list is empty, the top of the message will be stream channel name.
- `interval` is the time in minutes between each check.
  - Use a value that divides 60 (e.g. 1, 2, 3, 5, 10), otherwise polling gaps will be uneven.
- Run `python main.py --check-config` to validate the config without starting the service.
- The config is checked at startup: missing or invalid settings stop the service, and an uneven `interval`, empty `broadcast_types` or `upcoming` in `broadcast_types` only logs a warning.

## Env file

- You need to create a `.env` file in the root folder.
- In the `.env` file you need to add the following code:

```env
telegram_admin_id=""

bot_token=""
youtube_api_token=""

twitch_client_id=""
twitch_client_secret=""

APP_ENV=""
```

- `telegram_admin_id` is your telegram id.
- `bot_token` is the token of your telegram bot.
- `youtube_api_token` is the token of your youtube api.
- `twitch_client_id` and `twitch_client_secret` are the client id and client secret of your twitch api.
- `APP_ENV` set to `dev` loads `config/dev_config.py`, any other value loads `config/config.py`.

## How to run

- You need to have python installed.
- You need to install the requirements by running `pip install -r requirements.txt`.
- You need to run the `main.py` file.

## How it works

- On startup, every group records what it shows now as already notified: the latest 50 videos of each youtube playlist except upcoming ones, and the twitch streams that are live.
  - Only streams and videos that start or appear while the service is running are notified; anything missed during downtime is skipped.
  - If a startup check fails, the admin is alerted once and the group retries it on its next runs, sending nothing for that playlist or group until it succeeds.
- Each run checks the latest 50 videos of every youtube playlist; videos of a group are looked up together, 50 per request.
- Notified and skipped ids are kept in `asset/ignore/{group}/{channel}.json`. The folder is optional: starting with an empty one is safe, so it does not need to move with the deployment.

## Run with Docker

- Put `.env` in the root folder and `config.py` in the `config` folder, then run `scripts/deploy.sh`.
  - It tags the current image as `chu_yt_notification:prev`, builds a new one, checks the config, and restarts the container.
- `config/`, `asset/` and `log/` are mounted from the host, so they survive rebuilds. `asset/` can start empty on a new host.
- After changing the config, run `docker compose restart notifier`.
- Rollback: `docker tag chu_yt_notification:prev chu_yt_notification:latest && docker compose up -d`.

## How to get channel id

- Go to the youtube channel you want to get the id of.
  - Click on the share button.
  - Choose to copy channel id.

- Go to the twitch channel you want to get the id of.
  - The id is in the url after `twitch.tv/`.

## Todo

- [ ] Add more notifier types.
- [x] ~~Issue when a channel id in config in different group will cause second group to not work.~~

## Running tests

- Tests run in a local [uv](https://docs.astral.sh/uv/) virtual environment on Python 3.12, the same version as the Docker image.

```bash
uv venv --python 3.12
uv pip install -r requirements-dev.txt
uv run pytest
```

## Support me

<a href="https://www.buymeacoffee.com/hungliang" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>
