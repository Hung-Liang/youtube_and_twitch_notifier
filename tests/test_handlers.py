import pytest

from libs.handler import discord_handler, telegram_handler, youtube_handler
from libs.utils import tools


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body
        self.text = str(body)

    def json(self):
        if isinstance(self.body, Exception):
            raise self.body
        return self.body


def patch_post(monkeypatch, module, response):
    monkeypatch.setattr(
        module.requests, "post", lambda *args, **kwargs: response
    )


def test_telegram_reads_retry_after(monkeypatch):
    patch_post(
        monkeypatch,
        telegram_handler,
        FakeResponse(429, {"ok": False, "parameters": {"retry_after": 7}}),
    )
    handler = telegram_handler.TelegramHandler()

    assert handler.send_message("1", "hi") is False
    assert handler.last_retry_after == 7


def test_discord_reads_retry_after(monkeypatch):
    patch_post(
        monkeypatch, discord_handler, FakeResponse(429, {"retry_after": 1.5})
    )
    handler = discord_handler.DiscordHandler()

    assert handler.send_message("https://hook", "hi") is False
    assert handler.last_retry_after == 1.5


def test_retry_after_is_none_when_body_is_not_json(monkeypatch):
    patch_post(
        monkeypatch, discord_handler, FakeResponse(429, ValueError("html"))
    )
    handler = discord_handler.DiscordHandler()

    handler.send_message("https://hook", "hi")

    assert handler.last_retry_after is None


QUOTA_BODY = {"error": {"errors": [{"reason": "quotaExceeded"}]}}


@pytest.fixture
def youtube(monkeypatch):
    """Fake YouTube where keys listed in `out_of_quota` return 403."""
    monkeypatch.setattr(youtube_handler, "_exhausted_keys", {})
    monkeypatch.setattr(youtube_handler, "_quota_alert_day", None)
    monkeypatch.setattr(youtube_handler.random, "shuffle", lambda x: None)

    alerts = []
    monkeypatch.setattr(tools, "send_exception_log", alerts.append)

    state = {"out_of_quota": set(), "used": [], "alerts": alerts}

    def get(url, headers, timeout):
        key = headers["X-goog-api-key"]
        state["used"].append(key)
        if key in state["out_of_quota"]:
            return FakeResponse(403, QUOTA_BODY)
        return FakeResponse(200, {"items": []})

    monkeypatch.setattr(youtube_handler.requests, "get", get)
    return state


def test_youtube_switches_key_on_quota_exceeded(monkeypatch, youtube):
    monkeypatch.setenv("youtube_api_token", "k1,k2")
    youtube["out_of_quota"] = {"k1"}

    res = youtube_handler.YoutubeHandler().request("https://yt")
    assert res.status_code == 200
    assert youtube["used"] == ["k1", "k2"]

    # Exhausted key is skipped for the rest of the quota day
    youtube_handler.YoutubeHandler().request("https://yt")
    assert youtube["used"] == ["k1", "k2", "k2"]
    assert youtube["alerts"] == []


def test_youtube_alerts_once_per_day_when_all_keys_out(monkeypatch, youtube):
    monkeypatch.setenv("youtube_api_token", "k1,k2")
    youtube["out_of_quota"] = {"k1", "k2"}

    for _ in range(3):
        res = youtube_handler.YoutubeHandler().request("https://yt")
        assert res.status_code == 403

    assert len(youtube["alerts"]) == 1


def test_other_403_does_not_switch_key(monkeypatch, youtube):
    monkeypatch.setenv("youtube_api_token", "k1,k2")
    monkeypatch.setattr(
        youtube_handler.requests,
        "get",
        lambda url, headers, timeout: FakeResponse(403, {"error": {}}),
    )

    res = youtube_handler.YoutubeHandler().request("https://yt")

    assert res.status_code == 403
    assert youtube_handler._exhausted_keys == {}
