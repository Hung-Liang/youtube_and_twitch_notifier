import pytest
import requests

from libs.utils import tools


def make_video(video_id, status, title="title", channel="channel"):
    return {
        "id": video_id,
        "snippet": {
            "liveBroadcastContent": status,
            "title": title,
            "channelTitle": channel,
        },
    }


def patch_youtube(monkeypatch, playlist, videos):
    """Fake YoutubeHandler responses.

    `playlist`: video ids returned by playlistItems, newest first.
    `videos`: video info items keyed by id.
    """

    def find_recent_video(self, playlist_id, part="contentDetails",
                          max_results=3):
        return [
            {"contentDetails": {"videoId": video_id}}
            for video_id in playlist[:max_results]
        ]

    def get_video_info(self, video_id, part="snippet"):
        ids = video_id.split(",")
        return {"items": [videos[i] for i in ids if i in videos]}

    monkeypatch.setattr(
        tools.YoutubeHandler, "find_recent_video", find_recent_video
    )
    monkeypatch.setattr(tools.YoutubeHandler, "get_video_info", get_video_info)


def test_get_message_telegram_escapes_html():
    message = tools.get_message(
        "telegram", "a<b>&c", "https://x", "ch", []
    )
    assert message == "<b>ch\na&lt;b&gt;&amp;c\nhttps://x</b>"


def test_get_message_discord_uses_word_list():
    message = tools.get_message(
        "discord", "title", "https://x", "ch", ["hello"]
    )
    assert message == "hello\n\n[title](https://x)"


