import requests

from libs.handler.discord_handler import DiscordHandler
from libs.handler.telegram_handler import TelegramHandler
from libs.utils.logger import log
from libs.utils.tools import (
    get_message,
    get_multiple_live_title_and_url,
    get_multiple_twitch_title_and_url,
    get_multiple_upload_id,
    send_exception_log,
)


def send_notify_by_type(notifier_type, data, title, url, channel_title):
    """Send to every recipient of one notifier type.

    Returns:
        A list of bools, one per recipient, True if delivered.
    """

    def send_to_user(handler, message, user):
        if handler.send_message(user, message):
            return True

        # Not found won't recover with a different message
        if handler.last_status_code == 404:
            send_exception_log(
                f"[main] {notifier_type.capitalize()} Message Sent Failed"
                f" (404, skip fallback)"
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
