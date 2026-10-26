from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers.blocking import BlockingScheduler

from libs.config import youtube_groups, twitch_groups
from libs.utils.logger import TIMEZONE
from libs.utils.notify import send_notify
from libs.utils.tools import (
    send_daily_log,
    send_exception_log,
    send_service_start_notification,
)


def schedule_group_jobs(scheduler, platform, group_data):
    for group, config in group_data.items():
        interval = config["interval"]
        scheduler.add_job(
            send_notify,
            "cron",
            minute=f"0-59/{interval}",
            args=[platform, group, config],
        )


def on_job_error(event):
    send_exception_log(
        f"[scheduler] Job {event.job_id} failed\n{event.traceback}"
    )


def main():
    send_service_start_notification()

    scheduler = BlockingScheduler(timezone=TIMEZONE)
    scheduler.add_listener(on_job_error, EVENT_JOB_ERROR)

    schedule_group_jobs(scheduler, "youtube", youtube_groups)
    schedule_group_jobs(scheduler, "twitch", twitch_groups)

    scheduler.add_job(send_daily_log, "cron", hour=0, minute=0)

    scheduler.start()


if __name__ == "__main__":
    main()
