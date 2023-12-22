from time import sleep, time

from lib.config import groups, owner_id
from lib.utils.logger import log
from lib.utils.notify import send_notify, send_plurk_updates
from lib.utils.tools import send_daily_log, send_exception_log

while True:
    sleep(180 - time() % 180)

    try:
        log("[main]", "Send Daily Log")
        send_daily_log()

        log("[main]", "Send Notify")
        if time() % 360 <= 10:
            for channel_id, group in groups:
                send_notify(channel_id, group)
        else:
            for channel_id, group in groups[:2]:
                send_notify(channel_id, group)

        log("[main]", "Send Plurk Updates")
        send_plurk_updates(owner_id)
    except Exception as e:
        send_exception_log(e)
