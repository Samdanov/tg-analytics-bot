"""
Detect Proxy Channel Use Case

Use case для определения каналов-прокладок (ad-forwarding channels).
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass

from app.domain import ProxyChannelDetector, ProxyChannelDetectedError
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ProxyDetectionResult:
    """Результат определения прокладки."""
    is_proxy: bool
    linked_channels: List[Tuple[str, int]]  # [(username, count), ...]
    avg_text_length: float
    link_posts_ratio: float
    total_posts: int
    reason: str


class DetectProxyChannelUseCase:
    """
    Use case для определения каналов-прокладок.
    
    Использует domain.ProxyChannelDetector.
    """
    
    def __init__(
        self,
        detector: Optional[ProxyChannelDetector] = None,
        min_linked_channels: int = 3,
        max_avg_text: int = 100,
        min_link_ratio: float = 0.5
    ):
        """
        Args:
            detector: ProxyChannelDetector (создается по умолчанию)
            min_linked_channels: Минимум упоминаемых каналов
            max_avg_text: Максимальная средняя длина текста
            min_link_ratio: Минимальная доля постов со ссылками
        """
        self.detector = detector or ProxyChannelDetector(
            min_linked_channels=min_linked_channels,
            max_avg_text=max_avg_text,
            min_link_ratio=min_link_ratio
        )
    
    async def execute(
        self,
        posts: List[dict],
        exclude_username: Optional[str] = None
    ) -> ProxyDetectionResult:
        """
        Проверить, является ли канал прокладкой.
        
        Args:
            posts: Список постов канала
            exclude_username: Username текущего канала (исключить из подсчета)
        
        Returns:
            ProxyDetectionResult
        """
        if not posts:
            return ProxyDetectionResult(
                is_proxy=False,
                linked_channels=[],
                avg_text_length=0.0,
                link_posts_ratio=0.0,
                total_posts=0,
                reason="Нет постов для анализа"
            )
        
        try:
            # Используем domain service
            self.detector.detect(posts, exclude_username=exclude_username)
            
            # Если не бросило исключение - не прокладка
            return ProxyDetectionResult(
                is_proxy=False,
                linked_channels=[],
                avg_text_length=0.0,
                link_posts_ratio=0.0,
                total_posts=len(posts),
                reason="Обычный канал"
            )
        
        except ProxyChannelDetectedError as e:
            # Прокладка обнаружена
            linked_channels = e.details.get("linked_channels", [])
            
            return ProxyDetectionResult(
                is_proxy=True,
                linked_channels=linked_channels,
                avg_text_length=e.details.get("avg_text_length", 0.0),
                link_posts_ratio=e.details.get("link_posts_ratio", 0.0),
                total_posts=len(posts),
                reason=str(e)
            )

