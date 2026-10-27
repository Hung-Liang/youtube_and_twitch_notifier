import html
import json
import os
import random
from pathlib import Path

import requests
from dotenv import load_dotenv

from libs.handler.telegram_handler import TelegramHandler
from libs.handler.twitch_handler import TwitchHandler
from libs.handler.youtube_handler import YoutubeHandler
from libs.utils.file_path import IGNORE_PATH, LOG_PATH
from libs.utils.logger import get_log_filename, log

load_dotenv()

TELEGRAM_ADMIN_ID = os.environ.get("telegram_admin_id")

TELEGRAM_MESSAGE_LIMIT = 4096

# Max maxResults for playlistItems and max IDs per videos request
YOUTUBE_MAX_RESULTS = 50

# playlistItems costs 1 unit for up to 50 items, so check them all
YOUTUBE_CHECK_RANGE = YOUTUBE_MAX_RESULTS

YOUTUBE_VIDEO_PARTS = "snippet,liveStreamingDetails"

# Upload and member-only playlists share one ignore file, and entries are
# trimmed in write order, so keep a buffer over the 2 x 50 checked videos
IGNORE_MAX_SIZE = 200
IGNORE_KEEP_SIZE = 150


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
    # Write to a temp file then swap, so a crash never leaves a broken file
    tmp_path = Path(f"{path}.tmp")
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


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

    log("[main]", e)

    log("=" * 80)
    log("=" * 80)

    # Upload failure must not abort the caller's notification job
    try:
        TelegramHandler().send_message(
            TELEGRAM_ADMIN_ID, format_exception_message(e)
        )
    except requests.RequestException as err:
        log("[main]", f"Send exception log failed: {err!r}")


