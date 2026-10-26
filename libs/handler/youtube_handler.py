import json
import os
import random

import requests
from dotenv import load_dotenv

from libs.utils.logger import log

load_dotenv()

REQUEST_TIMEOUT = 10


class YoutubeHandler:
    """Youtube Handler

    Attributes:
        `token`: Youtube api 3 Token.
    """

    def __init__(self):
        # self.token = os.environ.get("youtube_api_token")
        tokens = os.environ.get("youtube_api_token")
        if not tokens:
            raise ValueError("youtube_api_token is not set in .env")

        self.token = random.choice(tokens.split(","))
        # Pass the key via header so it never appears in URLs or tracebacks
        self.headers = {"X-goog-api-key": self.token}

    def get_upload_playlist_id(self, channel_id):
        """Get upload playlist id from Youtube.

        Args:
            `channel_id`: Channel ID.
            `part`: Part to get.

        Returns:
            Upload playlist id.
        """

        url = (
            "https://www.googleapis.com/youtube/v3/channels?"
            "id={}&part=contentDetails".format(channel_id)
        )

        res = requests.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT)

        log(
            '[youtube_lib]',
            f'get upload playlist id: {res.status_code} {res.text}',
        )

        if res.status_code != 200:
            return None

        items = json.loads(res.text).get("items", [])
        if not items:
            log('[youtube_lib]', f'channel not found: {channel_id}')
            return None

        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

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
            Recent video.
        """

        url = (
            "https://www.googleapis.com/youtube/v3/playlistItems?"
            "part={}&maxResults={}&playlistId={}".format(
                part, max_results, playlist_id
            )
        )

        res = requests.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT)

        log(
            '[youtube_lib]',
            f'find recent video: {res.status_code} {res.text}',
        )

        if res.status_code == 200:
            return json.loads(res.text)["items"]
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

        res = requests.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT)

        log(
            '[youtube_lib]',
            f'get video info: {res.status_code} {res.text}',
        )

        if res.status_code == 200:
            return json.loads(res.text)
        else:
            return None
