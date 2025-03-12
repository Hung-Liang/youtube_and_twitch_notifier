# youtube_and_twitch_notification

🌍 **Languages:** [English](README.md) | [台灣繁體中文](README.zh-TW.md)

## Description

- This is a project that will notify you when a youtube channel or twitch streamer goes live.
- It will also notify you when a new video is uploaded to a youtube channel.

## How to use

- First you need to create a file called `config.py` in the `libs` folder.
- In the `config.py` file you need to add the following code:

```python
youtube_groups = {
    "group1": {
        "interval": 3,
        "channel_ids": [],
        "broadcast_types": [],
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
  - `upcoming`: upcoming stream.
  - `none`: normal video or ended stream.
- You can add as many `recipient_ids` and `webhook_urls` as you want under each notifier type.
- You can add as many `word_list` as you want under each notifier type.
  - word_list is a list of words will randomly be selected and added to the top of the message.
  - if the word_list is empty, the top of the message will be stream channel name.
- `interval` is the time in minutes between each check.

## Env file

- You need to create a `.env` file in the root folder.
- In the `.env` file you need to add the following code:

```env
telegram_admin_id=""

bot_token=""
youtube_api_token=""

twitch_client_id=""
twitch_client_secret=""
```

- `telegram_admin_id` is your telegram id.
- `bot_token` is the token of your telegram bot.
- `youtube_api_token` is the token of your youtube api.
- `twitch_client_id` and `twitch_client_secret` are the client id and client secret of your twitch api.

## How to run

- You need to have python installed.
- You need to install the requirements by running `pip install -r requirements.txt`.
- You need to run the `main.py` file.

## How to get channel id

- Go to the youtube channel you want to get the id of.
  - Click on the share button.
  - Choose to copy channel id.

- Go to the twitch channel you want to get the id of.
  - The id is in the url after `twitch.tv/`.

## Todo

- Add more notifier types.
- Issue when a channel id in config in different group will cause second group to not work.

## Support me

<a href="https://www.buymeacoffee.com/hungliang" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>