def test_save_json_leaves_no_temp_file(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    path = folder / "a.json"
    tools.save_json(path, {"a": 1})
    tools.save_json(path, {"b": "中"})

    assert tools.load_json(path) == {"b": "中"}
    assert [p.name for p in folder.iterdir()] == ["a.json"]


def test_load_ignore_json_keeps_last_50_when_over_100(tmp_path):
    path = tmp_path / "ignore.json"
    tools.save_json(path, {str(i): i for i in range(101)})

    ignore_list = tools.load_ignore_json(path)

    assert list(ignore_list) == [str(i) for i in range(51, 101)]


def test_live_video_is_returned_once(monkeypatch):
    patch_youtube(
        monkeypatch,
        ["v1", "v2"],
        {"v1": make_video("v1", "live"), "v2": make_video("v2", "none")},
    )

    first = tools.get_live_title_and_url("UU1", "g", ["live"])
    assert [r[:3] for r in first] == [
        ("title", "https://www.youtube.com/watch?v=v1", "channel")
    ]

    # Not marked yet, so it is returned again
    assert len(tools.get_live_title_and_url("UU1", "g", ["live"])) == 1

    first[0][3]()
    assert tools.get_live_title_and_url("UU1", "g", ["live"]) == []


def test_all_upcoming_fetches_more_videos(monkeypatch):
    playlist = ["u1", "u2", "u3", "v4"]
    videos = {i: make_video(i, "upcoming") for i in ["u1", "u2", "u3"]}
    videos["v4"] = make_video("v4", "none")
    patch_youtube(monkeypatch, playlist, videos)

    results = tools.get_live_title_and_url("UU1", "g", ["none"])

    assert [r[1] for r in results] == [
        "https://www.youtube.com/watch?v=v4"
    ]


def test_all_upcoming_fetch_stops_at_api_limit(monkeypatch):
    playlist = [f"u{i}" for i in range(60)]
    patch_youtube(
        monkeypatch, playlist, {i: make_video(i, "upcoming") for i in playlist}
    )
    requested = []
    fake_find = tools.YoutubeHandler.find_recent_video

    def find_recent_video(self, playlist_id, part="contentDetails",
                          max_results=3):
        requested.append(max_results)
        return fake_find(self, playlist_id, part, max_results)

    monkeypatch.setattr(
        tools.YoutubeHandler, "find_recent_video", find_recent_video
    )

    assert tools.get_live_title_and_url("UU1", "g", ["live"]) == []
    assert max(requested) == tools.YOUTUBE_MAX_RESULTS


def test_upcoming_pushed_out_of_playlist_is_notified_when_live(
    monkeypatch, isolate
):
    patch_youtube(monkeypatch, ["u1"], {"u1": make_video("u1", "upcoming")})
    assert tools.get_live_title_and_url("UU1", "g", ["live"]) == []
    assert tools.load_json(isolate / "upcoming" / "g" / "UU1.json") == {
        "u1": "title"
    }

    # Newer uploads push u1 out of the recent items before it goes live
    videos = {i: make_video(i, "none") for i in ["v1", "v2", "v3"]}
    videos["u1"] = make_video("u1", "live")
    patch_youtube(monkeypatch, ["v1", "v2", "v3", "u1"], videos)

    results = tools.get_live_title_and_url("UU1", "g", ["live"])
    assert [r[1] for r in results] == [
        "https://www.youtube.com/watch?v=u1"
    ]

    # Still tracked until delivered, then dropped on the next run
    results[0][3]()
    assert tools.get_live_title_and_url("UU1", "g", ["live"]) == []
    assert tools.load_json(isolate / "upcoming" / "g" / "UU1.json") == {}


def test_tracked_upcoming_member_only_keeps_prefix(monkeypatch):
    patch_youtube(monkeypatch, ["u1"], {"u1": make_video("u1", "upcoming")})
    tools.get_live_title_and_url(
        "UUMO1", "g", ["live"], is_member_only=True, channel_id="UC1"
    )

    patch_youtube(
        monkeypatch,
        ["v1", "v2", "v3"],
        {
            **{i: make_video(i, "none") for i in ["v1", "v2", "v3"]},
            "u1": make_video("u1", "live"),
        },
    )
    results = tools.get_live_title_and_url(
        "UUMO1", "g", ["live"], is_member_only=True, channel_id="UC1"
    )

    assert [r[0] for r in results] == ["【Member Only】\ntitle"]


def test_tracked_upcoming_is_dropped_when_unwanted_or_gone(
    monkeypatch, isolate
):
    upcoming_json = isolate / "upcoming" / "g" / "UU1.json"
    upcoming_json.parent.mkdir()
    tools.save_json(upcoming_json, {"ended": "t", "deleted": "t"})
    patch_youtube(monkeypatch, ["v1"], {
        "v1": make_video("v1", "none"),
        "ended": make_video("ended", "none"),
    })

    assert tools.get_live_title_and_url("UU1", "g", ["live"]) == []
    assert tools.load_json(upcoming_json) == {}


def test_tracked_upcoming_kept_when_video_info_fails(monkeypatch, isolate):
    upcoming_json = isolate / "upcoming" / "g" / "UU1.json"
    upcoming_json.parent.mkdir()
    tools.save_json(upcoming_json, {"u1": "t"})
    patch_youtube(monkeypatch, [], {})
    monkeypatch.setattr(
        tools.YoutubeHandler, "get_video_info", lambda *a, **k: None
    )

    assert tools.get_live_title_and_url("UU1", "g", ["live"]) == []
    assert tools.load_json(upcoming_json) == {"u1": "t"}


def test_video_in_both_playlists_is_returned_once(monkeypatch):
    patch_youtube(monkeypatch, ["v1"], {"v1": make_video("v1", "live")})

    results = tools.get_multiple_live_title_and_url(
        {"UC1": "UU1", "UC1_member": "UUMO1"}, ["live"], "g"
    )

    assert len(results) == 1


def test_exception_message_escapes_html():
    message = tools.format_exception_message("File <module> & co")

    assert message == (
        "<b>[Exception]</b>\n<pre>File &lt;module&gt; &amp; co</pre>"
    )


def test_exception_message_keeps_tail_within_limit():
    text = "start\n" + "<&>" * 5000 + "\nValueError: boom"

    message = tools.format_exception_message(text)

    assert len(message) <= tools.TELEGRAM_MESSAGE_LIMIT
    assert "ValueError: boom</pre>" in message
    assert "start" not in message


def test_exception_log_sends_text_message(monkeypatch):
    sent = []

    class FakeTelegram:
        def send_message(self, cid, message):
            sent.append(message)
            return True

    monkeypatch.setattr(tools, "TelegramHandler", FakeTelegram)

    tools.send_exception_log("boom")

    assert sent == ["<b>[Exception]</b>\n<pre>boom</pre>"]


def test_get_message_unknown_type_raises():
    with pytest.raises(ValueError):
        tools.get_message("line", "t", "https://x", "ch", [])


def test_load_ignore_json_creates_missing_file(tmp_path):
    path = tmp_path / "new.json"

    assert tools.load_ignore_json(path) == {}
    assert tools.load_json(path) == {}


def test_broadcast_types_filter_videos(monkeypatch):
    patch_youtube(
        monkeypatch,
        ["v1", "v2"],
        {"v1": make_video("v1", "live"), "v2": make_video("v2", "none")},
    )

    results = tools.get_live_title_and_url("UU1", "g", ["none"])

    assert [r[1] for r in results] == ["https://www.youtube.com/watch?v=v2"]


def test_member_only_title_and_shared_ignore_file(monkeypatch, isolate):
    patch_youtube(monkeypatch, ["v1"], {"v1": make_video("v1", "live")})

    results = tools.get_live_title_and_url(
        "UUMO1", "g", ["live"], is_member_only=True, channel_id="UC1"
    )
    results[0][3]()

    assert results[0][0] == "【Member Only】\ntitle"
    ignore = tools.load_json(isolate / "ignore" / "g" / "UC1.json")
    assert ignore == {"v1": "【Member Only】\ntitle"}


def test_video_without_info_is_skipped(monkeypatch):
    patch_youtube(monkeypatch, ["v1"], {})

    assert tools.get_live_title_and_url("UU1", "g", ["live"]) == []


def test_no_videos_returns_empty(monkeypatch):
    monkeypatch.setattr(
        tools.YoutubeHandler, "find_recent_video", lambda *a, **k: None
    )

    assert tools.get_live_title_and_url("UU1", "g", ["live"]) == []


def test_ignored_video_info_is_not_fetched(monkeypatch, isolate):
    patch_youtube(monkeypatch, ["v1"], {"v1": make_video("v1", "live")})
    group_path = isolate / "ignore" / "g"
    group_path.mkdir()
    tools.save_json(group_path / "UU1.json", {"v1": "title"})

    def get_video_info(self, video_id, part="snippet"):
        raise AssertionError("ignored video should not be fetched")

    monkeypatch.setattr(tools.YoutubeHandler, "get_video_info", get_video_info)

    assert tools.get_live_title_and_url("UU1", "g", ["live"]) == []


def test_get_upload_id_derives_from_channel_id():
    assert tools.get_upload_id("UC1") == "UU1"


def test_get_upload_id_rejects_non_uc_channel():
    assert tools.get_upload_id("XX1") is None


def test_get_multiple_upload_id_adds_member_playlist(monkeypatch):
    monkeypatch.setattr(tools, "get_upload_id", lambda c: "UU" + c[2:])

    assert tools.get_multiple_upload_id(["UC1"]) == {"UC1": "UU1"}
    assert tools.get_multiple_upload_id(["UC1"], True) == {
        "UC1": "UU1",
        "UC1_member": "UUMO1",
    }


def test_member_playlist_requires_uc_prefix():
    handler = tools.YoutubeHandler()

    assert handler.get_member_only_playlist_id("UC123") == "UUMO123"
    assert handler.get_member_only_playlist_id("XX123") is None


def patch_twitch(monkeypatch, streams):
    monkeypatch.setattr(
        tools,
        "TwitchHandler",
        lambda: type("FakeTwitch", (), {
            "get_stream_infos": lambda self, usernames: streams,
        })(),
    )


def make_stream(stream_id, login="chu"):
    return {
        "is_live": True,
        "title": "live!",
        "stream_id": stream_id,
        "user_login": login,
        "user_name": "Chu",
    }


def test_twitch_skips_query_without_channels(monkeypatch):
    def fail():
        raise AssertionError("twitch should not be queried")

    monkeypatch.setattr(tools, "TwitchHandler", fail)

    assert tools.get_multiple_twitch_title_and_url([], "g") == []


def test_twitch_stream_is_returned_until_marked(monkeypatch):
    patch_twitch(monkeypatch, [make_stream("s1")])

    first = tools.get_multiple_twitch_title_and_url(["chu"], "g")
    assert [r[:3] for r in first] == [
        ("live!", "https://www.twitch.tv/chu", "Chu")
    ]

    first[0][3]()
    assert tools.get_multiple_twitch_title_and_url(["chu"], "g") == []

    # A new stream id is a new broadcast
    patch_twitch(monkeypatch, [make_stream("s2")])
    assert len(tools.get_multiple_twitch_title_and_url(["chu"], "g")) == 1


class FakeTelegramDocument:
    sent = []
    succeed = True

    def send_document(self, cid, path, filename):
        self.sent.append(filename)
        return self.succeed, {}


def test_daily_log_uploads_past_logs_only(monkeypatch, isolate):
    log_path = isolate / "log"
    today = tools.get_log_filename()
    for name in ["2026-01-01.log", "2026-01-02.log", today]:
        (log_path / name).write_text("x", encoding="utf-8")

    FakeTelegramDocument.sent = []
    FakeTelegramDocument.succeed = True
    monkeypatch.setattr(tools, "TelegramHandler", FakeTelegramDocument)

    tools.send_daily_log()

    assert FakeTelegramDocument.sent == [
        "[Daily Log] 2026-01-01.log",
        "[Daily Log] 2026-01-02.log",
    ]
    assert [p.name for p in log_path.iterdir()] == [today]


def test_daily_log_keeps_file_when_upload_fails(monkeypatch, isolate):
    log_path = isolate / "log"
    (log_path / "2026-01-01.log").write_text("x", encoding="utf-8")

    FakeTelegramDocument.sent = []
    FakeTelegramDocument.succeed = False
    monkeypatch.setattr(tools, "TelegramHandler", FakeTelegramDocument)

    tools.send_daily_log()

    assert (log_path / "2026-01-01.log").exists()


def test_exception_log_survives_telegram_error(monkeypatch):
    class BrokenTelegram:
        def send_message(self, cid, message):
            raise requests.ConnectionError()

    monkeypatch.setattr(tools, "TelegramHandler", BrokenTelegram)

    tools.send_exception_log("boom")
