import os
from pathlib import Path

PROGRAM_PATH = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

LOG_PATH = Path(PROGRAM_PATH, 'log')
ASSET_PATH = Path(PROGRAM_PATH, 'asset')

IGNORE_JSON_PATH = Path(ASSET_PATH, 'ignore.json')
UPLOAD_PLAYLIST_JSON_PATH = Path(ASSET_PATH, 'upload_playlist.json')

LOG_PATH.mkdir(parents=True, exist_ok=True)
