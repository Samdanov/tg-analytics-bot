"""
Analyze Website Use Case

Use case для анализа веб-сайтов и поиска похожих Telegram каналов.
"""

from pathlib import Path
from typing import Tuple
import time

from app.services.use_cases.website_service import run_website_analysis_pipeline
from app.core.logging import get_logger

logger = get_logger(__name__)


class AnalyzeWebsiteUseCase:
    """
    Use case для анализа веб-сайта.
    
    Шаги:
    1. Парсинг контента сайта
    2. LLM-анализ контента
    3. Поиск похожих каналов по keywords
    4. Генерация XLSX отчета
    """
    
    def __init__(self):
        pass
    
    async def execute(
        self,
        url: str,
        top_n: int = 10
    ) -> Tuple[Path, dict]:
        """
        Выполнить анализ веб-сайта.
        
        Args:
            url: URL веб-сайта
            top_n: Количество похожих каналов
        
        Returns:
            (report_path, analysis_result) где:
            - report_path: путь к XLSX отчету
            - analysis_result: результат LLM анализа
        
        Raises:
            ValueError: если сайт недоступен или ошибка анализа
        """
        start_time = time.time()
        
        logger.info(f"[AnalyzeWebsite] Starting analysis: url={url}, top_n={top_n}")
        
        # Используем существующий pipeline (пока не рефакторим его)
        result = await run_website_analysis_pipeline(url, top_n=top_n)
        
        report_path, analysis_result = result
        
        elapsed = time.time() - start_time
        logger.info(
            f"[AnalyzeWebsite] DONE: url={url}, "
            f"keywords={len(analysis_result.get('keywords', []))}, "
            f"top_n={top_n}, elapsed={elapsed:.2f}s"
        )
        
        return report_path, analysis_result

