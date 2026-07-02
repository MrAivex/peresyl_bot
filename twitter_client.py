import logging
from typing import Dict, List, Optional
from twikit import Client as TwikitClient

logger = logging.getLogger(__name__)

class TwitterClient:
    def __init__(self, bearer_token: str = None, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url
        self.username = None
        # Передаём HTTP-прокси прямо в клиент twikit
        self.client = TwikitClient(proxy=proxy_url) if proxy_url else TwikitClient()

    async def get_user_id(self, username: str) -> int:
        self.username = username
        return 0  # twikit не требует числовой ID

    async def get_new_tweets(self, user_id: int, since_id: Optional[int] = None) -> List[Dict]:
        if not self.username:
            return []

        try:
            user = await self.client.get_user_by_screen_name(self.username)
            tweets_data = await user.get_tweets('Tweets', count=10)

            if not tweets_data:
                return []

            result = []
            for tweet in tweets_data:
                if since_id and int(tweet.id) <= since_id:
                    continue
                media_list = await self._extract_media(tweet)
                result.append({
                    "id": int(tweet.id),
                    "text": tweet.text,
                    "media": media_list,
                })
            return result
        except Exception as e:
            logger.error(f"Ошибка получения твитов: {e}")
            return []

    async def _extract_media(self, tweet) -> List[Dict]:
        media_list = []
        if hasattr(tweet, 'media') and tweet.media:
            for m in tweet.media:
                media_type = "video" if hasattr(m, 'video_info') else "photo"
                video_url = None
                if media_type == "video" and hasattr(m, 'video_info'):
                    variants = m.video_info.get('variants', [])
                    mp4_variants = [v for v in variants if v.get('content_type') == 'video/mp4']
                    if mp4_variants:
                        best = max(mp4_variants, key=lambda x: x.get('bitrate', 0))
                        video_url = best.get('url')
                media_list.append({
                    "key": None,
                    "type": media_type,
                    "url": m.media_url_https if media_type == "photo" else None,
                    "preview_image_url": m.media_url_https if media_type == "video" else None,
                    "video_url": video_url,
                })
        return media_list