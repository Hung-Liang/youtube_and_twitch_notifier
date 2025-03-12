import pytz
from apscheduler.schedulers.blocking import BlockingScheduler

from libs.config import groups
from libs.utils.notify import send_notify
from libs.utils.tools import send_daily_log


def schedule_group_jobs(scheduler, platform, group_data):
    for group, config in group_data.items():
        interval = config["interval"]
        scheduler.add_job(
            send_notify,
            "cron",
            minute=f"0-59/{interval}",
            args=[platform, group, config],
        )


timezone = pytz.timezone("Asia/Taipei")
scheduler = BlockingScheduler(timezone=timezone)

schedule_group_jobs(scheduler, "youtube", groups["youtube"])
schedule_group_jobs(scheduler, "twitch", groups["twitch"])

scheduler.add_job(send_daily_log, "cron", hour=0, minute=0)

scheduler.start()
