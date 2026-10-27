import json
import os
import random
import threading
from datetime import datetime

import pytz
import requests
from dotenv import load_dotenv

from libs.utils.logger import log

load_dotenv()

REQUEST_TIMEOUT = 10

# YouTube daily quota resets at midnight Pacific Time
QUOTA_TIMEZONE = pytz.timezone("America/Los_Angeles")
QUOTA_ERROR_REASONS = ("quotaExceeded", "dailyLimitExceeded")

# Shared across instances: key -> quota day it ran out
_exhausted_keys = {}
_quota_alert_day = None
_quota_lock = threading.Lock()


def get_quota_day():
    return datetime.now(QUOTA_TIMEZONE).date()


def is_quota_exceeded(res):
    if res.status_code != 403:
        return False
    try:
        errors = res.json().get("error", {}).get("errors", [])
    except ValueError:
        return False
    return any(error.get("reason") in QUOTA_ERROR_REASONS for error in errors)


def is_playlist_not_found(res):
    if res.status_code != 404:
        return False
    try:
        errors = res.json().get("error", {}).get("errors", [])
    except ValueError:
        return False
    return any(error.get("reason") == "playlistNotFound" for error in errors)


class YoutubeHandler:
    """Youtube Handler

    Attributes:
        `tokens`: Youtube api 3 Tokens.
    """

    def __init__(self):
        # self.token = os.environ.get("youtube_api_token")
        tokens = os.environ.get("youtube_api_token")
        if not tokens:
            raise ValueError("youtube_api_token is not set in .env")

        # Random order spreads usage across keys
        self.tokens = tokens.split(",")
        random.shuffle(self.tokens)

    def request(self, url):
        """GET from Youtube, switching keys when a key runs out of quota.

        Args:
            `url`: Request url without api key.

        Returns:
            The last response, or None on a network error.
        """
        global _quota_alert_day

        today = get_quota_day()
        with _quota_lock:
            tokens = [
                token
                for token in self.tokens
                if _exhausted_keys.get(token) != today
            ]
        # Every key ran out earlier today, try them again in case of reset
        if not tokens:
            tokens = self.tokens

        for index, token in enumerate(tokens):
            # Pass the key via header so it never appears in URLs or tracebacks
            try:
                res = requests.get(
                    url,
                    headers={"X-goog-api-key": token},
                    timeout=REQUEST_TIMEOUT,
                )
            # Network errors are usually transient, so callers treat this as
            # a failed request and retry next run instead of failing the job
            except requests.RequestException as err:
                log('[youtube_lib]', f'request failed: {err!r}')
                return None
            if not is_quota_exceeded(res):
                return res

            with _quota_lock:
                _exhausted_keys[token] = today
            log(
                '[youtube_lib]',
                f'api key quota exceeded, {len(tokens) - index - 1} left',
            )

        with _quota_lock:
            should_alert = _quota_alert_day != today
            _quota_alert_day = today

        if should_alert:
            # Imported here to avoid a circular import with tools
            from libs.utils.tools import send_exception_log

            send_exception_log(
                "[youtube_lib] All youtube api keys are out of quota"
            )

        return res

    def get_member_only_playlist_id(self, channel_id):
        """Get member-only playlist id from Youtube channel.

        Args:
            `channel_id`: Channel ID (e.g., "UC1234567890123456789")

        Returns:
            Member-only playlist id (e.g., "UUMO1234567890123456789")
        """
        if channel_id.startswith("UC"):
            return "UUMO" + channel_id[2:]
        else:
            return None

    def find_recent_video(
        self, playlist_id, part="contentDetails", max_results=3
    ):
        """Find recent video from Youtube playlist.

        Args:
            `playlist_id`: Playlist ID.
            `part`: Part to get.
            `max_results`: Max results.

        Returns:
            Recent video, or None if the request failed.
        """

        url = (
            "https://www.googleapis.com/youtube/v3/playlistItems?"
            "part={}&maxResults={}&playlistId={}".format(
                part, max_results, playlist_id
            )
        )

        res = self.request(url)
        if res is None:
            return None

        log(
            '[youtube_lib]',
            f'find recent video: {res.status_code} {res.text}',
        )

        if res.status_code == 200:
            return json.loads(res.text)["items"]
        # Channels without memberships have no member-only playlist
        elif is_playlist_not_found(res):
            return []
        else:
            return None

    def get_video_info(self, video_id, part="snippet"):
        """Get video info from Youtube.

        Args:
            `video_id`: Video ID, or comma-separated IDs (max 50).
            `part`: Part to get.

        Returns:
            Video info.
        """

        url = (
            "https://www.googleapis.com/youtube/v3/videos?"
            "part={}&id={}".format(part, video_id)
        )

        res = self.request(url)
        if res is None:
            return None

        log(
            '[youtube_lib]',
            f'get video info: {res.status_code} {res.text}',
        )

        if res.status_code == 200:
            return json.loads(res.text)
        else:
            return None
