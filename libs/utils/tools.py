import html
import json
import os
import random
import threading
from pathlib import Path

import requests
from dotenv import load_dotenv

from libs.handler.telegram_handler import TelegramHandler
from libs.handler.twitch_handler import TwitchHandler
from libs.handler.youtube_handler import YoutubeHandler
from libs.utils.file_path import (
    IGNORE_PATH,
    LOG_PATH,
    UPLOAD_PLAYLIST_JSON_PATH,
)
from libs.utils.logger import get_log_filename, log

load_dotenv()

TELEGRAM_ADMIN_ID = os.environ.get("telegram_admin_id")

UPLOAD_PLAYLIST_LOCK = threading.Lock()


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
        random_word = html.escape(random_word, quote=False)
        title = html.escape(title, quote=False)
        message = "<b>{}\n{}\n{}</b>".format(random_word, title, url)
    elif notifier_type == "discord":
        message = "{}\n\n[{}]({})".format(random_word, title, url)
    else:
        raise ValueError(f"Unknown notifier_type: {notifier_type}")

    return message


def send_service_start_notification():
    """Send Service Start Notification to Telegram Admin"""

    message = "🚀 <b>Service Started</b>"

    TelegramHandler().send_message(TELEGRAM_ADMIN_ID, message)


def send_daily_log():
    """Send Daily Log to Telegram Admin"""

    filenames = sorted(os.listdir(LOG_PATH))
    current_filename = get_log_filename()

    for filename in filenames:
        # Other jobs may still be writing to today's log
        if filename == current_filename:
            continue

        log_path = Path(LOG_PATH, filename)
        sent, _ = TelegramHandler().send_document(
            TELEGRAM_ADMIN_ID, log_path, "[Daily Log] " + filename
        )

        # Keep the file so it will be retried on the next run
        if sent:
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
    # Upload failure must not abort the caller's notification job
    try:
        TelegramHandler().send_document(
            TELEGRAM_ADMIN_ID, log_path, "[Exception] " + filename
        )
    except requests.RequestException as err:
        log("[main]", f"Send exception log failed: {err!r}")


def get_upload_id(channel_id):
    """Get Upload Playlist ID from Select Channel

    Args:
        `channel_id`: Channel ID

    Returns:
        A Upload Playlist ID of Select Channel
    """
    # Jobs run in a thread pool and may read/write this file at once
    with UPLOAD_PLAYLIST_LOCK:
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


def get_member_only_id(channel_id):
    """Get Member-Only Playlist ID from Select Channel

    Args:
        `channel_id`: Channel ID

    Returns:
        A Member-Only Playlist ID of Select Channel
    """
    return YoutubeHandler().get_member_only_playlist_id(channel_id)


def get_multiple_upload_id(channel_ids, include_member_only=False):
    """Get Multiple Upload Playlist ID from Select Channels

    Args:
        `channel_ids`: Channel IDs
        `include_member_only`: Whether to include member-only playlists

    Returns:
        A Multiple Upload Playlist ID of Select Channels
    """
    upload_ids = {}

    for channel_id in channel_ids:
        # Get regular upload playlist
        upload_id = get_upload_id(channel_id)
        if upload_id:
            upload_ids[channel_id] = upload_id

        # Get member-only playlist if requested
        if include_member_only:
            member_only_id = get_member_only_id(channel_id)
            if member_only_id:
                upload_ids[f"{channel_id}_member"] = member_only_id

    return upload_ids


def get_multiple_live_title_and_url(upload_ids, broadcast_types, group):
    """Get Multiple Live Title, URL, and Channel Title from Select Channels

    Args:
        `upload_ids`: Upload Playlist IDs
        `broadcast_types`: Broadcast Types
        `group`: Group

    Returns:
        A Multiple Live Title, URL, and Channel Title from Select Channels
    """
    results = []

    for channel_key, upload_id in upload_ids.items():
        # Check if this is a member-only playlist
        is_member_only = channel_key.endswith("_member")

        # Extract the original channel_id (remove _member suffix if present)
        original_channel_id = (
            channel_key[:-7] if is_member_only else channel_key
        )

        live_title_and_url = get_live_title_and_url(
            upload_id,
            group,
            broadcast_types,
            3,
            is_member_only,
            original_channel_id,
        )

        if live_title_and_url:
            results.extend(live_title_and_url)

    return results


