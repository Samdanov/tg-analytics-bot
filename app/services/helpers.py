from sqlalchemy import select
from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache
import json


async def build_channel_summary(username: str) -> str:
    """
    Возвращает красивый текстовый блок с данными о канале:
    - название
    - подписчики
    - ЦА (из LLM)
    - ключевые слова
    """

    username = username.strip().lstrip("@")

    async with async_session_maker() as session:
        result = await session.execute(
            select(Channel, KeywordsCache)
            .join(KeywordsCache, KeywordsCache.channel_id == Channel.id)
            .where(Channel.username == username)
        )
        row = result.first()

        if not row:
            return f"Канал @{username} не найден в базе."

        ch, kc = row

        # ---- Аудитория (LLM) ----
        audience = kc.audience or "—"

        # ---- Ключевые слова ----
        keywords_list = []
        if kc.keywords_json:
            try:
                parsed = json.loads(kc.keywords_json)
                if isinstance(parsed, list):
                    keywords_list = parsed
            except Exception:
                pass

        keywords = ", ".join(keywords_list) if keywords_list else "—"

        # ---- Подписчики ----
        subscribers = ch.subscribers if ch.subscribers is not None else "—"

        # ---- Финальный текст ----
        text = (
            f"📊 <b>Анализ канала @{ch.username}</b>\n\n"
            f"<b>Название:</b> {ch.title}\n"
            f"<b>Подписчиков:</b> {subscribers}\n"
            f"<b>Целевая аудитория:</b> {audience}\n"
            f"<b>Ключевые слова:</b> {keywords}\n"
        )

        return text
