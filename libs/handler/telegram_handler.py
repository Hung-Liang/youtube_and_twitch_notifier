import json
import os

import requests
from dotenv import load_dotenv

from libs.utils.logger import log

load_dotenv()

REQUEST_TIMEOUT = 10


class TelegramHandler:
    """Telegram Handler

    Attributes:
        `token`: Telegram Bot Token.

    Functions:
        `send_message`: Send message to Telegram.
        `send_document`: Send document to Telegram.
    """

    def __init__(self):
        self.token = os.environ.get("bot_token")
        self.last_status_code = None
        self.last_retry_after = None

    def send_message(self, cid, message):
        """Send message to Telegram.

        Args:
            `cid`: Chat ID.
            `message`: Message to send.

        Returns:
            True if success, False if fail.
        """

        url = 'https://api.telegram.org/bot{}/sendMessage'.format(self.token)
        data = {"chat_id": cid, "parse_mode": "HTML", "text": message}

        res = requests.post(url, data=data, timeout=REQUEST_TIMEOUT)
        self.last_status_code = res.status_code
        self.last_retry_after = None
        if res.status_code == 429:
            try:
                self.last_retry_after = (
                    res.json().get("parameters", {}).get("retry_after")
                )
            except ValueError:
                pass

        log(
            '[telegram_lib]',
            f'send message: {res.status_code} {res.text}',
        )

        if res.status_code == 200:
            return True
        else:
            return False

    def send_document(self, cid, path, filename):
        """Send document to Telegram.

        Args:
            `cid`: Chat ID.
            `path`: Path to file.
            `filename`: Filename.

        Returns:
            (True, body) if success, (False, body) if fail, or (False, None)
            on a network error.
        """

        url = 'https://api.telegram.org/bot{}/sendDocument?chat_id={}'.format(
            self.token, cid
        )

        with open(path, 'rb') as f:
            files = {
                "document": (filename, f, 'application/octet-stream'),
            }
            try:
                res = requests.post(url, files=files, timeout=REQUEST_TIMEOUT)
            # Network errors are usually transient, so callers treat this as
            # a failed upload and retry next run instead of failing the job
            except requests.RequestException as err:
                # Only the error type: its message may contain the bot token
                log(
                    '[telegram_lib]',
                    f'send document failed: {type(err).__name__}',
                )
                return False, None

        log(
            '[telegram_lib]',
            f'send document: {res.status_code} {res.text}',
        )

        if res.status_code == 200:
            return True, json.loads(res.text)
        else:
            return False, json.loads(res.text)
