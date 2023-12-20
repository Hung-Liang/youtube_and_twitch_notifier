import os

import requests
from dotenv import load_dotenv

from lib.utils.logger import log

load_dotenv()


class DiscordHandler:
    """Discord Handler

    Attributes:
        `webhook_url`: Discord webhook url.
    """

    def __init__(self, mode="prod"):
        if mode == "prod":
            self.webhook_url = os.environ.get("discord_webhook_url")
        elif mode == "test":
            self.webhook_url = os.environ.get("discord_webhook_url_test")

    def send_message(self, msg):
        """Send message to Discord.

        Args:
            `msg`: Message to send.

        Returns:
            True if success, False if fail.
        """

        url = self.webhook_url

        res = requests.post(url, json={"content": msg})

        log(
            '[discord_lib]',
            f'send message: {res.status_code} {res.text}',
        )

        if res.status_code == 204:
            return True
        else:
            return False
