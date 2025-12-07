from sqlalchemy import select
from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache
import json


async def build_channel_summary(username: str) -> str:
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

        # keywords_json → list
        keywords = []
        if kc.keywords_json:
            try:
                keywords = json.loads(kc.keywords_json)
            except:
                pass

        keywords_str = ", ".join(keywords) if keywords else "—"
        audience_str = kc.audience or "—"

        text = (
            f"📊 <b>Анализ канала @{ch.username}</b>\n\n"
            f"<b>Название:</b> {ch.title}\n"
            f"<b>Подписчиков:</b> {ch.subscribers}\n"
            f"<b>Целевая аудитория:</b> {audience_str}\n"
            f"<b>Ключевые слова:</b> {keywords_str}\n"
        )
        return text
