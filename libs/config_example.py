youtube_groups = {
    "group1": {
        "interval": 3,
        "channel_ids": [],
        "broadcast_types": ["none", "live"],
        "notify_member_only": False,  # Notify member-only streams
        "notifier_types": {
            "telegram": {
                "recipient_ids": [],
                "word_list": [],
            },
            "discord": {
                "webhook_urls": [],
                "word_list": [],
            },
        },
    },
}

twitch_groups = {
    "group1": {
        "interval": 3,
        "channel_ids": [],
        "notifier_types": {
            "telegram": {
                "recipient_ids": [],
                "word_list": [],
            },
            "discord": {
                "webhook_urls": [],
                "word_list": [],
            },
        },
    },
}
