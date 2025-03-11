import json
import os

import requests
from dotenv import load_dotenv

from libs.utils.logger import log

load_dotenv()


class YoutubeHandler:
    """Telegram Handler

    Attributes:
        `token`: Youtube api 3 Token.
    """

    def __init__(self):
        self.token = os.environ.get("youtube_api_token")

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
            "id={}&key={}&part=contentDetails".format(channel_id, self.token)
        )

        res = requests.get(url)

        log(
            '[youtube_lib]',
            f'get upload playlist id: {res.status_code} {res.text}',
        )

        if res.status_code == 200:
            return json.loads(res.text)["items"][0]["contentDetails"][
                "relatedPlaylists"
            ]["uploads"]
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
            "part={}&maxResults={}&playlistId={}&key={}".format(
                part, max_results, playlist_id, self.token
            )
        )

        res = requests.get(url)

        log(
            '[youtube_lib]',
            f'find recent video: {url}',
        )
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
            `video_id`: Video ID.
            `part`: Part to get.

        Returns:
            Video info.
        """

        url = (
            "https://www.googleapis.com/youtube/v3/videos?"
            "part={}&id={}&key={}".format(part, video_id, self.token)
        )

        res = requests.get(url)

        log(
            '[youtube_lib]',
            f'get video info: {res.status_code} {res.text}',
        )

        if res.status_code == 200:
            return json.loads(res.text)
        else:
            return None

    def get_channel_info(self, channel_id, event_type="live", part="snippet"):
        """Get channel info from Youtube.

        Args:
            `channel_id`: Channel ID.
            `event_type`: Event type.
            `part`: Part to get.

        Returns:
            Channel info.
        """

        url = (
            "https://www.googleapis.com/youtube/v3/search?"
            "part={}&channelId={}&eventType={}&type=video&key={}".format(
                part, channel_id, event_type, self.token
            )
        )

        res = requests.get(url)

        log(
            '[youtube_lib]',
            f'get channel info: {res.status_code} {res.text}',
        )

        if res.status_code == 200:
            return json.loads(res.text)
        else:
            return None
