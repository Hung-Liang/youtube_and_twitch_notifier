from datetime import datetime
from pathlib import Path

import pytz

from libs.utils.file_path import LOG_PATH

TIMEZONE = pytz.timezone("Asia/Taipei")


def get_log_filename():
    """Get today's log filename in the scheduler timezone."""
    return datetime.now(TIMEZONE).strftime('%Y-%m-%d') + '.log'


def log(*messages, console: bool = False, return_filename: bool = False):
    """Basic Log to Record Progress.

    Args:
        `messages`: Logging message.
    """

    filename = get_log_filename()

    file_path = Path(LOG_PATH, filename)

    with open(file_path, 'a', encoding='utf-8') as f:
        now = datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
        print(now, *messages, file=f)

    if console:
        print(messages)

    if return_filename:
        return filename
