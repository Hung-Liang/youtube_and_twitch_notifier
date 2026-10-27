import argparse
import sys

from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers.blocking import BlockingScheduler

from libs.utils.config_check import check_groups
from libs.utils.config_loader import load_config
from libs.utils.logger import TIMEZONE, log
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
    # Keep the traceback in the local log; Telegram gets the exception text only
    log("[scheduler]", f"Job {event.job_id} traceback\n{event.traceback}")
    send_exception_log(
        f"[scheduler] Job {event.job_id} failed\n"
        f"{type(event.exception).__name__}: {event.exception}"
    )


def check_config(youtube_groups, twitch_groups):
    errors = []
    for platform, groups in (
        ("youtube", youtube_groups),
        ("twitch", twitch_groups),
    ):
        group_errors, group_warnings = check_groups(platform, groups)
        errors += group_errors
        for warning in group_warnings:
            log("[config]", f"warning: {warning}", console=True)

    if errors:
        raise ValueError("Invalid config.py:\n" + "\n".join(errors))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="validate the config file and exit",
    )
    args = parser.parse_args(argv)

    if args.check_config:
        try:
            check_config(*load_config())
        except (FileNotFoundError, ValueError) as e:
            print(e)
            return 1
        print("Config OK")
        return 0

    youtube_groups, twitch_groups = load_config()
    check_config(youtube_groups, twitch_groups)

    send_service_start_notification()

    # Default misfire grace is 1s, so a slightly late wakeup skips the run
    scheduler = BlockingScheduler(
        timezone=TIMEZONE,
        job_defaults={"misfire_grace_time": 30, "coalesce": True},
    )
    scheduler.add_listener(on_job_error, EVENT_JOB_ERROR)

    schedule_group_jobs(scheduler, "youtube", youtube_groups)
    schedule_group_jobs(scheduler, "twitch", twitch_groups)

    scheduler.add_job(send_daily_log, "cron", hour=0, minute=0)

    scheduler.start()


if __name__ == "__main__":
    sys.exit(main())