def get_live_title_and_url(
    upload_id,
    group,
    broadcast_types=["none", "live"],
    max_results=3,
    is_member_only=False,
    channel_id=None,
    video_info_cache=None,
):
    """Get Live Title, URL, and Channel Title from the selected channel.

    Args:
        upload_id (str): Upload Playlist ID of the selected channel.
        group (str): Group name.
        broadcast_types (list): Broadcast types to check.
        max_results (int): Maximum results to fetch.
        is_member_only (bool): Whether this is a member-only playlist.
        channel_id (str): Original channel ID for shared ignore tracking.
        video_info_cache (dict): Video info already fetched, keyed by ID.

    Returns:
        tuple: (Live Title, URL, Channel Title) if live,
            else (None, None, None).
    """
    videos = YoutubeHandler().find_recent_video(
        upload_id, max_results=max_results
    )
    if not videos:
        log("[main]", f"No videos found for upload_id: {upload_id}")
        return []
    video_ids = [video["contentDetails"]["videoId"] for video in videos]

    group_path = Path(IGNORE_PATH, group)
    group_path.mkdir(parents=True, exist_ok=True)

    if channel_id:
        ignore_json = Path(group_path, f"{channel_id}.json")
    else:
        ignore_json = Path(group_path, f"{upload_id}.json")

    ignore_list = load_ignore_json(ignore_json)

    if video_info_cache is None:
        video_info_cache = {}

    # Fetch all uncached videos in one request to save quota
    missing_ids = [
        video_id
        for video_id in video_ids
        if video_id not in ignore_list and video_id not in video_info_cache
    ]
    if missing_ids:
        video_info = YoutubeHandler().get_video_info(",".join(missing_ids))
        for item in (video_info or {}).get("items", []):
            video_info_cache[item["id"]] = item

    results = []

    upcoming = 0

    for video_id in video_ids:
        if video_id in ignore_list:
            continue

        if video_id not in video_info_cache:
            log("[main]", f"No video info found for video_id: {video_id}")
            continue

        snippet = video_info_cache[video_id]["snippet"]
        broadcast_status = snippet.get("liveBroadcastContent", "")
        log(
            "[main]",
            f"video_id: {video_id}, broadcast_status: {broadcast_status}",
        )

        if broadcast_status == "upcoming":
            upcoming += 1
            continue

        if broadcast_status in broadcast_types:
            live_title = snippet["title"]

            if is_member_only:
                live_title = "【Member Only】\n" + live_title

            channel_title = snippet["channelTitle"]
            url = f"https://www.youtube.com/watch?v={video_id}"

            update_ignore_json(ignore_json, ignore_list, video_id, live_title)
            results.append((live_title, url, channel_title))

    if upcoming == max_results:
        log("[main]", "All videos are upcoming")
        return get_live_title_and_url(
            upload_id,
            group,
            broadcast_types,
            max_results + 3,
            is_member_only,
            channel_id,
            video_info_cache,
        )

    return results


def get_multiple_twitch_title_and_url(channel_ids, group):
    """Get Multiple Live Title, URL, and Channel Title from Select Channels

    Args:
        `channel_ids`: Channel IDs
        `group`: Group

    Returns:
        A Multiple Live Title, URL, and Channel Title from Select Channels
    """
    # Helix returns top live streams when user_login is omitted
    if not channel_ids:
        return []

    stream_infos = TwitchHandler().get_stream_infos(channel_ids)

    if not stream_infos:
        return []

    results = []

    group_path = Path(IGNORE_PATH, group)
    group_path.mkdir(parents=True, exist_ok=True)

    for stream_info in stream_infos:
        live_title = stream_info['title']
        stream_id = stream_info['stream_id']
        channel_title = stream_info['user_login']
        user_name = stream_info['user_name']

        ignore_json = Path(group_path, f"{channel_title}.json")
        ignore_list = load_ignore_json(ignore_json)

        if stream_id in ignore_list:
            continue

        update_ignore_json(ignore_json, ignore_list, stream_id, live_title)

        url = f"https://www.twitch.tv/{channel_title}"

        results.append((live_title, url, user_name))

    return results


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


def create_empty_json(json_path):
    """Create Empty Json

    Args:
        `json_path`: Json Path
    """
    if not Path(json_path).exists():
        save_json(json_path, {})
