import asyncio
import logging
from typing import Dict, List, Optional

from telegram import Bot, InputMediaPhoto, InputMediaVideo
from telegram.error import TelegramError
from telegram.request import HTTPXRequest

logger = logging.getLogger(__name__)

class TelegramPublisher:
    def __init__(self, token: str, channel_id: str, proxy_url: Optional[str] = None):
        request = None
        if proxy_url:
            request = HTTPXRequest(proxy_url=proxy_url)
        self.bot = Bot(token=token, request=request)
        self.channel_id = channel_id

    async def send_text(self, text: str) -> None:
        await self._retry_send(lambda: self.bot.send_message(self.channel_id, text, parse_mode="HTML"))

    async def send_photo(self, photo_path: str, caption: Optional[str] = None) -> None:
        with open(photo_path, "rb") as f:
            await self._retry_send(lambda: self.bot.send_photo(self.channel_id, f, caption=caption))

    async def send_video(self, video_path: str, caption: Optional[str] = None) -> None:
        with open(video_path, "rb") as f:
            await self._retry_send(lambda: self.bot.send_video(self.channel_id, f, caption=caption))

    async def send_media_group(self, media_files: List[Dict], caption: Optional[str] = None) -> None:
        group = []
        for i, m in enumerate(media_files):
            kwargs = {"media": open(m["path"], "rb")}
            if i == 0 and caption:
                kwargs["caption"] = caption
            if m["type"] == "photo":
                group.append(InputMediaPhoto(**kwargs))
            elif m["type"] == "video":
                group.append(InputMediaVideo(**kwargs))
        if group:
            await self._retry_send(lambda: self.bot.send_media_group(self.channel_id, group))

    async def _retry_send(self, func, attempts=3, delay=5):
        last_exc = None
        for i in range(attempts):
            try:
                return await func()
            except TelegramError as e:
                logger.warning(f"Попытка {i+1}/{attempts} не удалась: {e}")
                last_exc = e
                await asyncio.sleep(delay)
        raise last_exc