from libs.utils.config_check import check_groups


def make_group(**overrides):
    group = {
        "interval": 3,
        "channel_ids": [],
        "notifier_types": {
            "telegram": {"recipient_ids": [], "word_list": []},
            "discord": {"webhook_urls": [], "word_list": []},
        },
    }
    group.update(overrides)
    return group


def test_valid_group_passes():
    assert check_groups("twitch", {"g": make_group()}) == ([], [])


def test_missing_keys_are_errors():
    group = make_group(notifier_types={"telegram": {"recipient_ids": []}})
    del group["channel_ids"]

    errors, _ = check_groups("twitch", {"g": group})

    assert len(errors) == 2
    assert any("'channel_ids'" in error for error in errors)
    assert any("'word_list'" in error for error in errors)


def test_bad_interval_and_unknown_values_are_errors():
    group = make_group(
        interval=0,
        broadcast_types=["live", "replay"],
        notifier_types={"line": {}},
    )

    errors, _ = check_groups("youtube", {"g": group})

    assert len(errors) == 3


def test_uneven_interval_and_empty_broadcast_types_are_warnings():
    group = make_group(interval=7, broadcast_types=[])

    errors, warnings = check_groups("youtube", {"g": group})

    assert errors == []
    assert len(warnings) == 2


def test_upcoming_broadcast_type_is_a_warning():
    group = make_group(broadcast_types=["live", "upcoming"])

    errors, warnings = check_groups("youtube", {"g": group})

    assert errors == []
    assert len(warnings) == 1
    assert "'upcoming' has no effect" in warnings[0]
