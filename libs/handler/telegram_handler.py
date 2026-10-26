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
        `send_document_by_fid`: Send document by file id to Telegram.
    """

    def __init__(self):
        self.token = os.environ.get("bot_token")

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
            True if success, False if fail.
        """

        url = 'https://api.telegram.org/bot{}/sendDocument?chat_id={}'.format(
            self.token, cid
        )

        with open(path, 'rb') as f:
            files = {
                "document": (filename, f, 'application/octet-stream'),
            }
            res = requests.post(url, files=files, timeout=REQUEST_TIMEOUT)

        log(
            '[telegram_lib]',
            f'send document: {res.status_code} {res.text}',
        )

        if res.status_code == 200:
            return True, json.loads(res.text)
        else:
            return False, json.loads(res.text)

    def send_document_by_fid(self, cid, fid):
        """Send document by file id to Telegram.

        Args:
            `cid`: Chat ID.
            `fid`: File ID.

        Returns:
            True if success, False if fail.
        """

        url = (
            'https://api.telegram.org/bot{}'
            '/sendDocument?chat_id={}&document={}'.format(self.token, cid, fid)
        )

        res = requests.post(url, timeout=REQUEST_TIMEOUT)

        log(
            '[telegram_lib]',
            f'send document by fid: {res.status_code} {res.text}',
        )

        if res.status_code == 200:
            return True
        else:
            return False
