from time import sleep, time

from lib.utils.notify import send_notify
from lib.utils.tools import send_exception_log, send_daily_log


while True:
    sleep(180 - time() % 180)

    try:
        send_daily_log()
        send_notify("")

    except Exception as e:
        send_exception_log(e)
