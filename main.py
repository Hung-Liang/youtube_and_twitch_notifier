from time import sleep, time

from lib.handler.youtube_handler import YoutubeHandler
from lib.utils.notify import send_notify
from lib.utils.tools import send_exception_log


while True:
    sleep(180 - time() % 180)

    info = YoutubeHandler().get_channel_info("")

    try:
        send_notify(info)

    except Exception as e:
        send_exception_log(e)
