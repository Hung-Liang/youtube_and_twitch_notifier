import re

from libs.utils import logger


def test_log_appends_timestamped_line(isolate):
    filename = logger.log("[tag]", "hello", return_filename=True)
    logger.log("[tag]", "world")

    lines = (isolate / "log" / filename).read_text("utf-8").splitlines()
    assert filename == logger.get_log_filename()
    assert len(lines) == 2
    assert re.fullmatch(
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[tag\] hello", lines[0]
    )


def test_log_console_prints(capsys):
    logger.log("[tag]", "hello", console=True)

    assert capsys.readouterr().out == "[tag] hello\n"


def test_log_returns_none_by_default():
    assert logger.log("x") is None
