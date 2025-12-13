"""
Analysis Schemas

Pydantic models для LLM-анализа каналов.
"""

from typing import List, Optional, Literal
from pydantic import Field, field_validator

from .base import BaseSchema


class AnalysisRequestSchema(BaseSchema):
    """
    Schema для запроса анализа канала.
    """
    
    identifier: str = Field(
        ...,
        description="Идентификатор канала для анализа",
        examples=["@technews", "-1002508742544"]
    )
    post_limit: int = Field(
        50,
        ge=1,
        le=200,
        description="Количество постов для анализа"
    )
    force: bool = Field(
        False,
        description="Принудительный анализ (игнорировать кэш)"
    )


class AnalysisResultSchema(BaseSchema):
    """
    Schema для результата LLM-анализа.
    
    Соответствует domain.AnalysisResult.
    """
    
    audience: str = Field(
        ...,
        description="Описание целевой аудитории",
        min_length=1,
        max_length=2000
    )
    keywords: List[str] = Field(
        ...,
        description="Ключевые слова канала",
        min_items=0,
        max_items=50
    )
    tone: str = Field(
        "",
        description="Тональность канала",
        max_length=500
    )
    source: Literal["llm", "fallback", "manual"] = Field(
        "llm",
        description="Источник анализа"
    )
    confidence: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Уверенность в результате (0.0 - 1.0)"
    )
    
    @field_validator("keywords")
    @classmethod
    def clean_keywords(cls, v: List[str]) -> List[str]:
        """Очищает keywords от пустых значений."""
        return [kw.strip() for kw in v if kw and kw.strip()]
    
    @field_validator("audience", "tone")
    @classmethod
    def strip_text(cls, v: str) -> str:
        """Удаляет лишние пробелы."""
        return v.strip() if v else ""
    
    @property
    def is_from_llm(self) -> bool:
        """Результат получен из LLM."""
        return self.source == "llm"
    
    @property
    def is_fallback(self) -> bool:
        """Результат fallback (LLM не сработал)."""
        return self.source == "fallback"
    
    @property
    def has_keywords(self) -> bool:
        """Есть ли ключевые слова."""
        return bool(self.keywords)
    
    class Config:
        json_schema_extra = {
            "example": {
                "audience": "IT-специалисты 25-40 лет, интересующиеся технологиями",
                "keywords": ["python", "django", "backend", "devops"],
                "tone": "Профессиональный, с техническими деталями",
                "source": "llm",
                "confidence": 0.9
            }
        }


class AnalysisResponseSchema(BaseSchema):
    """
    Schema для ответа с результатами анализа.
    
    Включает информацию о канале и результат анализа.
    """
    
    channel_id: int = Field(..., description="ID канала в БД")
    identifier: str = Field(..., description="Идентификатор канала")
    is_id_based: bool = Field(..., description="Канал по ID")
    title: str = Field(..., description="Название канала")
    subscribers: int = Field(..., description="Количество подписчиков")
    
    # Результат анализа
    analysis: AnalysisResultSchema = Field(
        ...,
        description="Результат LLM-анализа"
    )
    
    # Метаданные
    analyzed_posts: int = Field(
        ...,
        ge=0,
        description="Количество проанализированных постов"
    )
    analysis_duration_ms: Optional[int] = Field(
        None,
        description="Длительность анализа (мс)"
    )
    
    @property
    def display_name(self) -> str:
        """Отображаемое имя канала."""
        if self.is_id_based:
            return f"ID: {self.identifier.replace('id:', '')}"
        return f"@{self.identifier}"
    
    class Config:
        json_schema_extra = {
            "example": {
                "channel_id": 123,
                "identifier": "technews",
                "is_id_based": False,
                "title": "Tech News",
                "subscribers": 10000,
                "analysis": {
                    "audience": "IT-специалисты 25-40 лет",
                    "keywords": ["python", "django", "backend"],
                    "tone": "Профессиональный",
                    "source": "llm",
                    "confidence": 0.9
                },
                "analyzed_posts": 50,
                "analysis_duration_ms": 5000
            }
        }


class KeywordsSuggestionSchema(BaseSchema):
    """
    Schema для предложения дополнительных keywords.
    
    Используется для улучшения анализа.
    """
    
    suggested_keywords: List[str] = Field(
        ...,
        description="Предлагаемые ключевые слова",
        min_items=1,
        max_items=20
    )
    reason: str = Field(
        ...,
        description="Причина предложения",
        max_length=500
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Уверенность в предложении"
    )

