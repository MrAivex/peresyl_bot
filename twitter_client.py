import logging
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

NITTER_INSTANCE = "https://nitter.woodland.cafe"  # если не работает, смените на "https://nitter.net"

class TwitterClient:
    def __init__(self, bearer_token: str = None, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url
        self.username = None
        self.session = requests.Session()
        if proxy_url:
            self.session.proxies = {"http": proxy_url, "https": proxy_url}
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:120.0) Gecko/20100101 Firefox/120.0"
        })

    def get_user_id(self, username: str) -> int:
        self.username = username
        return 0

    def get_new_tweets(self, user_id: int, since_id: Optional[int] = None) -> List[Dict]:
        if not self.username:
            return []
        try:
            url = f"{NITTER_INSTANCE}/{self.username}"
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            tweets = []
            # Ищем все элементы с классом "timeline-item" (стандартный класс Nitter)
            items = soup.select(".timeline-item")
            for item in items:
                tweet = self._parse_item(item)
                if tweet and (since_id is None or tweet["id"] > since_id):
                    tweets.append(tweet)
                    if len(tweets) >= 10:
                        break
            return tweets
        except Exception as e:
            logger.error(f"Ошибка получения твитов: {e}")
            return []

    def _parse_item(self, item) -> Optional[Dict]:
        try:
            # ID твита (из ссылки "permalink")
            link = item.select_one("a.permalink")
            if not link:
                return None
            tweet_id = int(link["href"].split("/")[-1])

            # Текст твита
            text_elem = item.select_one(".tweet-content")
            if not text_elem:
                return None
            text = text_elem.get_text("\n", strip=True)

            # Медиа (фото и превью видео)
            media_list = []
            attachments = item.select(".attachment img, .attachment video")
            for m in attachments:
                src = m.get("src") or m.get("data-src")
                if src and "/profile_images/" not in src:
                    # Определим тип: если img — фото, если video — видео
                    media_type = "photo"
                    if m.name == "video":
                        media_type = "video"
                    media_list.append({
                        "key": None,
                        "type": media_type,
                        "url": src,
                        "preview_image_url": src,
                        "video_url": src if media_type == "video" else None,
                    })
            return {"id": tweet_id, "text": text, "media": media_list}
        except Exception as e:
            logger.error(f"Ошибка парсинга твита: {e}")
            return None