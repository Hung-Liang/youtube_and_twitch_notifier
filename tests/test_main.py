import pytest

import main


class FakeScheduler:
    def __init__(self):
        self.jobs = []

    def add_job(self, func, trigger, **kwargs):
        self.jobs.append((func, trigger, kwargs))


def test_group_jobs_use_whole_minute_cron():
    scheduler = FakeScheduler()
    config = {"interval": 5}

    main.schedule_group_jobs(scheduler, "twitch", {"g": config})

    func, trigger, kwargs = scheduler.jobs[0]
    assert func is main.send_notify
    assert trigger == "cron"
    assert kwargs == {"minute": "0-59/5", "args": ["twitch", "g", config]}


def test_check_config_raises_on_errors(monkeypatch):
    monkeypatch.setattr(main, "youtube_groups", {"g": {"interval": 0}})
    monkeypatch.setattr(main, "twitch_groups", {})

    with pytest.raises(ValueError, match="Invalid config.py"):
        main.check_config()


def test_check_config_logs_warnings(monkeypatch, capsys):
    group = {
        "interval": 7,
        "channel_ids": [],
        "notifier_types": {},
    }
    monkeypatch.setattr(main, "youtube_groups", {})
    monkeypatch.setattr(main, "twitch_groups", {"g": group})

    main.check_config()

    assert "does not divide 60" in capsys.readouterr().out


def test_job_error_sends_exception_text_only(monkeypatch):
    logged, sent = [], []
    monkeypatch.setattr(main, "log", lambda *m, **kw: logged.append(m))
    monkeypatch.setattr(main, "send_exception_log", sent.append)

    class Event:
        job_id = "abc"
        exception = ConnectionError("Connection reset")
        traceback = 'File "x.py", line 1, in f\n'

    main.on_job_error(Event())

    assert sent == [
        "[scheduler] Job abc failed\nConnectionError: Connection reset"
    ]
    assert 'File "x.py"' in logged[0][1]
