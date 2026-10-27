BROADCAST_TYPES = ("live", "upcoming", "none")

NOTIFIER_KEYS = {
    "telegram": ("recipient_ids", "word_list"),
    "discord": ("webhook_urls", "word_list"),
}


def check_groups(platform, groups):
    """Check one platform's groups in the config file.

    Args:
        `platform`: "youtube" or "twitch"
        `groups`: Groups dict from the config file

    Returns:
        (errors, warnings): Lists of messages. Errors must stop startup.
    """
    errors = []
    warnings = []

    if not isinstance(groups, dict):
        return [f"{platform}_groups must be a dict"], warnings

    for group, config in groups.items():
        where = f"{platform}_groups[{group!r}]"

        if not isinstance(config, dict):
            errors.append(f"{where} must be a dict")
            continue

        interval = config.get("interval")
        if (
            not isinstance(interval, int)
            or isinstance(interval, bool)
            or interval <= 0
        ):
            errors.append(f"{where}['interval'] must be a positive int")
        elif 60 % interval != 0:
            # Cron restarts at minute 0, so the last gap of each hour is short
            warnings.append(
                f"{where}['interval'] = {interval} does not divide 60,"
                " polling gaps will be uneven"
            )

        if not isinstance(config.get("channel_ids"), list):
            errors.append(f"{where}['channel_ids'] must be a list")

        errors += check_notifier_types(where, config.get("notifier_types"))

        if platform == "youtube" and "broadcast_types" in config:
            broadcast_types = config["broadcast_types"]
            if not isinstance(broadcast_types, list):
                errors.append(f"{where}['broadcast_types'] must be a list")
            elif not broadcast_types:
                warnings.append(
                    f"{where}['broadcast_types'] is empty,"
                    " no youtube video will be notified"
                )
            else:
                for broadcast_type in broadcast_types:
                    if broadcast_type not in BROADCAST_TYPES:
                        errors.append(
                            f"{where}['broadcast_types'] has unknown value"
                            f" {broadcast_type!r}"
                        )
                if "upcoming" in broadcast_types:
                    warnings.append(
                        f"{where}['broadcast_types'] 'upcoming' has no"
                        " effect, waiting rooms are notified as 'live'"
                        " once they start"
                    )

    return errors, warnings


def check_notifier_types(where, notifier_types):
    if not isinstance(notifier_types, dict):
        return [f"{where}['notifier_types'] must be a dict"]

    errors = []
    for notifier_type, data in notifier_types.items():
        if notifier_type not in NOTIFIER_KEYS:
            errors.append(
                f"{where}['notifier_types'] has unknown type"
                f" {notifier_type!r}"
            )
            continue

        if not isinstance(data, dict):
            errors.append(
                f"{where}['notifier_types'][{notifier_type!r}] must be a dict"
            )
            continue

        for key in NOTIFIER_KEYS[notifier_type]:
            if not isinstance(data.get(key), list):
                errors.append(
                    f"{where}['notifier_types'][{notifier_type!r}][{key!r}]"
                    " must be a list"
                )

    return errors
