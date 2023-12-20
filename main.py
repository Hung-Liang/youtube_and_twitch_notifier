from time import sleep, time

from lib.config import groups
from lib.utils.notify import send_notify
from lib.utils.tools import send_daily_log, send_exception_log


while True:
    sleep(180 - time() % 180)

    try:
        send_daily_log()

        if time() % 360 <= 10:
            for channel_id, group in groups:
                send_notify(channel_id, group)
        else:
            for channel_id, group in groups[:2]:
                send_notify(channel_id, group)

    except Exception as e:
        send_exception_log(e)
