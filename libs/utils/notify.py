import time

import requests

from libs.handler.discord_handler import DiscordHandler
from libs.handler.telegram_handler import TelegramHandler
from libs.utils.logger import log
from libs.utils.tools import (
    get_message,
    get_multiple_live_title_and_url,
    get_multiple_twitch_title_and_url,
    get_multiple_upload_id,
    init_twitch_baseline,
    init_youtube_baseline,
    send_exception_log,
)

# Longest rate-limit wait we accept before giving up on a recipient
MAX_RETRY_AFTER = 30


def send_notify_by_type(notifier_type, data, title, url, channel_title):
    """Send to every recipient of one notifier type.

    Returns:
        A list of bools, one per recipient, True if delivered.
    """

    def send_to_user(handler, message, user):
        if handler.send_message(user, message):
            return True

        status_code = handler.last_status_code

        if status_code == 429:
            retry_after = handler.last_retry_after
            if retry_after is not None and retry_after <= MAX_RETRY_AFTER:
                time.sleep(retry_after)
                if handler.send_message(user, message):
                    return True
            send_exception_log(
                f"[main] {notifier_type.capitalize()} Message Sent Failed"
                f" (429, retry_after={retry_after})"
            )
            return False

        # Not found won't recover with a different message, and neither will
        # other errors; only a bad request (e.g. broken HTML) may
        if status_code != 400:
            send_exception_log(
                f"[main] {notifier_type.capitalize()} Message Sent Failed"
                f" ({status_code}, skip fallback)"
            )
            return False

        fallback_message = get_message(
            notifier_type, "", url, channel_title, data["word_list"]
        )
        if handler.send_message(user, fallback_message):
            return True

        send_exception_log(
            f"[main] {notifier_type.capitalize()} Message Sent Failed"
        )
        return False

    def send_with_retry(handler, message, users):
        delivered = []
        for index, user in enumerate(users):
            # One unreachable recipient must not block the others
            try:
                delivered.append(send_to_user(handler, message, user))
            # The request was sent but the reply was lost, so the message
            # has likely arrived; count it as delivered to avoid a resend
            except requests.ReadTimeout as err:
                send_exception_log(
                    f"[main] {notifier_type.capitalize()} Message Delivery"
                    f" Unknown (recipient #{index}, {type(err).__name__})"
                )
                delivered.append(True)
            except requests.RequestException as err:
                # Only the error type: its message may contain the bot token
                # or webhook url
                send_exception_log(
                    f"[main] {notifier_type.capitalize()} Message Sent Failed"
                    f" (recipient #{index}, {type(err).__name__})"
                )
                delivered.append(False)
        return delivered

    message = get_message(
        notifier_type, title, url, channel_title, data["word_list"]
    )

    if notifier_type == "telegram":
        users = data["recipient_ids"]
        handler = TelegramHandler()
    elif notifier_type == "discord":
        users = data["webhook_urls"]
        handler = DiscordHandler()
    else:
        raise ValueError(f"Unknown notifier_type: {notifier_type}")

    return send_with_retry(handler, message, users)


def send_notify(platform, group, config):
    def get_results(platform, channel_ids, config):

        if platform == "youtube":
            broadcast_types = config.get('broadcast_types', ["none", "live"])
            notify_member_only = config.get('notify_member_only', False)
            upload_ids = get_multiple_upload_id(
                channel_ids, notify_member_only
            )
            return get_multiple_live_title_and_url(
                upload_ids, broadcast_types, group
            )

        elif platform == "twitch":
            return get_multiple_twitch_title_and_url(channel_ids, group)

        return []

    def notify_all(results, notifier_types):
        for title, url, channel_title, mark_notified in results:
            delivered = []
            for notifier_type, data in notifier_types.items():
                delivered += send_notify_by_type(
                    notifier_type, data, title, url, channel_title
                )

            # Retry next run only when every recipient failed
            if delivered and not any(delivered):
                log("[main]", f"All recipients failed, retry later: {url}")
                continue

            mark_notified()

    channel_ids = config['channel_ids']
    notifier_types = config['notifier_types']

    results = get_results(platform, channel_ids, config)
    if results:
        notify_all(results, notifier_types)


def init_baseline(platform, group, config):
    """Ignore what a group shows now, so only later streams are notified."""
    channel_ids = config['channel_ids']

    if platform == "youtube":
        notify_member_only = config.get('notify_member_only', False)
        upload_ids = get_multiple_upload_id(channel_ids, notify_member_only)
        init_youtube_baseline(upload_ids, group)

    elif platform == "twitch":
        init_twitch_baseline(channel_ids, group)
