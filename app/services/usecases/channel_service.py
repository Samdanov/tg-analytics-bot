from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from app.db.repo import (
    save_channel,
    save_posts,
    get_channel_id_by_username,
)
from app.services.telegram_parser.channel_info import get_channel_with_posts
from app.services.llm.analyzer import analyze_channel, save_analysis
from app.services.workflow_pipeline import run_full_analysis_pipeline
from app.core.logging import get_logger

logger = get_logger(__name__)


async def add_channel_usecase(
    raw_username: str,
    post_limit: int = 50,
) -> Tuple[Optional[Dict[str, Any]], Optional[int], int, Optional[str]]:
    """
    Загружает канал + посты, сохраняет в БД.
    Возвращает (channel_data, channel_id, posts_count, error_message).
    """
    channel_data, posts, error = await get_channel_with_posts(raw_username=raw_username, limit=post_limit)
    if error:
        return None, None, 0, error

    channel_id = await save_channel(channel_data)
    await save_posts(channel_id, posts)

    posts_count = len(posts or [])
    identifier = channel_data.get("username") or f"ID:{channel_data.get('id')}"
    logger.info("Add channel done identifier=%s channel_id=%s posts=%s", identifier, channel_id, posts_count)
    return channel_data, channel_id, posts_count, None


async def analyze_usecase(username: str, post_limit: int = 50) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Выполняет анализ канала с сохранением результатов в БД.
    Возвращает (result_dict, error_message).
    Поддерживает как username, так и ID каналов.
    """
    channel, posts, error = await get_channel_with_posts(username, limit=post_limit)
    if error:
        return None, error

    # Для ID-based каналов используем ID вместо username
    identifier = channel.get("username") or str(channel.get("id"))
    channel_id = await get_channel_id_by_username(identifier)
    if not channel_id:
        return None, "Сначала добавьте канал командой /add_channel"

    result = await analyze_channel(channel, posts)
    await save_analysis(channel_id, result)

    logger.info("Analyze done identifier=%s channel_id=%s", identifier, channel_id)
    return result, None


async def run_full_pipeline_usecase(username: str, top_n: int = 10) -> Path:
    """
    Обёртка над полным пайплайном (Telethon → LLM → similarity → XLSX).
    """
    return await run_full_analysis_pipeline(username, top_n=top_n)
