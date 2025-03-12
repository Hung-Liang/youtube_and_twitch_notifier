from libs.handler.discord_handler import DiscordHandler
from libs.handler.telegram_handler import TelegramHandler
from libs.utils.tools import (
    get_live_title_and_url,
    get_message,
    get_twitch_title_and_url,
    get_upload_id,
    send_exception_log,
)


def send_notify_by_type(notifier_type, data, title, url, channel_title):
    def send_with_retry(handler, message, users):
        for user in users:
            sent = handler.send_message(user, message)
            if not sent:
                message = get_message(
                    notifier_type, "", url, channel_title, data["word_list"]
                )
                sent = handler.send_message(user, message)
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

    send_with_retry(handler, message, users)


def send_notify(platform, group):
    def get_results(platform, channel_id, group):
        if platform == "youtube":
            broadcast_types = group.get('broadcast_types', ["none", "live"])
            upload_id = get_upload_id(channel_id)
            return get_live_title_and_url(upload_id, broadcast_types)

        elif platform == "twitch":
            title, url, channel_title = get_twitch_title_and_url(channel_id)
            return [(title, url, channel_title)] if title else []

        return []

    def notify_all(results, notifier_types):
        for title, url, channel_title in results:
            for notifier_type, data in notifier_types.items():
                send_notify_by_type(
                    notifier_type, data, title, url, channel_title
                )

    channel_ids = group['channel_ids']
    notifier_types = group['notifier_types']

    for channel_id in channel_ids:
        results = get_results(platform, channel_id, group)
        if results:
            notify_all(results, notifier_types)
