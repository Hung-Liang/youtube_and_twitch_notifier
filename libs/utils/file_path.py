import os
from pathlib import Path

PROGRAM_PATH = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

LOG_PATH = Path(PROGRAM_PATH, 'log')
ASSET_PATH = Path(PROGRAM_PATH, 'asset')
IGNORE_PATH = Path(ASSET_PATH, 'ignore')

LOG_PATH.mkdir(parents=True, exist_ok=True)
ASSET_PATH.mkdir(parents=True, exist_ok=True)
IGNORE_PATH.mkdir(parents=True, exist_ok=True)
