# app/services/workflow_pipeline.py

from pathlib import Path

from app.db.repo import get_pool, save_channel, save_posts
from app.services.telegram_parser.channel_info import get_channel_with_posts
from app.services.llm.analyzer import analyze_channel, save_analysis
from app.services.similarity_engine.engine_single import calculate_similarity_for_channel
from app.services.xlsx_generator import generate_similar_channels_xlsx


async def run_full_analysis_pipeline(username: str) -> Path:
    """
    Полный пайплайн анализа канала:
    1) Получаем данные через Telethon
    2) Сохраняем канал + посты в БД
    3) LLM-анализ → keywords_cache
    4) Расчёт похожих каналов
    5) Генерация XLSX
    """

    # 1. Получаем данные
    print("WF RAW:", username)
    channel_data, posts, error = await get_channel_with_posts(raw_username=username, limit=100)

    if error:
        raise ValueError(f"Ошибка при получении данных: {error}")

    print("WF CHANNEL_DATA:", channel_data)

    # 2. Сохраняем в БД
    pool = await get_pool()
    channel_id = await save_channel(pool, channel_data)
    await save_posts(pool, channel_id, posts)

    # 3. Запуск LLM-анализатора
    # analyze_channel ожидает ДВА аргумента → передаём их
    llm_result = await analyze_channel(channel_data, posts)

    # сохраняем ключевые слова в keywords_cache
    await save_analysis(channel_id, llm_result)

    print("WF ANALYSIS COMPLETED:", channel_id)

    # 4. Рассчитываем похожие каналы
    await calculate_similarity_for_channel(channel_id)

    # 5. Генерируем XLSX
    username_clean = channel_data.get("username") or username.lstrip("@")
    report_path = await generate_similar_channels_xlsx(username_clean)

    return report_path
