import requests
from dotenv import load_dotenv

from libs.utils.logger import log

load_dotenv()


class DiscordHandler:
    """Discord Handler

    Attributes:
        `webhook_url`: Discord webhook url.
    """

    def __init__(self):
        pass

    def send_message(self, webhook_url, message):
        """Send message to Discord.

        Args:
            `msg`: Message to send.

        Returns:
            True if success, False if fail.
        """

        url = webhook_url

        res = requests.post(url, json={"content": message})

        log(
            '[discord_lib]',
            f'send message: {res.status_code} {res.text}',
        )

        if res.status_code == 204:
            return True
        else:
            return False
