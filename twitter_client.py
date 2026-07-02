import logging
from typing import Dict, List, Optional
import snscrape.modules.twitter as sntwitter

logger = logging.getLogger(__name__)

class TwitterClient:
    def __init__(self, bearer_token: str = None, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url
        self.username = None
        # snscrape не требует bearer_token, оставляем для совместимости

    def get_user_id(self, username: str) -> int:
        self.username = username
        # Возвращаем фиктивный ID, он не используется в snscrape
        return 0

    def get_new_tweets(self, user_id: int, since_id: Optional[int] = None) -> List[Dict]:
        if not self.username:
            return []

        try:
            tweets = []
            scraper = sntwitter.TwitterUserScraper(self.username)
            # Если since_id передан, парсим только свежие (snscrape не поддерживает since_id напрямую, поэтому остановимся после достижения старого ID)
            for i, tweet in enumerate(scraper.get_items()):
                if since_id and tweet.id <= since_id:
                    break
                tweets.append({
                    "id": tweet.id,
                    "text": tweet.rawContent,
                    "media": self._extract_media(tweet),
                })
                if len(tweets) >= 10:
                    break
            return tweets
        except Exception as e:
            logger.error(f"Ошибка получения твитов: {e}")
            return []

    def _extract_media(self, tweet) -> List[Dict]:
        media_list = []
        if tweet.media:
            for m in tweet.media:
                media_type = "video" if m.videoVariants else "photo"
                video_url = None
                if m.videoVariants:
                    # Выбираем вариант с максимальным битрейтом
                    video_url = max(
                        [v.url for v in m.videoVariants if v.contentType == "video/mp4"],
                        key=lambda x: x.get("bitrate", 0) if hasattr(x, 'bitrate') else 0
                    )
                media_list.append({
                    "key": None,
                    "type": media_type,
                    "url": m.fullUrl if media_type == "photo" else None,
                    "preview_image_url": m.thumbnailUrl if hasattr(m, 'thumbnailUrl') else None,
                    "video_url": video_url,
                })
        return media_list