def format_exception_message(e):
    """Format an exception as a Telegram HTML message within size limit.

    Args:
        `e`: Exception

    Returns:
        A Telegram HTML message
    """
    header = "<b>[Exception]</b>\n"
    text = str(e)

    # Keep the tail, where a traceback shows the actual error
    while True:
        body = html.escape(text, quote=False)
        if len(header) + len(body) + len("<pre></pre>") <= (
            TELEGRAM_MESSAGE_LIMIT
        ):
            return f"{header}<pre>{body}</pre>"
        text = "...\n" + text[-(len(text) * 9 // 10):]


def get_upload_id(channel_id):
    """Get Upload Playlist ID from Select Channel

    Args:
        `channel_id`: Channel ID

    Returns:
        A Upload Playlist ID of Select Channel
    """
    # The UC -> UU mapping is not officially documented, but saves an API call
    if channel_id.startswith("UC"):
        return "UU" + channel_id[2:]

    log("[main]", f"Invalid channel id: {channel_id}")
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
        list: (Live Title, URL, Channel Title, Mark Notified) per video;
            call Mark Notified after sending to skip it next time.
    """
    playlists, video_info_cache, _ = fetch_playlists(upload_ids, group)

    results = []
    seen_urls = set()

    for playlist in playlists:
        playlist_results = get_playlist_results(
            playlist, video_info_cache, broadcast_types, group
        )

        # Ignore files are only updated after sending, so a video found in
        # both the upload and member-only playlists must be deduped here
        for result in playlist_results:
            if result[1] not in seen_urls:
                seen_urls.add(result[1])
                results.append(result)

    return results


def get_ignore_json(group, channel_id):
    """Get the ignore json path of a channel, shared by its playlists.

    Args:
        `group`: Group
        `channel_id`: Channel ID

    Returns:
        Ignore Json Path
    """
    group_path = Path(IGNORE_PATH, group)
    group_path.mkdir(parents=True, exist_ok=True)
    return Path(group_path, f"{channel_id}.json")


def fetch_playlists(upload_ids, group):
    """Fetch recent videos of each playlist, then look up the ones not
    ignored yet in shared batches.

    Args:
        `upload_ids`: Upload Playlist IDs keyed by channel key
        `group`: Group

    Returns:
        (playlists, video_info_cache, gone_ids); `video_ids` of a playlist
        holds its videos not ignored yet, or None if the playlist request
        failed.
    """
    playlists = []

    for channel_key, upload_id in upload_ids.items():
        # Check if this is a member-only playlist
        is_member_only = channel_key.endswith("_member")

        # Extract the original channel_id (remove _member suffix if present)
        channel_id = channel_key[:-7] if is_member_only else channel_key

        ignore_json = get_ignore_json(group, channel_id)
        ignore_list = load_ignore_json(ignore_json)

        videos = YoutubeHandler().find_recent_video(
            upload_id, max_results=YOUTUBE_CHECK_RANGE
        )
        if not videos:
            log("[main]", f"No videos found for upload_id: {upload_id}")

        video_ids = None
        if videos is not None:
            video_ids = [
                video["contentDetails"]["videoId"]
                for video in videos
                if video["contentDetails"]["videoId"] not in ignore_list
            ]

        playlists.append(
            {
                "upload_id": upload_id,
                "channel_id": channel_id,
                "is_member_only": is_member_only,
                "ignore_json": ignore_json,
                "video_ids": video_ids,
            }
        )

    # A video can be in both the upload and member-only playlists
    video_ids = list(
        dict.fromkeys(
            video_id
            for playlist in playlists
            for video_id in playlist["video_ids"] or []
        )
    )
    video_info_cache = {}
    gone_ids = fetch_video_info(video_ids, video_info_cache)

    return playlists, video_info_cache, gone_ids


def fetch_video_info(video_ids, video_info_cache):
    """Fetch video info into the cache, batched to save quota.

    Args:
        `video_ids`: Video IDs to fetch.
        `video_info_cache`: Video info keyed by ID, updated in place.

    Returns:
        IDs a successful response left out, e.g. deleted or private videos.
    """
    gone_ids = set()

    for start in range(0, len(video_ids), YOUTUBE_MAX_RESULTS):
        chunk = video_ids[start:start + YOUTUBE_MAX_RESULTS]
        video_info = YoutubeHandler().get_video_info(
            ",".join(chunk), part=YOUTUBE_VIDEO_PARTS
        )
        # A failed request says nothing about whether the videos still exist
        if video_info is None:
            continue

        for item in video_info.get("items", []):
            video_info_cache[item["id"]] = item
        gone_ids.update(
            video_id for video_id in chunk if video_id not in video_info_cache
        )

    return gone_ids


def get_playlist_results(playlist, video_info_cache, broadcast_types, group):
    """Sort the new videos of one playlist by broadcast status.

    Upcoming videos are left out of the ignore json, so they are checked
    again until they go live or leave the checked range. Unwanted videos
    are ignored right away so they are not looked up again.

    Args:
        `playlist`: A playlist from `fetch_playlists`
        `video_info_cache`: Video info keyed by ID
        `broadcast_types`: Broadcast Types
        `group`: Group

    Returns:
        list: (Live Title, URL, Channel Title, Mark Notified) per video
    """
    results = []
    skipped = {}

    for video_id in playlist["video_ids"] or []:
        # Private or scheduled videos may become public later
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
            log(
                "[upcoming]",
                f"{group} / {playlist['channel_id']} / {video_id}"
                f" / {snippet['title']}",
            )
            continue

        if broadcast_status not in broadcast_types:
            skipped[video_id] = "[skip] " + snippet["title"]
            continue

        live_title = snippet["title"]

        if playlist["is_member_only"]:
            live_title = "【Member Only】\n" + live_title

        channel_title = snippet["channelTitle"]
        url = f"https://www.youtube.com/watch?v={video_id}"

        results.append(
            (
                live_title,
                url,
                channel_title,
                make_mark_notified(
                    playlist["ignore_json"], video_id, live_title
                ),
            )
        )

    if skipped:
        add_ignore_entries(playlist["ignore_json"], skipped)

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

        url = f"https://www.twitch.tv/{channel_title}"

        results.append(
            (
                live_title,
                url,
                user_name,
                make_mark_notified(ignore_json, stream_id, live_title),
            )
        )

    return results


def load_ignore_json(json_path):
    """Load Ignore Json

    Returns:
        A Ignore Json
    """

    if not Path(json_path).exists():
        create_empty_json(json_path)

    ignore_list = load_json(json_path)

    if len(ignore_list) > IGNORE_MAX_SIZE:
        ignore_list = dict(list(ignore_list.items())[-IGNORE_KEEP_SIZE:])

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


def add_ignore_entries(json_path, entries):
    """Merge entries into the ignore json.

    Args:
        `json_path`: Ignore Json Path
        `entries`: Titles keyed by Video ID or Stream ID
    """
    ignore_list = load_ignore_json(json_path)
    ignore_list.update(entries)
    save_json(json_path, ignore_list)


def make_mark_notified(json_path, key, value):
    """Build a callback that records `key` in the ignore json.

    Args:
        `json_path`: Ignore Json Path
        `key`: Video ID or Stream ID
        `value`: Title
    """

    def mark_notified():
        update_ignore_json(json_path, load_ignore_json(json_path), key, value)

    return mark_notified


def create_empty_json(json_path):
    """Create Empty Json

    Args:
        `json_path`: Json Path
    """
    if not Path(json_path).exists():
        save_json(json_path, {})
