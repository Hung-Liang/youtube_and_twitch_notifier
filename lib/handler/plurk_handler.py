import datetime
import os

from dotenv import load_dotenv
from plurk_oauth import PlurkAPI
import json

load_dotenv()


class PlurkHandler:
    def __init__(self):

        consumer_key = os.environ.get("plurk_consumer_key")
        consumer_secret = os.environ.get("plurk_consumer_secret")
        access_token = os.environ.get("plurk_access_token")
        access_token_secret = os.environ.get("plurk_access_token_secret")

        self.plurk = PlurkAPI(consumer_key, consumer_secret)
        self.plurk.authorize(access_token, access_token_secret)

    def get_offset(self, hours=None, minutes=None, seconds=None):
        """Get offset for plurk API

        Args:
            `hours`: Hours to find.
            `minutes`: Minutes to find.
            `seconds`: Seconds to find.

        Returns:
            Offset string.
        """

        offset = "now"

        if hours is not None:
            offset = datetime.datetime.utcnow() - datetime.timedelta(
                hours=hours
            )
        elif minutes is not None:
            offset = datetime.datetime.utcnow() - datetime.timedelta(
                minutes=minutes
            )
        elif seconds is not None:
            offset = datetime.datetime.utcnow() - datetime.timedelta(
                seconds=seconds
            )

        offset = offset.strftime("%Y-%m-%dT%H:%M:%S")

        return offset

    def find_plurk(self, hours=None, minutes=None, seconds=None):
        """Find plurk by time

        Args:
            `hours`: Hours to find.
            `minutes`: Minutes to find.
            `seconds`: Seconds to find.

        Returns:
            Plurk content if success, None if fail.
        """

        offset = self.get_offset(hours, minutes, seconds)

        result = self.plurk.callAPI(
            "/APP/Polling/getPlurks",
            options={"offset": offset, "qualifier": ':'},
        )

        return result

    def get_plurk(self, plurk_id):
        """Get plurk by id

        Args:
            `plurk_id`: Plurk id.

        Returns:
            Plurk content if success, None if fail.
        """

        result = self.plurk.callAPI(
            "/APP/Timeline/getPlurk",
            options={"plurk_id": plurk_id},
        )

        return result

    def like_plurk(self, plurk_id):
        """Favorite plurk by id

        Args:
            `plurk_id`: Plurk id.

        Returns:
            True if success, False if fail.
        """

        ids = json.dumps([plurk_id])

        result = self.plurk.callAPI(
            "/APP/Timeline/favoritePlurks",
            options={"ids": ids},
        )

        if result["success_text"] == 'ok':
            return True
        else:
            return False

    def replurk_plurk(self, plurk_id):
        """Replurk plurk by id

        Args:
            `plurk_id`: Plurk id.

        Returns:
            True if success, False if fail.
        """

        ids = json.dumps([plurk_id])

        result = self.plurk.callAPI(
            "/APP/Timeline/replurk",
            options={"ids": ids},
        )

        if result["success"]:
            return True
        else:
            return False
