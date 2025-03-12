import json
import os
import random
from pathlib import Path

from dotenv import load_dotenv

from libs.handler.telegram_handler import TelegramHandler
from libs.handler.twitch_handler import TwitchHandler
from libs.handler.youtube_handler import YoutubeHandler
from libs.utils.file_path import (
    IGNORE_PATH,
    LOG_PATH,
    UPLOAD_PLAYLIST_JSON_PATH,
)
from libs.utils.logger import log

load_dotenv()

TELEGRAM_ADMIN_ID = os.environ.get("telegram_admin_id")


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


def get_message(notifier_type, title, url, channel_title, word_list):
    """Get Message from Select Title, URL and Channel Title

    Args:
        `title`: Live Title
        `url`: Live URL
        `channel_title`: Channel Title

    Returns:
        A Message of Select Title, URL and Channel Title
    """
    if len(word_list) > 0:
        random_word = random.choice(word_list)
    else:
        random_word = channel_title

    if notifier_type == "telegram":
        message = "<b>{}\n{}\n{}</b>".format(random_word, title, url)
    elif notifier_type == "discord":
        message = "@everyone\n{}\n\n[{}]({})".format(random_word, title, url)

    return message


def send_daily_log():
    """Send Daily Log to Telegram Admin"""

    filenames = os.listdir(LOG_PATH)

    for filename in filenames:
        log_path = Path(LOG_PATH, filename)
        TelegramHandler().send_document(
            TELEGRAM_ADMIN_ID, log_path, "[Daily Log] " + filename
        )
        log_path.unlink()


def send_exception_log(e):
    """Send Exception Log to Telegram Admin

    Args:
        `e`: Exception
    """
    log("=" * 80)
    log("=" * 80)

    filename = log("[main]", e, return_filename=True)

    log("=" * 80)
    log("=" * 80)

    log_path = Path(LOG_PATH, filename)
    TelegramHandler().send_document(
        TELEGRAM_ADMIN_ID, log_path, "[Exception] " + filename
    )


def get_upload_id(channel_id):
    """Get Upload Playlist ID from Select Channel

    Args:
        `channel_id`: Channel ID

    Returns:
        A Upload Playlist ID of Select Channel
    """
    if not Path(UPLOAD_PLAYLIST_JSON_PATH).exists():
        save_json(UPLOAD_PLAYLIST_JSON_PATH, {})

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


def get_live_title_and_url(
    upload_id, group, broadcast_types=["none", "live"], max_results=3
):
    """Get Live Title, URL, and Channel Title from the selected channel.

    Args:
        upload_id (str): Upload Playlist ID of the selected channel.

    Returns:
        tuple: (Live Title, URL, Channel Title) if live,
            else (None, None, None).
    """
    videos = YoutubeHandler().find_recent_video(
        upload_id, max_results=max_results
    )
    video_ids = [video["contentDetails"]["videoId"] for video in videos]

    group_path = Path(IGNORE_PATH, group)
    group_path.mkdir(parents=True, exist_ok=True)

    ignore_json = Path(group_path, f"{upload_id}.json")

    ignore_list = load_ignore_json(ignore_json)

    results = []

    upcoming = 0

    for video_id in video_ids:
        if video_id in ignore_list:
            continue

        video_info = YoutubeHandler().get_video_info(video_id)
        snippet = video_info["items"][0]["snippet"]
        broadcast_status = snippet.get("liveBroadcastContent", "")
        log("[main]", f"video_id: {video_id}")
        log("[main]", f"broadcast_status: {broadcast_status}")

        if broadcast_status == "upcoming":
            upcoming += 1
            continue

        if broadcast_status in broadcast_types:
            live_title = replace_html_sensitive_symbols(snippet["title"])
            channel_title = replace_html_sensitive_symbols(
                snippet["channelTitle"]
            )
            url = f"https://www.youtube.com/watch?v={video_id}"

            update_ignore_json(ignore_json, ignore_list, video_id, live_title)
            results.append((live_title, url, channel_title))

    if upcoming == max_results:
        log("[main]", "All videos are upcoming")
        return get_live_title_and_url(
            upload_id, broadcast_types, max_results + 3
        )

    return results


def get_twitch_title_and_url(channel_id, group):
    """Get Live Title, URL, and Channel Title from the selected channel.

    Args:
        channel_id (str): Channel ID
        group (str): Group

    Returns:
        tuple: (Live Title, URL, Channel Title) if live,
            else (None, None, None)
    """
    stream_info = TwitchHandler().get_stream_info(channel_id)
    if not stream_info['is_live']:
        return None, None, None

    group_path = Path(IGNORE_PATH, group)
    group_path.mkdir(parents=True, exist_ok=True)

    ignore_json = Path(group_path, f"{channel_id}.json")

    ignore_list = load_ignore_json(ignore_json)
    live_title = replace_html_sensitive_symbols(stream_info['title'])

    if ignore_list.get(channel_id) == live_title:
        return None, None, None

    update_ignore_json(ignore_json, ignore_list, channel_id, live_title)
    return live_title, f"https://www.twitch.tv/{channel_id}", channel_id


def load_ignore_json(json_path):
    """Load Ignore Json

    Returns:
        A Ignore Json
    """

    if not Path(json_path).exists():
        create_empty_json(json_path)

    ignore_list = load_json(json_path)

    if len(ignore_list) > 100:
        ignore_list = dict(list(ignore_list.items())[-50:] or ignore_list)

    return ignore_list


def update_ignore_json(json_path, ignore_list, key, value):
    """Update Ignore Json

    Args:
        `ignore_list`: Ignore List
        `key`: Key
        `value`: Value
    """
    ignore_list[key] = value
    save_json(json_path, ignore_list)


def replace_html_sensitive_symbols(text):
    """Remove HTML Sensitive Symbols from Select Text

    Args:
        text: The input text to be sanitized.

    Returns:
        str: Text without HTML sensitive symbols.
    """
    replacements = {
        '%': '%25',
        '&': '%26',
        '+': '%2B',
        '#': '%23',
        '>': '%3E',
        '=': '%3D',
        '<': '%26lt;',
        '"': '%22',
        "'": '%27',
        '/': '%2F',
        '(': '%28',
        ')': '%29',
        '{': '%7B',
        '}': '%7D',
        '[': '%5B',
        ']': '%5D',
        '|': '%7C',
    }

    for symbol, replacement in replacements.items():
        text = text.replace(symbol, replacement)

    return text


def create_empty_json(json_path):
    """Create Empty Json

    Args:
        `json_path`: Json Path
    """
    if not Path(json_path).exists():
        save_json(json_path, {})
