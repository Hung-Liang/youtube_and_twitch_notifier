from lib.handler.discord_handler import DiscordHandler
from lib.handler.telegram_handler import TelegramHandler
from lib.utils.tools import (
    get_live_title_and_url,
    get_message,
    get_twitch_title_and_url,
    get_upload_id,
    send_exception_log,
)


def send_notify_by_type(notifier_type, data, title, url, channel_title):

    message = get_message(
        notifier_type, title, url, channel_title, data["word_list"]
    )

    if notifier_type == "telegram":
        recipients_ids = data["recipient_id"]

        for cid in recipients_ids:
            sent = TelegramHandler().send_message(cid, message)

            if not sent:
                message = get_message(
                    notifier_type, "", url, channel_title, data["word_list"]
                )
                sent = TelegramHandler().send_message(cid, message)
                send_exception_log("[main] Telegram Message Sent Failed")

    elif notifier_type == "discord":
        webhook_urls = data["webhook_url"]

        for webhook_url in webhook_urls:
            sent = DiscordHandler(webhook_url).send_message(message)

            if not sent:
                send_exception_log("[main] Discord Message Sent Failed")


def send_notify(platform, group):

    if platform == "youtube":
        channel_ids = group['channel_id']

        for channel_id in channel_ids:
            upload_id = get_upload_id(channel_id)

            results = get_live_title_and_url(upload_id)
            # title, url, channel_title = get_live_title_and_url(upload_id)

            if len(results) == 0:
                continue

            notifier_types = group['notifier_types']

            for result in results:
                title, url, channel_title = result

                for notifier_type, data in notifier_types.items():
                    send_notify_by_type(
                        notifier_type, data, title, url, channel_title
                    )

    elif platform == "twitch":
        channel_ids = group['channel_id']

        for channel_id in channel_ids:

            title, url, channel_title = get_twitch_title_and_url(channel_id)

            if not title:
                continue

            notifier_types = group['notifier_types']

            for notifier_type, data in notifier_types.items():
                send_notify_by_type(
                    notifier_type, data, title, url, channel_title
                )
