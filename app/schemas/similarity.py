"""
Similarity Schemas

Pydantic models для поиска похожих каналов.
"""

from typing import List, Optional
from pydantic import Field, field_validator

from .base import BaseSchema


class SimilarityRequestSchema(BaseSchema):
    """
    Schema для запроса поиска похожих каналов.
    """
    
    identifier: str = Field(
        ...,
        description="Идентификатор целевого канала",
        examples=["@technews", "-1002508742544"]
    )
    top_n: int = Field(
        10,
        ge=1,
        le=500,
        description="Количество похожих каналов для поиска"
    )
    min_score: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Минимальный порог similarity score"
    )
    exclude_analyzed: bool = Field(
        False,
        description="Исключить уже проанализированные каналы"
    )


class SimilarChannelSchema(BaseSchema):
    """
    Schema для одного похожего канала.
    """
    
    channel_id: int = Field(..., description="ID канала в БД")
    identifier: str = Field(..., description="Идентификатор канала")
    is_id_based: bool = Field(..., description="Канал по ID")
    title: str = Field(..., description="Название канала")
    description: Optional[str] = Field(None, description="Описание канала")
    subscribers: int = Field(..., ge=0, description="Количество подписчиков")
    keywords: List[str] = Field(
        default_factory=list,
        description="Ключевые слова"
    )
    
    # Метрики similarity
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity score (0.0 - 1.0)"
    )
    common_keywords: List[str] = Field(
        default_factory=list,
        description="Общие ключевые слова с целевым каналом"
    )
    
    @property
    def display_name(self) -> str:
        """Отображаемое имя канала."""
        if self.is_id_based:
            return f"ID: {self.identifier.replace('id:', '')}"
        return f"@{self.identifier}"
    
    @property
    def relevance_percent(self) -> float:
        """Score в процентах."""
        return round(self.score * 100, 1)
    
    @property
    def telegram_link(self) -> Optional[str]:
        """Ссылка на Telegram канал."""
        if self.is_id_based:
            return None  # Приватные каналы без ссылки
        return f"https://t.me/{self.identifier}"
    
    class Config:
        json_schema_extra = {
            "example": {
                "channel_id": 456,
                "identifier": "devnews",
                "is_id_based": False,
                "title": "Dev News",
                "description": "Developer news and updates",
                "subscribers": 8000,
                "keywords": ["python", "javascript", "devops"],
                "score": 0.85,
                "common_keywords": ["python", "devops"]
            }
        }


class SimilarityResultSchema(BaseSchema):
    """
    Schema для результата поиска похожих каналов.
    """
    
    target_channel_id: int = Field(..., description="ID целевого канала")
    target_identifier: str = Field(..., description="Идентификатор целевого")
    target_keywords: List[str] = Field(
        ...,
        description="Ключевые слова целевого канала"
    )
    
    # Похожие каналы
    similar_channels: List[SimilarChannelSchema] = Field(
        ...,
        description="Список похожих каналов"
    )
    
    # Метаданные
    total_found: int = Field(
        ...,
        ge=0,
        description="Всего найдено похожих каналов"
    )
    calculation_duration_ms: Optional[int] = Field(
        None,
        description="Длительность расчёта (мс)"
    )
    
    @property
    def has_results(self) -> bool:
        """Найдены ли похожие каналы."""
        return bool(self.similar_channels)
    
    @property
    def avg_score(self) -> float:
        """Средний similarity score."""
        if not self.similar_channels:
            return 0.0
        return sum(ch.score for ch in self.similar_channels) / len(self.similar_channels)
    
    @property
    def top_3_channels(self) -> List[SimilarChannelSchema]:
        """Топ-3 самых похожих канала."""
        return self.similar_channels[:3]
    
    class Config:
        json_schema_extra = {
            "example": {
                "target_channel_id": 123,
                "target_identifier": "technews",
                "target_keywords": ["python", "django", "backend"],
                "similar_channels": [
                    {
                        "channel_id": 456,
                        "identifier": "devnews",
                        "is_id_based": False,
                        "title": "Dev News",
                        "subscribers": 8000,
                        "keywords": ["python", "javascript"],
                        "score": 0.85,
                        "common_keywords": ["python"]
                    }
                ],
                "total_found": 50,
                "calculation_duration_ms": 1200
            }
        }


class ProxyChannelDetectionSchema(BaseSchema):
    """
    Schema для результата определения канала-прокладки.
    
    Используется в workflow для принятия решений.
    """
    
    is_proxy: bool = Field(..., description="Является ли прокладкой")
    linked_channels: List[tuple[str, int]] = Field(
        default_factory=list,
        description="Упоминаемые каналы [(username, count), ...]"
    )
    avg_text_length: float = Field(..., description="Средняя длина текста")
    link_posts_ratio: float = Field(..., description="Доля постов со ссылками")
    total_posts: int = Field(..., ge=0, description="Всего постов проверено")
    reason: str = Field("", description="Причина определения как прокладки")
    
    @field_validator("linked_channels")
    @classmethod
    def validate_linked_channels(cls, v):
        """Валидация формата упоминаемых каналов."""
        if not all(isinstance(item, (tuple, list)) and len(item) == 2 for item in v):
            raise ValueError("linked_channels must be list of (username, count) tuples")
        return v
    
    @property
    def top_linked_channel(self) -> Optional[str]:
        """Самый упоминаемый канал."""
        if not self.linked_channels:
            return None
        return self.linked_channels[0][0]
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_proxy": True,
                "linked_channels": [
                    ("channel1", 5),
                    ("channel2", 3),
                    ("channel3", 2)
                ],
                "avg_text_length": 45.5,
                "link_posts_ratio": 0.8,
                "total_posts": 20,
                "reason": "Найдено 3 упоминаемых каналов (>= 3) | Средняя длина текста: 46 символов (< 100)"
            }
        }

