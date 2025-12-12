from sqlalchemy import select
from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache
import json
import re


def format_audience(audience: str) -> str:
    """
    Красиво форматирует длинный текст ЦА от LLM в виде списка.
    """
    if not audience or audience.strip() == "":
        return "—"

    # Разбиваем по точкам или запятым + переносы строк
    parts = re.split(r'[.\n]+', audience)
    parts = [p.strip() for p in parts if p.strip()]

    # превращаем в список
    return "\n".join(f"• {p}" for p in parts)


async def build_channel_summary(username: str) -> str:
    """
    Создаёт красивую карточку канала.
    Поддерживает как обычные username, так и ID-based каналы.
    
    ━━━━━━━━━━━━━━
    📊 @username
    ━━━━━━━━━━━━━━
    👥 Подписчики: …
    🎯 ЦА:
    • …
    • …
    📌 Ключевые слова: …
    ━━━━━━━━━━━━━━
    """
    identifier = username.strip().lstrip("@")
    
    # Если это ID канала (число), добавляем префикс "id:"
    if identifier.lstrip('-').isdigit():
        identifier = f"id:{identifier}"

    async with async_session_maker() as session:
        result = await session.execute(
            select(Channel, KeywordsCache)
            .join(KeywordsCache, KeywordsCache.channel_id == Channel.id)
            .where(Channel.username == identifier)
        )
        row = result.first()

        if not row:
            # Красивое отображение ошибки
            if identifier.startswith("id:"):
                return f"Канал с ID {identifier} не найден в базе."
            else:
                return f"Канал @{identifier} не найден в базе."

        ch, kc = row

        # ---- Subscribers ----
        subs = ch.subscribers if ch.subscribers not in (None, 0) else "—"

        # ---- Audience (LLM) ----
        audience_raw = kc.audience or "—"
        audience_fmt = format_audience(audience_raw)

        # ---- Keywords ----
        keywords_list = []
        if kc.keywords_json:
            try:
                parsed = json.loads(kc.keywords_json)
                if isinstance(parsed, list):
                    keywords_list = parsed
            except:
                pass

        keywords = ", ".join(keywords_list) if keywords_list else "—"

        # ---- Определяем отображение канала ----
        # Для ID-based каналов (username начинается с "id:")
        if ch.username.startswith("id:"):
            channel_display = f"<b>{ch.title or 'Приватный канал'}</b>\n🆔 <code>{ch.username}</code>"
        else:
            channel_display = f"<b>@{ch.username}</b>"

        # ---- Card style summary ----
        text = (
            "━━━━━━━━━━━━━━━━━━\n"
            f"📊 {channel_display}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"👥 <b>Подписчики:</b> {subs}\n"
            f"📌 <b>Название:</b> {ch.title}\n\n"
            f"🎯 <b>Целевая аудитория:</b>\n{audience_fmt}\n\n"
            f"🔑 <b>Ключевые слова:</b>\n{keywords}\n"
            "━━━━━━━━━━━━━━━━━━"
        )

        return text
