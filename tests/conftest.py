import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from libs.utils import logger, tools  # noqa: E402


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    """Keep tests away from real log/asset dirs and the network."""
    log_path = tmp_path / "log"
    ignore_path = tmp_path / "ignore"
    log_path.mkdir()
    ignore_path.mkdir()

    # Daily logs are uploaded to Telegram, so tests must not write to them
    monkeypatch.setattr(logger, "LOG_PATH", log_path)
    monkeypatch.setattr(tools, "LOG_PATH", log_path)
    monkeypatch.setattr(tools, "IGNORE_PATH", ignore_path)
    monkeypatch.setenv("youtube_api_token", "key1")

    def no_network(*args, **kwargs):
        raise RuntimeError("network access is disabled in tests")

    monkeypatch.setattr(requests.api, "request", no_network)
    monkeypatch.setattr(requests.sessions.Session, "request", no_network)

    return tmp_path
