# app/services/workflow.py

from pathlib import Path

from app.db.repo import get_pool, save_channel, save_posts
from app.services.telegram_parser.channel_info import get_channel_with_posts
from app.services.llm.analyzer import analyze_channel, save_analysis
from app.services.similarity_engine.engine import SimilarityEngine
from app.services.xlsx_generator import generate_similar_channels_xlsx
from app.services.similarity_engine.engine_single import calculate_similarity_for_channel


async def run_full_analysis_pipeline(raw: str) -> Path:
    """
    Полный пайплайн:
    1) Парсим канал и посты через Telethon
    2) Сохраняем в БД (channels + posts)
    3) LLM-анализ → keywords_cache
    4) Считаем похожие каналы (SimilarityEngine → analytics_results)
    5) Генерируем XLSX по похожим каналам
    6) Возвращаем путь к XLSX-файлу

    raw — может быть @username, t.me/..., текст с ссылкой.
    """

    # 1. Парсинг канала и постов
    print("RUN WF RAW:", raw)
    channel_data, posts, error = await get_channel_with_posts(raw_username=raw, limit=100)
    if error:
        raise ValueError(error)

    print("WF CHANNEL_DATA:", channel_data)


    # 2. Сохранение в БД
    pool = await get_pool()
    channel_id = await save_channel(pool, channel_data)
    await save_posts(pool, channel_id, posts)
    print("WF ANALYSIS_SAVED FOR ID:", channel_id)


    # 3. LLM-анализ
    llm_result = await analyze_channel(channel_data, posts)
    await save_analysis(channel_id, llm_result)

    # 4. SimilarityEngine по всей базе (MVP-вариант)
    await calculate_similarity_for_channel(channel_id)


    # 5. XLSX-отчёт по этому каналу
    # username у нас есть в channel_data
    username = channel_data.get("username")
    if not username:
        # на всякий случай
        username = raw.lstrip("@")

    report_path: Path = await generate_similar_channels_xlsx(username)
    return report_path
