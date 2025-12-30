import pytz
from apscheduler.schedulers.blocking import BlockingScheduler

from libs.config import youtube_groups, twitch_groups
from libs.utils.notify import send_notify
from libs.utils.tools import send_daily_log, send_service_start_notification


def schedule_group_jobs(scheduler, platform, group_data):
    for group, config in group_data.items():
        interval = config["interval"]
        scheduler.add_job(
            send_notify,
            "cron",
            minute=f"0-59/{interval}",
            args=[platform, group, config],
        )


send_service_start_notification()

timezone = pytz.timezone("Asia/Taipei")
scheduler = BlockingScheduler(timezone=timezone)

schedule_group_jobs(scheduler, "youtube", youtube_groups)
schedule_group_jobs(scheduler, "twitch", twitch_groups)

scheduler.add_job(send_daily_log, "cron", hour=0, minute=0)

scheduler.start()
