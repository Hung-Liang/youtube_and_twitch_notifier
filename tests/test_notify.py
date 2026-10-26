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


def test_fallback_only_on_bad_request(monkeypatch, handler, alerts):
    FakeHandler.replies = {"a": 400, "b": 500}

    run_notify(monkeypatch, telegram_config("a", "b"), [make_result([])])

    assert [user for user, _ in handler[0].sent] == ["a", "a", "b"]


def test_rate_limit_waits_then_resends_same_message(
    monkeypatch, handler, alerts
):
    waits = []
    monkeypatch.setattr(notify.time, "sleep", waits.append)

    replies = iter([429, True])

    def send_message(self, user, message):
        self.sent.append((user, message))
        reply = next(replies)
        self.last_status_code = 200 if reply is True else reply
        self.last_retry_after = 5
        return reply is True

    monkeypatch.setattr(FakeHandler, "send_message", send_message)
    marked = []

    run_notify(monkeypatch, telegram_config("a"), [make_result(marked)])

    assert waits == [5]
    sent = handler[0].sent
    assert len(sent) == 2 and sent[0] == sent[1]
    assert marked == [True]


def test_rate_limit_too_long_is_not_waited(monkeypatch, handler, alerts):
    waits = []
    monkeypatch.setattr(notify.time, "sleep", waits.append)

    def send_message(self, user, message):
        self.sent.append((user, message))
        self.last_status_code = 429
        self.last_retry_after = notify.MAX_RETRY_AFTER + 1
        return False

    monkeypatch.setattr(FakeHandler, "send_message", send_message)

    run_notify(monkeypatch, telegram_config("a"), [make_result([])])

    assert waits == []
    assert len(handler[0].sent) == 1


def test_not_found_skips_fallback(monkeypatch, handler, alerts):
    FakeHandler.replies = {"a": 404}

    run_notify(monkeypatch, telegram_config("a"), [make_result([])])

    assert len(handler[0].sent) == 1
    assert "404" in alerts[0]


def test_fallback_drops_title(monkeypatch, handler, alerts):
    replies = iter([400, True])

    def send_message(self, user, message):
        self.sent.append((user, message))
        reply = next(replies)
        self.last_status_code = 200 if reply is True else reply
        return reply is True

    monkeypatch.setattr(FakeHandler, "send_message", send_message)
    marked = []

    run_notify(monkeypatch, telegram_config("a"), [make_result(marked)])

    first, fallback = [message for _, message in handler[0].sent]
    assert "title" in first
    assert "title" not in fallback
    assert marked == [True]
    assert alerts == []


def test_discord_sends_to_webhooks(monkeypatch, handler, alerts):
    discord = []

    def factory():
        instance = FakeHandler()
        discord.append(instance)
        return instance

    monkeypatch.setattr(notify, "DiscordHandler", factory)
    notifier_types = {
        "discord": {"webhook_urls": ["https://hook"], "word_list": ["hi"]}
    }

    run_notify(monkeypatch, notifier_types, [make_result([])])

    assert discord[0].sent == [("https://hook", "hi\n\n[title](https://x)")]


def test_unknown_notifier_raises(monkeypatch, handler, alerts):
    with pytest.raises(ValueError):
        run_notify(
            monkeypatch,
            {"line": {"word_list": []}},
            [make_result([])],
        )


def test_one_recipient_success_marks_even_if_other_type_fails(
    monkeypatch, handler, alerts
):
    def failing_discord():
        instance = FakeHandler()
        instance.replies = {"https://hook": 500}
        return instance

    monkeypatch.setattr(notify, "DiscordHandler", failing_discord)
    notifier_types = {
        **telegram_config("a"),
        "discord": {"webhook_urls": ["https://hook"], "word_list": []},
    }
    marked = []

    run_notify(monkeypatch, notifier_types, [make_result(marked)])

    assert marked == [True]


def test_youtube_uses_default_broadcast_types(monkeypatch, handler, alerts):
    seen = {}

    def get_multiple_upload_id(channel_ids, include_member_only):
        seen["member"] = include_member_only
        return {"UC1": "UU1"}

    def get_multiple_live(upload_ids, broadcast_types, group):
        seen["broadcast_types"] = broadcast_types
        return []

    monkeypatch.setattr(
        notify, "get_multiple_upload_id", get_multiple_upload_id
    )
    monkeypatch.setattr(
        notify, "get_multiple_live_title_and_url", get_multiple_live
    )

    notify.send_notify(
        "youtube",
        "g",
        {"channel_ids": ["UC1"], "notifier_types": telegram_config("a")},
    )

    assert seen == {"member": False, "broadcast_types": ["none", "live"]}
    assert handler == []
