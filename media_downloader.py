import logging
import tempfile
from typing import Optional

import requests

logger = logging.getLogger(__name__)

class MediaDownloader:
    @staticmethod
    def download(url: str, file_type: str) -> Optional[str]:
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            suffix = ".mp4" if file_type == "video" else ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        tmp.write(chunk)
                return tmp.name
        except Exception as e:
            logger.error(f"Ошибка загрузки {url}: {e}")
            return None