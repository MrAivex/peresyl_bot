import asyncio
import logging
import os
from typing import Dict, Optional

from state_manager import StateManager
from twitter_client import TwitterClient
from translator import Translator
from media_downloader import MediaDownloader
from telegram_publisher import TelegramPublisher

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, config: Dict):
        if config["source"] == "instagram":
            from instagram_client import InstagramClient
            self.instagram = InstagramClient(
                login=config["instagram_login"],
                password=config["instagram_password"],
                proxy=config.get("instagram_proxy"),
                session_file=config.get("instagram_session_file", "instagram_session.json")
            )
            if not self.instagram.login_user():
                raise Exception("Не удалось войти в Instagram")
            self.target_user_id = self.instagram.get_user_id_from_username(config["instagram_username"])
            if not self.target_user_id:
                raise Exception(f"Пользователь {config['instagram_username']} не найден")
            self.source = "instagram"
        else:
            config.get("twitter_proxy")
            os.environ["HTTP_PROXY"] = config["twitter_proxy"]
            os.environ["HTTPS_PROXY"] = config["twitter_proxy"]
            self.twitter = TwitterClient(
            bearer_token=config["twitter_bearer_token"],
            proxy_url=config.get("twitter_proxy"),
        )
        self.translator = Translator(
            api_key=config["llm_api_key"],
            model=config["llm_model"],
            base_url=config.get("llm_base_url"),
        )
        self.downloader = MediaDownloader()
        self.publisher = TelegramPublisher(
            token=config["tg_bot_token"],
            channel_id=config["tg_channel_id"],
            proxy_url=config.get("tg_proxy"),
        )
        self.state = StateManager(config.get("state_file", "state.json"))
        self.target_username = config["target_username"]
        self.interval = config.get("poll_interval_sec", 900)
        self.user_id: Optional[int] = None

    async def start(self) -> None:
        if self.source == "instagram":
            self.target_user_id = self.instagram.get_user_id_from_username(config["instagram_username"])
            logger.info(f"Мониторим Instagram @{config['instagram_username']} (id={self.target_user_id})")

            while True:
                try:
                    # В Instagram вместо since_id используем timestamp
                    last_ts = self.state.get_last_id()  # на самом деле храним timestamp
                    new_posts = self.instagram.get_new_posts(
                        self.target_user_id, amount=10, since_timestamp=last_ts
                    )
                    for post in sorted(new_posts, key=lambda p: p["timestamp"]):
                        await self._process_post(post)
                        self.state.save_last_id(post["timestamp"])  # сохраняем timestamp
                except Exception as e:
                    logger.error(f"Ошибка в цикле Instagram: {e}")
                await asyncio.sleep(self.interval)
        else:
            self.user_id = self.twitter.get_user_id(self.target_username)
            logger.info(f"Мониторим @{self.target_username} (id={self.user_id})")
            logger.info("Бот запущен. Ожидаю новые твиты...")  # <-- добавьте эту строку

            while True:
                try:
                    logger.info("Проверяю новые твиты...")
                    last_id = self.state.get_last_id()
                    new_tweets = self.twitter.get_new_tweets(self.user_id, since_id=last_id)

                    for tweet in sorted(new_tweets, key=lambda t: t["id"]):
                        await self._process_tweet(tweet)
                        self.state.save_last_id(tweet["id"])

                    if new_tweets:
                        logger.info(f"Обработано {len(new_tweets)} твитов")
                    else:
                        logger.info("Новых твитов нет")
                except Exception as e:
                    logger.error(f"Ошибка в основном цикле: {e}", exc_info=True)

                await asyncio.sleep(self.interval)

    async def _process_tweet(self, tweet: Dict) -> None:
        translated = self.translator.translate(tweet["text"])

        media_files = []
        for m in tweet["media"]:
            url = None
            file_type = "photo" if m["type"] == "photo" else "video"
            if m["type"] == "photo":
                url = m["url"]
            elif m["type"] == "video" and m.get("video_url"):
                url = m["video_url"]

            if url:
                path = self.downloader.download(url, file_type)
                if path:
                    media_files.append({"type": file_type, "path": path})

        try:
            if not media_files:
                await self.publisher.send_text(translated)
            elif len(media_files) == 1:
                if media_files[0]["type"] == "photo":
                    await self.publisher.send_photo(media_files[0]["path"], caption=translated)
                else:
                    await self.publisher.send_video(media_files[0]["path"], caption=translated)
            else:
                await self.publisher.send_media_group(media_files)
                await self.publisher.send_text(translated)
        except Exception as e:
            logger.error(f"Ошибка отправки твита {tweet['id']}: {e}")
        finally:
            for m in media_files:
                try:
                    os.unlink(m["path"])
                except OSError:
                    pass
    
    async def _process_post(self, post: Dict) -> None:
        text = post["caption"]
        if text:
            translated = self.translator.translate(text)
        else:
            translated = ""  # если нет подписи

        media_files = []
        for m in post["media"]:
            url = m["url"]
            file_type = m["type"]
            if url:
                path = self.downloader.download(url, file_type)
                if path:
                    media_files.append({"type": file_type, "path": path})

        try:
            if not media_files:
                await self.publisher.send_text(translated or "🖼 Без подписи")
            elif len(media_files) == 1:
                if media_files[0]["type"] == "photo":
                    await self.publisher.send_photo(media_files[0]["path"], caption=translated)
                else:
                    await self.publisher.send_video(media_files[0]["path"], caption=translated)
            else:
                await self.publisher.send_media_group(media_files)
                await self.publisher.send_text(translated or "🖼")
        except Exception as e:
            logger.error(f"Ошибка отправки поста {post['id']}: {e}")
        finally:
            for m in media_files:
                try:
                    os.unlink(m["path"])
                except OSError:
                    pass