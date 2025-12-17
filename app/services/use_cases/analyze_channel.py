"""
Analyze Channel Use Case

Use case для полного анализа канала (Telethon → LLM → Similarity → Report).

Логика similarity:
- Если есть в БД → используем (быстро)
- Если нет → считаем on-the-fly (только для новых каналов)
"""

from pathlib import Path
from typing import Optional
import time

from app.domain import ChannelIdentifier
from app.db.repositories import RepositoryFacade, get_repository_facade
from app.schemas import ChannelCreateSchema, AnalysisResultSchema
from app.services.telegram_parser.channel_info import get_channel_with_posts
from app.services.llm.analyzer import analyze_channel
from app.services.similarity_engine.engine_single import calculate_similarity_for_channel
from app.services.xlsx_generator import generate_similar_channels_xlsx
from app.core.logging import get_logger

logger = get_logger(__name__)


class AnalyzeChannelUseCase:
    """
    Use case для полного анализа канала.
    
    Шаги:
    1. Получение данных через Telethon
    2. Сохранение в БД через repositories
    3. LLM-анализ (keywords, audience, tone)
    4. Расчет похожих каналов (similarity)
    5. Генерация XLSX отчета
    """
    
    def __init__(
        self,
        repo: Optional[RepositoryFacade] = None,
        post_limit: int = 100
    ):
        """
        Args:
            repo: RepositoryFacade (по умолчанию singleton)
            post_limit: Количество постов для анализа
        """
        self.repo = repo or get_repository_facade()
        self.post_limit = post_limit
    
    async def execute(
        self,
        identifier: ChannelIdentifier,
        top_n: int = 10
    ) -> Path:
        """
        Выполнить полный анализ канала.
        
        Args:
            identifier: ChannelIdentifier (domain object)
            top_n: Количество похожих каналов для поиска
        
        Returns:
            Path к сгенерированному XLSX отчету
        
        Raises:
            ValueError: если канал не найден или ошибка анализа
        """
        start_time = time.time()
        
        # Шаг 1: Получение данных через Telethon
        logger.info(f"[AnalyzeChannel] Step 1: Fetching channel data for {identifier.to_display_format()}")
        
        channel_data, posts, error = await get_channel_with_posts(
            raw_username=identifier.to_telethon_format(),
            limit=self.post_limit
        )
        
        if error:
            raise ValueError(f"Ошибка при получении данных канала: {error}")
        
        logger.debug(f"[AnalyzeChannel] Fetched: channel_data={channel_data}, posts={len(posts or [])}")
        
        # Шаг 2: Сохранение в БД
        logger.info(f"[AnalyzeChannel] Step 2: Saving channel to DB")
        
        channel_create = ChannelCreateSchema(
            identifier=identifier.to_db_format(),
            title=channel_data.get("title", ""),
            description=channel_data.get("about", ""),
            subscribers=channel_data.get("participants_count", 0)
        )
        
        channel = await self.repo.channels.upsert(channel_create)
        logger.info(f"[AnalyzeChannel] Channel saved: id={channel.id}")
        
        # Сохранение постов
        if posts:
            await self.repo.posts.replace_posts(channel.id, posts)
            logger.info(f"[AnalyzeChannel] Posts saved: count={len(posts)}")
        
        # Шаг 3: LLM-анализ
        logger.info(f"[AnalyzeChannel] Step 3: LLM analysis")
        
        llm_result = await analyze_channel(channel_data, posts)
        
        analysis = AnalysisResultSchema(
            audience=llm_result.get("audience", ""),
            keywords=llm_result.get("keywords", []),
            tone=llm_result.get("tone", ""),
            source="llm",
            confidence=1.0
        )
        
        await self.repo.keywords.upsert_analysis(channel.id, analysis)
        
        # Обновляем keywords в канале
        await self.repo.channels.update_keywords(channel.id, analysis.keywords)
        
        # ВАЖНО: Обновляем category в канале (нужно для similarity!)
        category = llm_result.get("category", "")
        if category:
            await self.repo.channels.update_category(channel.id, category)
            logger.info(f"[AnalyzeChannel] Category updated: '{category}'")
        
        logger.info(f"[AnalyzeChannel] Analysis saved: keywords={len(analysis.keywords)}, category='{category}'")
        
        # Шаг 4: Similarity — сначала проверяем БД, потом fallback
        logger.info(f"[AnalyzeChannel] Step 4: Checking similarity in DB")
        
        has_similarity = await self.repo.analytics.has_results(channel.id)
        
        if has_similarity:
            # Данные есть — используем их (быстрый путь)
            logger.info(f"[AnalyzeChannel] Similarity EXISTS in DB — using cached data (fast path)")
        else:
            # Данных нет — считаем on-the-fly для нового канала
            # Это работает ТОЛЬКО внутри категории канала (не глобально!)
            logger.info(f"[AnalyzeChannel] Similarity NOT in DB — calculating on-the-fly (new channel)")
            
            similarity_success = await calculate_similarity_for_channel(
                channel.id,
                top_n=top_n
            )
            
            if similarity_success:
                logger.info(f"[AnalyzeChannel] Similarity calculated and saved")
            else:
                logger.warning(f"[AnalyzeChannel] Similarity calculation failed (no data or small category)")
        
        # Шаг 5: Генерация XLSX
        logger.info(f"[AnalyzeChannel] Step 5: Generating XLSX report")
        
        # Определяем имя файла
        if identifier.is_id_based:
            filename = f"id_{identifier.channel_id}"
        else:
            filename = identifier.username
        
        report_path = await generate_similar_channels_xlsx(filename)
        
        elapsed = time.time() - start_time
        logger.info(
            f"[AnalyzeChannel] DONE: channel_id={channel.id}, "
            f"posts={len(posts or [])}, keywords={len(analysis.keywords)}, "
            f"top_n={top_n}, elapsed={elapsed:.2f}s, report={report_path}"
        )
        
        return report_path

