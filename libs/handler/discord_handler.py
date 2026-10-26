import requests
from dotenv import load_dotenv

from libs.utils.logger import log

load_dotenv()

REQUEST_TIMEOUT = 10


class DiscordHandler:
    """Discord Handler

    Attributes:
        `webhook_url`: Discord webhook url.
    """

    def __init__(self):
        self.last_status_code = None
        self.last_retry_after = None

    def send_message(self, webhook_url, message):
        """Send message to Discord.

        Args:
            `msg`: Message to send.

        Returns:
            True if success, False if fail.
        """

        url = webhook_url

        res = requests.post(
            url, json={"content": message}, timeout=REQUEST_TIMEOUT
        )
        self.last_status_code = res.status_code
        self.last_retry_after = None
        if res.status_code == 429:
            try:
                self.last_retry_after = res.json().get("retry_after")
            except ValueError:
                pass

        log(
            '[discord_lib]',
            f'send message: {res.status_code} {res.text}',
        )

        if res.status_code == 204:
            return True
        else:
            return False
