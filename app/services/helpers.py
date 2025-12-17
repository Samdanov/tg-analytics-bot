from sqlalchemy import select
from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache
import json
import re
from app.bot.styles import Icons, get_separator


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

        # ---- Tone (Тональность) ----
        tone = getattr(kc, 'tone', None) or "—"

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

        # ---- Category ----
        category = ch.category or "—"
        
        # ---- Card style summary (стиль ОРБИТА) ----
        separator = get_separator(20)
        text = (
            f"{separator}\n"
            f"{Icons.ORBIT} {channel_display}\n"
            f"{separator}\n"
            f"{Icons.SUBSCRIBERS} <b>Подписчики:</b> {subs}\n"
            f"{Icons.CHANNEL} <b>Название:</b> {ch.title}\n"
            f"📂 <b>Категория:</b> {category}\n\n"
            f"{Icons.TARGET} <b>Целевая аудитория:</b>\n{audience_fmt}\n\n"
            f"{Icons.KEYWORDS} <b>Ключевые слова:</b>\n{keywords}\n"
        )
        
        # Добавляем тональность, если она есть
        if tone != "—":
            text += f"\n{Icons.CHART} <b>Тональность:</b> {tone}\n"
        
        text += f"{separator}"

        return text


def build_website_summary(url: str, analysis_result: dict) -> str:
    """
    Создаёт красивую карточку для веб-сайта с результатами анализа.
    Аналогично build_channel_summary, но для сайтов.
    
    Args:
        url: URL сайта
        analysis_result: Результат анализа от LLM (содержит audience, keywords, tone)
    
    Returns:
        Отформатированный текст карточки
    """
    # ---- Audience (LLM) ----
    audience_raw = analysis_result.get("audience", "") or "—"
    audience_fmt = format_audience(audience_raw)

    # ---- Keywords ----
    keywords_list = analysis_result.get("keywords", []) or []
    keywords = ", ".join(keywords_list) if keywords_list else "—"

    # ---- Category ----
    category = analysis_result.get("category", "") or "—"

    # ---- Tone (опционально) ----
    tone = analysis_result.get("tone", "") or "—"

    # ---- Card style summary (стиль ОРБИТА) ----
    separator = get_separator(20)
    text = (
        f"{separator}\n"
        f"{Icons.SATELLITE} <b>Веб-сайт</b>\n"
        f"{Icons.DATA} <code>{url}</code>\n"
        f"{separator}\n"
        f"📂 <b>Категория:</b> {category}\n\n"
        f"{Icons.TARGET} <b>Целевая аудитория:</b>\n{audience_fmt}\n\n"
        f"{Icons.KEYWORDS} <b>Ключевые слова:</b>\n{keywords}\n"
    )
    
    if tone != "—":
        text += f"\n{Icons.CHART} <b>Тональность:</b> {tone}\n"
    
    text += f"{separator}"
    
    return text
