import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self, file_path: str = "state.json"):
        self.file_path = file_path

    def get_last_id(self) -> Optional[int]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("last_tweet_id")
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def save_last_id(self, tweet_id: int) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump({"last_tweet_id": tweet_id}, f)