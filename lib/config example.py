import os

from dotenv import load_dotenv

load_dotenv()

groups = [
    ("", "group_1"),
    ("", "group_2"),
    ("", "group_3"),
]

telegram_channel_id = os.environ.get("telegram_channel_id")

group_id_1 = []

group_id_2 = []

group_id_3 = []
