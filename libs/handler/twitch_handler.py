import os
import threading

import requests
from dotenv import load_dotenv

from libs.utils.logger import log

load_dotenv()

REQUEST_TIMEOUT = 10

# Shared across instances since app access tokens are valid for ~60 days
_access_token = None
_access_token_lock = threading.Lock()


class TwitchHandler:
    def __init__(self):
        self.client_id = os.environ.get("twitch_client_id")
        self.client_secret = os.environ.get("twitch_client_secret")
        self.access_token = self.get_access_token()
        self.base_url = "https://api.twitch.tv/helix/"
        self.headers = self.get_headers()

    def get_access_token(self, expired_token=None):
        global _access_token

        with _access_token_lock:
            # Another thread may have refreshed the token already
            if _access_token and _access_token != expired_token:
                return _access_token

            url = "https://id.twitch.tv/oauth2/token"
            params = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            }
            response = requests.post(
                url, params=params, timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                log("[twitch_lib]", "access token updated")
                _access_token = data["access_token"]
                return _access_token
            else:
                raise Exception(
                    f"Twitch API Error: {response.status_code} {response.text}"
                )

    def get_headers(self):
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}",
        }
        return headers

    def request_streams(self, params):
        return requests.get(
            f"{self.base_url}streams",
            headers=self.headers,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

    def get_stream_infos(self, usernames: list):
        params = {"user_login": usernames}
        response = self.request_streams(params)

        if response.status_code == 401:
            self.access_token = self.get_access_token(self.access_token)
            self.headers = self.get_headers()
            response = self.request_streams(params)

        if response.status_code == 200:
            data = response.json()
            streams = data.get("data", [])
            log(
                "[twitch_lib]",
                f"get stream infos: {response.status_code} {data}",
            )

            stream_infos = []

            for stream in streams:
                stream_infos.append(
                    {
                        "is_live": True,
                        "title": stream["title"],
                        "stream_id": stream["id"],
                        "user_login": stream["user_login"],
                        "user_name": stream["user_name"],
                    }
                )
            return stream_infos
        else:
            raise Exception(
                f"Twitch API Error: {response.status_code} {response.text}"
            )
