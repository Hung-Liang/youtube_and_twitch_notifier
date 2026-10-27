import os
import runpy
from pathlib import Path

from libs.utils.file_path import CONFIG_PATH, DEV_CONFIG_PATH
from libs.utils.logger import log


def get_config_path():
    """Get the config path for the current APP_ENV.

    Returns:
        `dev_config.py` when APP_ENV is "dev", otherwise `config.py`
    """
    # Read at call time, .env is loaded after file_path is imported
    if os.environ.get("APP_ENV") == "dev":
        return DEV_CONFIG_PATH
    return CONFIG_PATH


def load_config(path=None):
    """Load youtube and twitch groups from a config file.

    Args:
        `path`: Config path, defaults to the one selected by APP_ENV

    Returns:
        (youtube_groups, twitch_groups)
    """
    if path is None:
        path = get_config_path()

    if not Path(path).is_file():
        raise FileNotFoundError(
            f"Config not found: {path}"
            f" (APP_ENV={os.environ.get('APP_ENV')!r})"
        )

    namespace = runpy.run_path(str(path))
    log("[config]", f"loaded {path}", console=True)

    return namespace.get("youtube_groups"), namespace.get("twitch_groups")
