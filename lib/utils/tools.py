import json
import os
import random
from pathlib import Path
from time import time

from dotenv import load_dotenv

from lib.config import group_id_1, group_id_2, group_id_3
from lib.handler.telegram_handler import TelegramHandler
from lib.handler.youtube_handler import YoutubeHandler
from lib.utils.file_path import (
    IGNORE_JSON_PATH,
    LOG_PATH,
    UPLOAD_PLAYLIST_JSON_PATH,
)
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


def save_json(path, data):
    """Save Json to Select File

    Args:
        `path`: File path
        `data`: Json data
    """
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_message(title, url, channel_title, group):
    """Get Message from Select Title, URL and Channel Title

    Args:
        `title`: Live Title
        `url`: Live URL
        `channel_title`: Channel Title

    Returns:
        A Message of Select Title, URL and Channel Title
    """
    # word_list = ["軍團長開台啦！！！", "快點進來看我",
    # "今天想要做一點有趣的！", "開開開開開開台！", "來這邊，這邊好玩！"]
    if group == "group_1":
        word_list = ["時辰已到！", "休息時間！"]
    else:
        word_list = [channel_title]

    random_word = random.choice(word_list)

    # telegram_message = "<b>{}</b>\n<a href='{}'><b>{}</b></a>".format(
    #     random_word, url, title
    # )
    telegram_message = "<b>{}\n{}\n{}</b>".format(random_word, title, url)

    discord_message = "@everyone\n{}\n\n[{}]({})".format(
        random_word, title, url
    )

    return telegram_message, discord_message


def send_daily_log():
    """Send Daily Log to Telegram Admin"""
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
    """Send Exception Log to Telegram Admin

    Args:
        `e`: Exception
    """
    telegram_admin_id = os.environ.get("telegram_admin_id")

    filename = log("[main]", e, return_filename=True)

    log_path = Path(LOG_PATH, filename)
    TelegramHandler().send_document(
        telegram_admin_id, log_path, "[Exception] " + filename
    )


def get_upload_id(channel_id):
    """Get Upload Playlist ID from Select Channel

    Args:
        `channel_id`: Channel ID

    Returns:
        A Upload Playlist ID of Select Channel
    """
    upload_playlist = load_json(UPLOAD_PLAYLIST_JSON_PATH)

    if channel_id in upload_playlist:
        return upload_playlist[channel_id]
    else:
        upload_id = YoutubeHandler().get_upload_playlist_id(channel_id)

        if upload_id:
            upload_playlist[channel_id] = upload_id
            save_json(UPLOAD_PLAYLIST_JSON_PATH, upload_playlist)
            return upload_id
        else:
            return None


def get_live_title_and_url(upload_id):
    """Get Live Title, URL and Channel Title from Select Channel

    Args:
        `upload_id`: Upload Playlist ID of Select Channel

    Returns:
        A Live Title, URL and Channel Title of Select Channel
    """
    videos = YoutubeHandler().find_recent_video(upload_id)

    videos_ids = [video["contentDetails"]["videoId"] for video in videos]

    ignore_list = load_json(IGNORE_JSON_PATH)

    if len(ignore_list) > 100:
        ignore_list = dict(list(ignore_list.items())[-50:] or ignore_list)

    title = None
    url = None
    channel_title = None

    for video_id in videos_ids:
        if video_id not in ignore_list:
            video_info = YoutubeHandler().get_video_info(video_id)

            if (
                video_info["items"][0]["snippet"]["liveBroadcastContent"]
                == "upcoming"
            ):
                continue

            if (
                video_info["items"][0]["snippet"]["liveBroadcastContent"]
                == "live"
            ):
                title = video_info["items"][0]["snippet"]["title"]
                url = "https://www.youtube.com/watch?v={}".format(video_id)
                channel_title = video_info["items"][0]["snippet"][
                    "channelTitle"
                ]

                title = replace_html_sensitive_symbols(title)
                channel_title = replace_html_sensitive_symbols(channel_title)

            ignore_list[video_id] = video_info["items"][0]["snippet"]["title"]
            save_json(IGNORE_JSON_PATH, ignore_list)

    return title, url, channel_title


def get_id_list(group):
    """Get ID List from Select Group

    Args:
        `group`: Group name

    Returns:
        A ID List of Select Group
    """
    if group == "group_1":
        id_list = group_id_1  # mine, chu, chu telegram channel

    elif group == "group_2":
        id_list = group_id_2  # mine, tata

    elif group == "group_3":
        id_list = group_id_3  # mine

    return id_list


def replace_html_sensitive_symbols(text):
    """Remove HTML Sensitive Symbols from Select Text

    Args:
        `text`: Text

    Returns:
        A Text without HTML Sensitive Symbols
    """
    text = (
        text.replace('%', '%25')
        .replace('&', '%26')
        .replace('+', '%2B')
        .replace('#', '%23')
        .replace('>', '%3E')
        .replace('=', '%3D')
        .replace('<', '%26lt;')
    )

    return text


def find_raw_content_by_user_id(owner_id, plurks):
    """Find raw content by user id

    Args:
        `owner_id`: User id.
        `plurks`: Plurk results.

    Returns:
        Raw content list.
    """

    raw_contents = []
    for plurk in plurks:
        if plurk["owner_id"] == int(owner_id):
            raw_contents.append(plurk["content_raw"])

    return raw_contents
