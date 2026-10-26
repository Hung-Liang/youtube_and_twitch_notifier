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


def test_video_in_both_playlists_is_returned_once(monkeypatch):
    patch_youtube(monkeypatch, ["v1"], {"v1": make_video("v1", "live")})

    results = tools.get_multiple_live_title_and_url(
        {"UC1": "UU1", "UC1_member": "UUMO1"}, ["live"], "g"
    )

    assert len(results) == 1
