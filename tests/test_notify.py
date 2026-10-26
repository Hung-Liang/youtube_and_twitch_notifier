import pytest
import requests

from libs.utils import notify


class FakeHandler:
    """Replies per recipient: True, False, a status code, or an exception."""

    replies = {}

    def __init__(self):
        self.last_status_code = None
        self.sent = []

    def send_message(self, user, message):
        self.sent.append((user, message))
        reply = self.replies.get(user, True)
        if isinstance(reply, Exception):
            raise reply
        if reply is True:
            self.last_status_code = 200
            return True
        self.last_status_code = reply
        return False


@pytest.fixture
def handler(monkeypatch):
    created = []

    def factory():
        instance = FakeHandler()
        created.append(instance)
        return instance

    FakeHandler.replies = {}
    monkeypatch.setattr(notify, "TelegramHandler", factory)
    return created


@pytest.fixture
def alerts(monkeypatch):
    sent = []
    monkeypatch.setattr(notify, "send_exception_log", sent.append)
    return sent


def telegram_config(*users):
    return {"telegram": {"recipient_ids": list(users), "word_list": []}}


def run_notify(monkeypatch, notifier_types, results):
    monkeypatch.setattr(
        notify, "get_multiple_twitch_title_and_url", lambda *a: results
    )
    notify.send_notify(
        "twitch", "g", {"channel_ids": ["c"], "notifier_types": notifier_types}
    )


def make_result(marked):
    return ("title", "https://x", "ch", lambda: marked.append(True))


def test_connection_error_does_not_block_other_recipients(
    monkeypatch, handler, alerts
):
    FakeHandler.replies = {"a": requests.ConnectionError("bot123:secret")}
    marked = []

    run_notify(monkeypatch, telegram_config("a", "b"), [make_result(marked)])

    assert [user for user, _ in handler[0].sent] == ["a", "b"]
    assert marked == [True]
    assert len(alerts) == 1
    assert "ConnectionError" in alerts[0]
    assert "secret" not in alerts[0]


def test_not_marked_when_every_recipient_fails(monkeypatch, handler, alerts):
    FakeHandler.replies = {"a": 500, "b": requests.Timeout()}
    marked = []

    run_notify(monkeypatch, telegram_config("a", "b"), [make_result(marked)])

    assert marked == []


def test_marked_when_no_recipient_configured(monkeypatch, handler, alerts):
    marked = []

    run_notify(monkeypatch, telegram_config(), [make_result(marked)])

    assert marked == [True]
