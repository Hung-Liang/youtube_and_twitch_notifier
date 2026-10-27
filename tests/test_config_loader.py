from pathlib import Path

import pytest

from libs.utils import config_loader
from libs.utils.config_check import check_groups

EXAMPLE_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "config.example.py"
)


@pytest.fixture
def config_paths(tmp_path, monkeypatch):
    prod_path = tmp_path / "config.py"
    dev_path = tmp_path / "dev_config.py"
    monkeypatch.setattr(config_loader, "CONFIG_PATH", prod_path)
    monkeypatch.setattr(config_loader, "DEV_CONFIG_PATH", dev_path)
    return prod_path, dev_path


@pytest.mark.parametrize(
    "app_env, expected",
    [("dev", 1), (None, 0), ("prod", 0), ("", 0)],
)
def test_app_env_selects_config(monkeypatch, config_paths, app_env, expected):
    if app_env is None:
        monkeypatch.delenv("APP_ENV", raising=False)
    else:
        monkeypatch.setenv("APP_ENV", app_env)

    assert config_loader.get_config_path() == config_paths[expected]


def test_load_config_reads_selected_file(monkeypatch, config_paths):
    _, dev_path = config_paths
    dev_path.write_text(
        'youtube_groups = {"dev": {}}\ntwitch_groups = {}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("APP_ENV", "dev")

    assert config_loader.load_config() == ({"dev": {}}, {})


def test_load_config_example_is_valid():
    youtube_groups, twitch_groups = config_loader.load_config(EXAMPLE_PATH)

    assert check_groups("youtube", youtube_groups)[0] == []
    assert check_groups("twitch", twitch_groups)[0] == []


def test_load_config_missing_file_raises(monkeypatch, config_paths):
    monkeypatch.setenv("APP_ENV", "dev")

    with pytest.raises(FileNotFoundError, match="APP_ENV='dev'"):
        config_loader.load_config()
