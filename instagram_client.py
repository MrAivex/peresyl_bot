import logging
from typing import Dict, List, Optional

from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError

logger = logging.getLogger(__name__)

class InstagramClient:
    def __init__(self, login: str, password: str, proxy: Optional[str] = None,
                 session_file: str = "instagram_session.json"):
        self.login = login
        self.password = password
        self.proxy = proxy
        self.session_file = session_file
        self.client = Client()

        if proxy:
            # instagrapi принимает прокси в формате http://user:pass@host:port
            self.client.set_proxy(proxy)

    def login_user(self) -> bool:
        """Выполняет вход и сохраняет сессию. Возвращает True при успехе."""
        try:
            # Пробуем загрузить сессию
            self.client.load_settings(self.session_file)
            self.client.get_timeline_feed()  # проверка живой сессии
            logger.info("Instagram: сессия загружена")
            return True
        except (LoginRequired, ClientError):
            logger.info("Instagram: сессия недействительна, требуется логин")
            try:
                self.client.login(self.login, self.password)
                self.client.dump_settings(self.session_file)
                logger.info("Instagram: вход выполнен, сессия сохранена")
                return True
            except Exception as e:
                logger.error(f"Ошибка входа в Instagram: {e}")
                return False

    def get_user_id_from_username(self, username: str) -> Optional[str]:
        """Получает числовой ID пользователя по имени."""
        try:
            user_info = self.client.user_info_by_username(username)
            return str(user_info.pk)
        except Exception as e:
            logger.error(f"Не удалось найти пользователя {username}: {e}")
            return None

    def get_new_posts(self, user_id: str, amount: int = 10,
                      since_timestamp: Optional[int] = None) -> List[Dict]:
        """
        Возвращает список новых постов пользователя.
        since_timestamp – Unix timestamp, если указан, возвращаются посты новее этого времени.
        Каждый пост – словарь с полями: id, timestamp, caption, media (список словарей).
        """
        try:
            posts = self.client.user_medias(user_id, amount=amount)
        except Exception as e:
            logger.error(f"Ошибка получения постов: {e}")
            return []

        result = []
        for post in posts:
            # Если задан фильтр по времени и пост старый – пропускаем
            if since_timestamp and post.taken_at.timestamp() <= since_timestamp:
                continue

            media_list = self._extract_media(post)
            result.append({
                "id": post.pk,
                "timestamp": int(post.taken_at.timestamp()),
                "caption": post.caption_text or "",
                "media": media_list,
            })
        return result

    def _extract_media(self, post) -> List[Dict]:
        """Извлекает медиа из поста (фото, видео, карусель)."""
        media = []
        # Определяем тип ресурса: 1 – фото, 2 – видео, 8 – карусель
        if post.media_type == 1:  # фото
            if post.thumbnail_url:
                media.append({
                    "type": "photo",
                    "url": str(post.thumbnail_url),
                })
        elif post.media_type == 2:  # видео
            if post.video_url:
                media.append({
                    "type": "video",
                    "url": str(post.video_url),
                    "preview_url": str(post.thumbnail_url) if post.thumbnail_url else None,
                })
        elif post.media_type == 8:  # карусель
            for resource in post.resources:
                if resource.media_type == 1:
                    if resource.thumbnail_url:
                        media.append({
                            "type": "photo",
                            "url": str(resource.thumbnail_url),
                        })
                elif resource.media_type == 2:
                    if resource.video_url:
                        media.append({
                            "type": "video",
                            "url": str(resource.video_url),
                            "preview_url": str(resource.thumbnail_url) if resource.thumbnail_url else None,
                        })
        return media