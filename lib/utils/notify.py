from lib.handler.discord_handler import DiscordHandler
from lib.handler.plurk_handler import PlurkHandler
from lib.handler.telegram_handler import TelegramHandler
from lib.utils.logger import log
from lib.utils.tools import (
    find_plurk_id_by_user_id,
    find_raw_content_by_user_id,
    get_id_list,
    get_live_title_and_url,
    get_message,
    get_upload_id,
    send_exception_log,
)


def send_plurk_updates(owner_id):
    plurk = PlurkHandler()
    result = plurk.find_plurk(minutes=3)
    contents = find_raw_content_by_user_id(owner_id, result['plurks'])

    for content in contents:
        log('[main]', 'Plurk Content: ', content)
        sent = DiscordHandler(mode="test").send_message(content)
        if not sent:
            send_exception_log('[main] Plurk Message Sent Failed')

    plurk_ids = find_plurk_id_by_user_id(owner_id, result['plurks'])

    for plurk_id in plurk_ids:
        plurk.like_plurk(plurk_id)
        plurk.replurk_plurk(plurk_id)


def send_notify(channel_id, group="group_1"):
    id_list = get_id_list(group)

    upload_id = get_upload_id(channel_id)
    title, url, channel_title = get_live_title_and_url(upload_id)

    if title:
        telegram_message, discord_message = get_message(
            title, url, channel_title, group
        )

        log("[main]", "Telegram Message: ", telegram_message)
        log("[main]", "Discord Message: ", discord_message)

        for cid in id_list:
            sent = TelegramHandler().send_message(cid, telegram_message)

            if not sent:
                sent = telegram_message, discord_message = get_message(
                    "", url, channel_title, group
                )
                sent = TelegramHandler().send_message(cid, telegram_message)
                send_exception_log("[main] Telegram Message Sent Failed")

        # TelegramHandler().send_message(telegram_channel_id, telegram_message)
        if group == "group_1":
            sent = DiscordHandler().send_message(discord_message)
            if not sent:
                send_exception_log("[main] Discord Message Sent Failed")
