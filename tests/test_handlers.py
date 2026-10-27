import json

import pytest
import requests

from libs.handler import (
    discord_handler,
    telegram_handler,
    twitch_handler,
    youtube_handler,
)
from libs.utils import tools


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body
        self.text = (
            str(body) if isinstance(body, Exception) else json.dumps(body)
        )

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


def test_youtube_error_responses_return_none(monkeypatch):
    monkeypatch.setattr(
        youtube_handler.requests,
        "get",
        lambda url, headers, timeout: FakeResponse(500, {}),
    )
    handler = youtube_handler.YoutubeHandler()

    assert handler.find_recent_video("UU1") is None
    assert handler.get_video_info("v1") is None


def test_youtube_network_error_returns_none(monkeypatch):
    def get(url, headers, timeout):
        raise requests.exceptions.SSLError("EOF occurred")

    monkeypatch.setattr(youtube_handler.requests, "get", get)
    handler = youtube_handler.YoutubeHandler()

    assert handler.request("https://yt") is None
    assert handler.find_recent_video("UU1") is None
    assert handler.get_video_info("v1") is None


def test_youtube_missing_playlist_returns_empty(monkeypatch):
    body = {"error": {"errors": [{"reason": "playlistNotFound"}]}}
    monkeypatch.setattr(
        youtube_handler.requests,
        "get",
        lambda url, headers, timeout: FakeResponse(404, body),
    )

    assert youtube_handler.YoutubeHandler().find_recent_video("UUMO1") == []


def test_youtube_other_not_found_returns_none(monkeypatch):
    monkeypatch.setattr(
        youtube_handler.requests,
        "get",
        lambda url, headers, timeout: FakeResponse(404, {"error": {}}),
    )

    assert youtube_handler.YoutubeHandler().find_recent_video("UU1") is None


def test_youtube_missing_token_raises(monkeypatch):
    monkeypatch.delenv("youtube_api_token")

    with pytest.raises(ValueError):
        youtube_handler.YoutubeHandler()


def test_youtube_key_is_sent_in_header_not_url(monkeypatch):
    requests_seen = []

    def get(url, headers, timeout):
        requests_seen.append((url, headers))
        return FakeResponse(200, {"items": []})

    monkeypatch.setattr(youtube_handler.requests, "get", get)

    youtube_handler.YoutubeHandler().find_recent_video("UU1")

    url, headers = requests_seen[0]
    assert headers == {"X-goog-api-key": "key1"}
    assert "key1" not in url


def test_telegram_send_document_returns_body(monkeypatch, tmp_path):
    path = tmp_path / "a.log"
    path.write_text("x", encoding="utf-8")
    patch_post(
        monkeypatch, telegram_handler, FakeResponse(200, {"ok": True})
    )

    sent, body = telegram_handler.TelegramHandler().send_document(
        "1", path, "a.log"
    )

    assert sent is True
    assert body == {"ok": True}


@pytest.fixture
def twitch(monkeypatch):
    """Fake Twitch API; `valid_token` is the token streams accept."""
    monkeypatch.setattr(twitch_handler, "_access_token", None)
    state = {"tokens_issued": 0, "valid_token": "t1", "stream_calls": 0}

    def post(url, params, timeout):
        state["tokens_issued"] += 1
        return FakeResponse(
            200, {"access_token": f"t{state['tokens_issued']}"}
        )

    def get(url, headers, params, timeout):
        state["stream_calls"] += 1
        if headers["Authorization"] != f"Bearer {state['valid_token']}":
            return FakeResponse(401, {})
        return FakeResponse(
            200,
            {
                "data": [
                    {
                        "title": "live!",
                        "id": "s1",
                        "user_login": "chu",
                        "user_name": "Chu",
                    }
                ]
            },
        )

    monkeypatch.setattr(twitch_handler.requests, "post", post)
    monkeypatch.setattr(twitch_handler.requests, "get", get)
    return state


def test_twitch_token_is_shared_across_instances(twitch):
    twitch_handler.TwitchHandler()
    twitch_handler.TwitchHandler()

    assert twitch["tokens_issued"] == 1


def test_twitch_refreshes_token_on_401(twitch):
    handler = twitch_handler.TwitchHandler()
    twitch["valid_token"] = "t2"

    streams = handler.get_stream_infos(["chu"])

    assert twitch["tokens_issued"] == 2
    assert twitch["stream_calls"] == 2
    assert streams == [
        {
            "is_live": True,
            "title": "live!",
            "stream_id": "s1",
            "user_login": "chu",
            "user_name": "Chu",
        }
    ]


def test_twitch_splits_user_logins_into_batches(twitch, monkeypatch):
    requested = []

    def get(url, headers, params, timeout):
        requested.append(params)
        return FakeResponse(
            200,
            {
                "data": [
                    {
                        "title": "live!",
                        "id": f"s{params['user_login'][0]}",
                        "user_login": params["user_login"][0],
                        "user_name": "Chu",
                    }
                ]
            },
        )

    monkeypatch.setattr(twitch_handler.requests, "get", get)
    usernames = [f"u{i}" for i in range(250)]

    streams = twitch_handler.TwitchHandler().get_stream_infos(usernames)

    assert [len(p["user_login"]) for p in requested] == [100, 100, 50]
    assert [p["first"] for p in requested] == [100, 100, 50]
    assert [s["user_login"] for s in streams] == ["u0", "u100", "u200"]


def test_twitch_error_raises(twitch, monkeypatch):
    monkeypatch.setattr(
        twitch_handler.requests,
        "get",
        lambda url, headers, params, timeout: FakeResponse(500, {}),
    )

    with pytest.raises(Exception, match="Twitch API Error: 500"):
        twitch_handler.TwitchHandler().get_stream_infos(["chu"])


def test_twitch_token_error_raises(monkeypatch):
    monkeypatch.setattr(twitch_handler, "_access_token", None)
    monkeypatch.setattr(
        twitch_handler.requests,
        "post",
        lambda url, params, timeout: FakeResponse(400, {}),
    )

    with pytest.raises(Exception, match="Twitch API Error: 400"):
        twitch_handler.TwitchHandler()
