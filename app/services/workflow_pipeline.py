from pathlib import Path

from app.db.repo import save_channel, save_posts
from app.services.telegram_parser.channel_info import get_channel_with_posts
from app.services.llm.analyzer import analyze_channel, save_analysis
from app.services.usecases.similarity_service import recalc_for_channel
from app.services.xlsx_generator import generate_similar_channels_xlsx
from app.core.logging import get_logger

logger = get_logger(__name__)


async def run_full_analysis_pipeline(username: str, top_n: int = 10) -> Path:
    """
    Полный пайплайн анализа канала:
    1) Получаем данные через Telethon
    2) Сохраняем канал + посты в БД
    3) LLM-анализ → keywords_cache
    4) Расчёт похожих каналов
    5) Генерация XLSX
    """

    logger.info("WF: start pipeline username=%s top_n=%s", username, top_n)
    channel_data, posts, error = await get_channel_with_posts(raw_username=username, limit=100)

    if error:
        raise ValueError(f"Ошибка при получении данных: {error}")

    logger.debug("WF: channel_data=%s", channel_data)

    channel_id = await save_channel(channel_data)
    await save_posts(channel_id, posts)

    llm_result = await analyze_channel(channel_data, posts)

    await save_analysis(channel_id, llm_result)

    logger.info("WF: analysis completed channel_id=%s", channel_id)

    await recalc_for_channel(channel_id, top_n=top_n)

    # Определяем имя для отчёта
    if channel_data.get("username"):
        username_clean = channel_data["username"].lstrip("@")
    else:
        # Для каналов без username используем формат id:CHANNEL_ID (как в БД)
        channel_id_value = channel_data.get('id', username)
        username_clean = f"id:{channel_id_value}"
    
    report_path = await generate_similar_channels_xlsx(username_clean)

    logger.info("WF: pipeline finished channel_id=%s report=%s top_n=%s", channel_id, report_path, top_n)
    return report_path
