import logging
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

class Translator:
    def __init__(self, api_key: str, model: str = "deepseek-chat", base_url: Optional[str] = None):
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = model

    def translate(self, text: str, target_lang: str = "Russian") -> str:
        prompt = f"""Ты — креативный переводчик для Telegram-канала.
            Переведи следующий твит на {target_lang}, сохраняя стиль и энергию оригинала.
            Добавь в перевод уместные эмодзи (1–3 на пост), чтобы текст выглядел живо.
            Оставь без изменений хештеги, @упоминания и ссылки.
            Если в оригинале есть эмодзи — сохрани их и добавь свои, где это улучшает восприятие.

            Оригинал:
            {text}
            """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Ошибка перевода: {e}")
            return text