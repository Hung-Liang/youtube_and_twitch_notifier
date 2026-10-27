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

    `playlist`: video ids returned by playlistItems, newest first; a dict
        keyed by playlist id, or a list shared by every playlist.
    `videos`: video info items keyed by id.

    Returns:
        Calls made, as ("items", playlist_id, max_results) or
        ("videos", ids, part).
    """
    calls = []

    def find_recent_video(self, playlist_id, part="contentDetails",
                          max_results=3):
        calls.append(("items", playlist_id, max_results))
        ids = (
            playlist.get(playlist_id, [])
            if isinstance(playlist, dict)
            else playlist
        )
        return [
            {"contentDetails": {"videoId": video_id}}
            for video_id in ids[:max_results]
        ]

    def get_video_info(self, video_id, part="snippet"):
        ids = video_id.split(",")
        calls.append(("videos", ids, part))
        return {"items": [videos[i] for i in ids if i in videos]}

    monkeypatch.setattr(
        tools.YoutubeHandler, "find_recent_video", find_recent_video
    )
    monkeypatch.setattr(tools.YoutubeHandler, "get_video_info", get_video_info)
    return calls


def check_youtube(broadcast_types, upload_ids=None):
    return tools.get_multiple_live_title_and_url(
        upload_ids or {"UC1": "UU1"}, broadcast_types, "g"
    )


def read_ignore(isolate, channel_id="UC1"):
    return tools.load_json(isolate / "ignore" / "g" / f"{channel_id}.json")


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


def test_load_ignore_json_keeps_last_150_when_over_200(tmp_path):
    path = tmp_path / "ignore.json"
    tools.save_json(path, {str(i): i for i in range(201)})

    ignore_list = tools.load_ignore_json(path)

    assert list(ignore_list) == [str(i) for i in range(51, 201)]


def test_load_ignore_json_keeps_all_at_200(tmp_path):
    path = tmp_path / "ignore.json"
    tools.save_json(path, {str(i): i for i in range(200)})

    assert len(tools.load_ignore_json(path)) == 200


def test_live_video_is_returned_until_marked(monkeypatch):
    patch_youtube(monkeypatch, ["v1"], {"v1": make_video("v1", "live")})

    first = check_youtube(["live"])
    assert [r[:3] for r in first] == [
        ("title", "https://www.youtube.com/watch?v=v1", "channel")
    ]

    # Not marked yet, so it is returned again
    assert len(check_youtube(["live"])) == 1

    first[0][3]()
    assert check_youtube(["live"]) == []


def test_unwanted_video_is_ignored_with_skip_mark(monkeypatch, isolate):
    calls = patch_youtube(
        monkeypatch,
        ["v1", "v2"],
        {"v1": make_video("v1", "live"), "v2": make_video("v2", "none")},
    )

    results = check_youtube(["none"])

    assert [r[1] for r in results] == ["https://www.youtube.com/watch?v=v2"]
    assert read_ignore(isolate) == {"v1": "[skip] title"}

    calls.clear()
    check_youtube(["none"])
    assert ("videos", ["v2"], tools.YOUTUBE_VIDEO_PARTS) in calls


def test_upcoming_is_not_ignored_until_live(monkeypatch, isolate):
    patch_youtube(monkeypatch, ["u1"], {"u1": make_video("u1", "upcoming")})

    assert check_youtube(["live"]) == []
    assert read_ignore(isolate) == {}
    log_text = "".join(
        p.read_text(encoding="utf-8") for p in (isolate / "log").iterdir()
    )
    assert "[upcoming] g / UC1 / u1 / title" in log_text

    patch_youtube(monkeypatch, ["u1"], {"u1": make_video("u1", "live")})
    assert [r[1] for r in check_youtube(["live"])] == [
        "https://www.youtube.com/watch?v=u1"
    ]


def test_playlist_items_use_check_range(monkeypatch):
    calls = patch_youtube(monkeypatch, [], {})

    check_youtube(["live"])

    assert calls == [("items", "UU1", tools.YOUTUBE_CHECK_RANGE)]
    assert tools.YOUTUBE_CHECK_RANGE == 50


def test_group_videos_are_looked_up_together(monkeypatch):
    calls = patch_youtube(
        monkeypatch,
        {"UU1": ["a1", "a2"], "UU2": ["b1"]},
        {i: make_video(i, "live") for i in ["a1", "a2", "b1"]},
    )

    results = check_youtube(["live"], {"UC1": "UU1", "UC2": "UU2"})

    assert len(results) == 3
    assert [c for c in calls if c[0] == "videos"] == [
        ("videos", ["a1", "a2", "b1"], "snippet,liveStreamingDetails")
    ]


def test_group_lookup_is_batched_by_50(monkeypatch):
    calls = patch_youtube(
        monkeypatch,
        {
            "UU1": [f"a{i}" for i in range(50)],
            "UU2": [f"b{i}" for i in range(10)],
        },
        {},
    )

    check_youtube(["live"], {"UC1": "UU1", "UC2": "UU2"})

    assert [len(c[1]) for c in calls if c[0] == "videos"] == [50, 10]


def test_video_in_both_playlists_is_returned_once(monkeypatch):
    calls = patch_youtube(
        monkeypatch, ["v1"], {"v1": make_video("v1", "live")}
    )

    results = check_youtube(["live"], {"UC1": "UU1", "UC1_member": "UUMO1"})

    assert len(results) == 1
    assert [c[1] for c in calls if c[0] == "videos"] == [["v1"]]


def test_member_only_title_and_shared_ignore_file(monkeypatch, isolate):
    patch_youtube(
        monkeypatch, {"UUMO1": ["v1"]}, {"v1": make_video("v1", "live")}
    )

    results = check_youtube(["live"], {"UC1": "UU1", "UC1_member": "UUMO1"})
    results[0][3]()

    assert results[0][0] == "【Member Only】\ntitle"
    assert read_ignore(isolate) == {"v1": "【Member Only】\ntitle"}


def test_video_without_info_is_retried(monkeypatch, isolate):
    calls = patch_youtube(monkeypatch, ["v1"], {})

    assert check_youtube(["live"]) == []
    assert read_ignore(isolate) == {}

    calls.clear()
    check_youtube(["live"])
    assert [c[1] for c in calls if c[0] == "videos"] == [["v1"]]


def test_no_videos_returns_empty(monkeypatch):
    monkeypatch.setattr(
        tools.YoutubeHandler, "find_recent_video", lambda *a, **k: None
    )

    assert check_youtube(["live"]) == []


def test_ignored_video_info_is_not_fetched(monkeypatch, isolate):
    patch_youtube(monkeypatch, ["v1"], {"v1": make_video("v1", "live")})
    group_path = isolate / "ignore" / "g"
    group_path.mkdir()
    tools.save_json(group_path / "UC1.json", {"v1": "title"})

    def get_video_info(self, video_id, part="snippet"):
        raise AssertionError("ignored video should not be fetched")

    monkeypatch.setattr(tools.YoutubeHandler, "get_video_info", get_video_info)

    assert check_youtube(["live"]) == []


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


@pytest.fixture
def admin_alerts(monkeypatch):
    sent = []
    monkeypatch.setattr(tools, "send_exception_log", sent.append)
    return sent


def test_youtube_baseline_ignores_all_but_upcoming(monkeypatch, isolate):
    patch_youtube(monkeypatch, ["u1", "v1", "v2", "gone"], {
        "u1": make_video("u1", "upcoming"),
        "v1": make_video("v1", "live"),
        "v2": make_video("v2", "none", title="old"),
    })

    assert tools.baseline_youtube_group({"UC1": "UU1"}, "g") == []
    assert read_ignore(isolate) == {
        "v1": "[baseline] title",
        "v2": "[baseline] old",
    }
    assert check_youtube(["live", "none"]) == []

    patch_youtube(monkeypatch, ["u1"], {"u1": make_video("u1", "live")})
    assert [r[1] for r in check_youtube(["live"])] == [
        "https://www.youtube.com/watch?v=u1"
    ]


def test_youtube_baseline_merges_into_existing_ignore(monkeypatch, isolate):
    group_path = isolate / "ignore" / "g"
    group_path.mkdir()
    tools.save_json(group_path / "UC1.json", {"old": "title"})
    patch_youtube(monkeypatch, ["v1"], {"v1": make_video("v1", "none")})

    tools.baseline_youtube_group({"UC1": "UU1"}, "g")

    assert read_ignore(isolate) == {"old": "title", "v1": "[baseline] title"}


def test_youtube_baseline_fails_when_video_lookup_fails(
    monkeypatch, isolate
):
    patch_youtube(monkeypatch, ["v1"], {})
    monkeypatch.setattr(
        tools.YoutubeHandler, "get_video_info", lambda *a, **k: None
    )

    assert tools.baseline_youtube_group({"UC1": "UU1"}, "g") == ["UU1"]
    assert read_ignore(isolate) == {}


def test_failed_youtube_baseline_is_retried_before_notifying(
    monkeypatch, isolate, admin_alerts
):
    patch_youtube(monkeypatch, {}, {})
    monkeypatch.setattr(
        tools.YoutubeHandler,
        "find_recent_video",
        lambda self, playlist_id, **k: (
            None if playlist_id == "UU1"
            else [{"contentDetails": {"videoId": "b1"}}]
        ),
    )

    tools.init_youtube_baseline({"UC1": "UU1", "UC2": "UU2"}, "g")

    assert tools._pending_baselines == {("youtube", "g", "UU1")}
    assert len(admin_alerts) == 1
    assert "UU1" in admin_alerts[0]

    # The retry ignores what is live now instead of notifying it
    videos = {"a1": make_video("a1", "live"), "b2": make_video("b2", "live")}
    patch_youtube(monkeypatch, {"UU1": ["a1"], "UU2": ["b2", "b1"]}, videos)
    results = check_youtube(["live"], {"UC1": "UU1", "UC2": "UU2"})

    assert [r[1] for r in results] == ["https://www.youtube.com/watch?v=b2"]
    assert tools._pending_baselines == set()
    assert read_ignore(isolate) == {"a1": "[baseline] title"}
    assert len(admin_alerts) == 1

    videos["a2"] = make_video("a2", "live")
    patch_youtube(monkeypatch, {"UU1": ["a2", "a1"]}, videos)
    assert [r[1] for r in check_youtube(["live"])] == [
        "https://www.youtube.com/watch?v=a2"
    ]


def test_youtube_baseline_succeeds_on_empty_playlist(monkeypatch):
    patch_youtube(monkeypatch, {"UU1": ["v1"]}, {})

    assert tools.baseline_youtube_group(
        {"UC1": "UU1", "UC1_member": "UUMO1"}, "g"
    ) == []


def test_youtube_baseline_exception_marks_group_pending(
    monkeypatch, admin_alerts
):
    def find_recent_video(*args, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(
        tools.YoutubeHandler, "find_recent_video", find_recent_video
    )

    tools.init_youtube_baseline({"UC1": "UU1", "UC1_member": "UUMO1"}, "g")

    assert tools._pending_baselines == {
        ("youtube", "g", "UU1"),
        ("youtube", "g", "UUMO1"),
    }
    assert "ConnectionError: down" in admin_alerts[0]


def test_youtube_baseline_success_sends_no_alert(monkeypatch, admin_alerts):
    patch_youtube(monkeypatch, [], {})

    tools.init_youtube_baseline({"UC1": "UU1"}, "g")

    assert tools._pending_baselines == set()
    assert admin_alerts == []


def test_twitch_baseline_ignores_live_streams(monkeypatch, isolate):
    patch_twitch(monkeypatch, [make_stream("s1")])

    tools.init_twitch_baseline(["chu"], "g")

    assert read_ignore(isolate, "chu") == {"s1": "[baseline] live!"}
    assert tools.get_multiple_twitch_title_and_url(["chu"], "g") == []


def test_twitch_baseline_skips_query_without_channels(monkeypatch):
    def fail():
        raise AssertionError("twitch should not be queried")

    monkeypatch.setattr(tools, "TwitchHandler", fail)

    tools.init_twitch_baseline([], "g")

    assert tools._pending_baselines == set()


def test_failed_twitch_baseline_is_retried_before_notifying(
    monkeypatch, isolate, admin_alerts
):
    def broken():
        raise Exception("Twitch API Error: 500")

    monkeypatch.setattr(tools, "TwitchHandler", broken)
    tools.init_twitch_baseline(["chu"], "g")

    assert tools._pending_baselines == {("twitch", "g")}
    assert "Twitch API Error: 500" in admin_alerts[0]

    # A failed retry raises to the job error listener and stays pending
    with pytest.raises(Exception, match="500"):
        tools.get_multiple_twitch_title_and_url(["chu"], "g")
    assert tools._pending_baselines == {("twitch", "g")}

    patch_twitch(monkeypatch, [make_stream("s1")])
    assert tools.get_multiple_twitch_title_and_url(["chu"], "g") == []
    assert tools._pending_baselines == set()
    assert read_ignore(isolate, "chu") == {"s1": "[baseline] live!"}

    patch_twitch(monkeypatch, [make_stream("s2")])
    assert len(tools.get_multiple_twitch_title_and_url(["chu"], "g")) == 1
