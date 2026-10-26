from libs.handler.discord_handler import DiscordHandler
from libs.handler.telegram_handler import TelegramHandler
from libs.utils.tools import (
    get_message,
    get_multiple_live_title_and_url,
    get_multiple_twitch_title_and_url,
    get_multiple_upload_id,
    send_exception_log,
)


def send_notify_by_type(notifier_type, data, title, url, channel_title):
    def send_with_retry(handler, message, users):
        for user in users:
            if handler.send_message(user, message):
                continue

            # Not found won't recover with a different message
            if handler.last_status_code == 404:
                send_exception_log(
                    f"[main] {notifier_type.capitalize()} Message Sent Failed"
                    f" (404, skip fallback)"
                )
                continue

            fallback_message = get_message(
                notifier_type, "", url, channel_title, data["word_list"]
            )
            if not handler.send_message(user, fallback_message):
                send_exception_log(
                    f"[main] {notifier_type.capitalize()} Message Sent Failed"
                )

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

    send_with_retry(handler, message, users)


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
        for title, url, channel_title in results:
            for notifier_type, data in notifier_types.items():
                send_notify_by_type(
                    notifier_type, data, title, url, channel_title
                )

    channel_ids = config['channel_ids']
    notifier_types = config['notifier_types']

    results = get_results(platform, channel_ids, config)
    if results:
        notify_all(results, notifier_types)
