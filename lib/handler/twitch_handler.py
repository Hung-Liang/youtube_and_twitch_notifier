import requests

from dotenv import load_dotenv
import os

load_dotenv()


class TwitchHandler:
    def __init__(self):
        self.client_id = os.environ.get("twitch_client_id")
        self.client_secret = os.environ.get("twitch_client_secret")
        self.access_token = self.get_access_token()
        self.base_url = "https://api.twitch.tv/helix/"
        self.headers = self.get_headers()

    def get_access_token(self):
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        response = requests.post(url, params=params)

        if response.status_code == 200:
            data = response.json()
            return data["access_token"]
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

    def get_stream_info(self, username: str):
        url = f"{self.base_url}streams"
        params = {"user_login": username}
        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            data = response.json()
            streams = data.get("data", [])
            if streams:
                return {"is_live": True, "title": streams[0]["title"]}
            return {"is_live": False, "title": None}
        else:
            raise Exception(
                f"Twitch API Error: {response.status_code} {response.text}"
            )
