import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import re
import requests
from html import unescape

logger = logging.getLogger(__name__)

NITTER_INSTANCE = "https://nitter.net"   # если заблокирован, попробуйте "https://nitter.poast.org"

class TwitterClient:
    def __init__(self, bearer_token: str = None, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url
        self.username = None
        self.session = requests.Session()
        if proxy_url:
            self.session.proxies = {"http": proxy_url, "https": proxy_url}

    def get_user_id(self, username: str) -> int:
        self.username = username
        return 0

    def get_new_tweets(self, user_id: int, since_id: Optional[int] = None) -> List[Dict]:
        if not self.username:
            return []
        try:
            url = f"{NITTER_INSTANCE}/{self.username}/rss"
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            tweets = []
            for item in root.findall(".//item"):
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
            # Извлекаем ID твита из ссылки
            link = item.find("guid").text
            tweet_id = int(link.split("/")[-1])
            # Текст: берём description, вырезаем HTML
            desc = item.find("description").text or ""
            clean_text = re.sub(r'<.*?>', '', desc)   # убираем теги
            clean_text = unescape(clean_text.strip())
            # Медиа: ищем все img в description
            media_urls = re.findall(r'<img[^>]+src="([^"]+)"', desc)
            media_list = []
            for url in media_urls:
                # пропускаем аватары (обычно содержат /profile_images/)
                if "/profile_images/" in url:
                    continue
                media_list.append({
                    "key": None,
                    "type": "photo",         # видео через RSS не получить, к сожалению
                    "url": url,
                    "preview_image_url": url,
                    "video_url": None,
                })
            return {"id": tweet_id, "text": clean_text, "media": media_list}
        except Exception as e:
            logger.error(f"Ошибка парсинга элемента RSS: {e}")
            return None