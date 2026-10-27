import pytest

import main
from libs.utils import config_loader


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


def test_check_config_raises_on_errors():
    with pytest.raises(ValueError, match="Invalid config"):
        main.check_config({"g": {"interval": 0}}, {})


def test_check_config_logs_warnings(capsys):
    group = {
        "interval": 7,
        "channel_ids": [],
        "notifier_types": {},
    }
    main.check_config({}, {"g": group})

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


def test_check_config_flag_exits_without_starting(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("must not start the service")

    monkeypatch.setattr(main, "load_config", lambda: ({}, {}))
    monkeypatch.setattr(main, "send_service_start_notification", fail)
    monkeypatch.setattr(main, "BlockingScheduler", fail)

    assert main.main(["--check-config"]) == 0


def test_check_config_flag_fails_on_invalid_config(monkeypatch, capsys):
    monkeypatch.setattr(
        main, "load_config", lambda: ({"g": {"interval": 0}}, {})
    )

    assert main.main(["--check-config"]) == 1
    assert "Invalid config" in capsys.readouterr().out


def test_check_config_flag_fails_on_missing_config(monkeypatch, tmp_path):
    monkeypatch.setattr(
        main,
        "load_config",
        lambda: config_loader.load_config(tmp_path / "missing.py"),
    )

    assert main.main(["--check-config"]) == 1


def test_baselines_run_before_scheduler_starts(monkeypatch):
    events = []

    class Scheduler(FakeScheduler):
        def __init__(self, **kwargs):
            super().__init__()

        def add_listener(self, *args):
            pass

        def start(self):
            events.append("start")

    youtube = {"y": {"interval": 5}}
    twitch = {"t": {"interval": 5}}
    monkeypatch.setattr(main, "load_config", lambda: (youtube, twitch))
    monkeypatch.setattr(main, "check_config", lambda *a: None)
    monkeypatch.setattr(main, "send_service_start_notification", lambda: None)
    monkeypatch.setattr(
        main,
        "init_baseline",
        lambda platform, group, config: events.append((platform, group)),
    )
    monkeypatch.setattr(main, "BlockingScheduler", Scheduler)

    main.main([])

    assert events == [("youtube", "y"), ("twitch", "t"), "start"]
