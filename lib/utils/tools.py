import json
import os
from pathlib import Path
from time import time

from dotenv import load_dotenv

from lib.handler.telegram_handler import TelegramHandler
from lib.handler.youtube_handler import YoutubeHandler
from lib.utils.file_path import LOG_PATH, UPLOAD_PLAYLIST_JSON_PATH
from lib.utils.logger import log

load_dotenv()


def load_json(path):
    """Load Json from Select File

    Args:
        `path`: File path
        `file_name`: File name

    Returns:
        A Json Object of Select File
    """
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return data


def write_json(path, data):
    """Write Json to Select File

    Args:
        `path`: File path
        `data`: Json data
    """
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_message(title, url):
    telegram_message = (
        "<b>軍團長開台啦！！！</b>\n<a href='{}'><b>{}</b></a>".format(url, title)
    )

    discord_message = "@everyone\n軍團長開台啦！！！\n\n[{}]({})".format(title, url)

    return telegram_message, discord_message


def get_title_and_video_id(info):
    title = info["items"][0]["snippet"]["title"]
    video_id = info["items"][0]["id"]["videoId"]
    return title, video_id


def send_daily_log():
    if time() % 86400 <= 10:
        telegram_admin_id = os.environ.get("telegram_admin_id")

        filenames = os.listdir(LOG_PATH)

        for filename in filenames:
            log_path = Path(LOG_PATH, filename)
            TelegramHandler().send_document(
                telegram_admin_id, log_path, "[Daily Log] " + filename
            )
            log_path.unlink()


def send_exception_log(e):
    telegram_admin_id = os.environ.get("telegram_admin_id")

    filename = log("[main]", e)

    log_path = Path(LOG_PATH, filename)
    TelegramHandler().send_document(
        telegram_admin_id, log_path, "[Exception] " + filename
    )


def get_upload_id(channel_id):
    upload_playlist = load_json(UPLOAD_PLAYLIST_JSON_PATH)

    if channel_id in upload_playlist:
        return upload_playlist[channel_id]
    else:
        upload_id = YoutubeHandler().get_upload_playlist_id(channel_id)

        if upload_id:
            upload_playlist[channel_id] = upload_id
            write_json(UPLOAD_PLAYLIST_JSON_PATH, upload_playlist)
            return upload_id
        else:
            return None
