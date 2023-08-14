import os

from dotenv import load_dotenv

from lib.handler.discord_handler import DiscordHandler
from lib.handler.telegram_handler import TelegramHandler
from lib.utils.file_path import NOTIFIED_JSON_PATH
from lib.utils.logger import log
from lib.utils.tools import (
    get_message,
    get_title_and_video_id,
    load_json,
    write_json,
)

load_dotenv()


def send_notify(info):
    channel_id = os.environ.get("telegram_channel_id")

    id_list = []

    if info and len(info["items"]) > 0:
        title, video_id = get_title_and_video_id(info)

        url = "https://www.youtube.com/watch?v={}".format(video_id)

        telegram_message, discord_message = get_message(title, url)

        log("[main]", "Telegram Message: ", telegram_message)
        log("[main]", "Discord Message: ", discord_message)

        data = load_json(NOTIFIED_JSON_PATH)

        if video_id not in data:
            data[video_id] = title
            write_json(NOTIFIED_JSON_PATH, data)

            for cid in id_list:
                TelegramHandler().send_message(cid, telegram_message)

            # TelegramHandler().send_message(channel_id, telegram_message)

            DiscordHandler().send_message(discord_message)

        else:
            log("[main]", "Already notified.")
