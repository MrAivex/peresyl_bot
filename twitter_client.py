import logging
from typing import Dict, List, Optional

import httpx
from tweepy import Client, Media

logger = logging.getLogger(__name__)

class TwitterClient:
    def __init__(self, bearer_token: str, proxy_url: Optional[str] = None):
        self.bearer_token = bearer_token
        # Создаём клиента без кастомной сессии
        self.client = Client(bearer_token)

        # Если указан прокси — подменяем стандартную сессию на httpx с SOCKS5
        if proxy_url:
            transport = httpx.HTTPTransport(proxy=httpx.Proxy(proxy_url))
            custom_session = httpx.Client(transport=transport)
            # Заменяем сессию в tweepy на нашу
            self.client.session = custom_session

    def get_user_id(self, username: str) -> int:
        user = self.client.get_user(username=username)
        return user.data.id

    def get_new_tweets(self, user_id: int, since_id: Optional[int] = None) -> List[Dict]:
        try:
            tweets = self.client.get_users_tweets(
                id=user_id,
                since_id=since_id,
                max_results=10,
                expansions=["attachments.media_keys"],
                media_fields=["url", "preview_image_url", "type", "variants"],
                tweet_fields=["text", "attachments"],
            )
        except Exception as e:
            logger.error(f"Ошибка получения твитов: {e}")
            return []

        if not tweets.data:
            return []

        media_lookup = {m.media_key: m for m in (tweets.includes.get("media") or [])}

        result = []
        for tweet in tweets.data:
            media_list = []
            if tweet.attachments and "media_keys" in tweet.attachments:
                for key in tweet.attachments["media_keys"]:
                    if key in media_lookup:
                        media_list.append(self._serialize_media(media_lookup[key]))
            result.append({
                "id": tweet.id,
                "text": tweet.text,
                "media": media_list,
            })
        return result

    def _serialize_media(self, media: Media) -> Dict:
        best_video = None
        if media.type == "video" and media.variants:
            video_variants = [
                v for v in media.variants if v.get("content_type") == "video/mp4"
            ]
            if video_variants:
                best_video = max(video_variants, key=lambda v: v.get("bit_rate", 0))

        return {
            "key": media.media_key,
            "type": media.type,
            "url": media.url,
            "preview_image_url": media.preview_image_url,
            "video_url": best_video["url"] if best_video else None,
        }