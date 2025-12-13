"""
Analysis Result Entity

Доменная модель результата анализа канала.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class AnalysisResult:
    """
    Результат анализа канала через LLM.
    
    Содержит:
    - Целевую аудиторию
    - Ключевые слова
    - Тональность
    """
    
    audience: str
    keywords: List[str]
    tone: str = ""
    
    # Метаданные анализа
    source: str = "llm"  # llm | fallback | manual
    confidence: float = 1.0  # 0.0 - 1.0
    
    def __post_init__(self):
        """Валидация после инициализации."""
        # Очистка keywords от пустых значений
        self.keywords = [kw.strip() for kw in self.keywords if kw and kw.strip()]
        
        # Нормализация confidence
        if self.confidence < 0:
            self.confidence = 0.0
        elif self.confidence > 1.0:
            self.confidence = 1.0
    
    @property
    def is_from_llm(self) -> bool:
        """Был ли результат получен из LLM."""
        return self.source == "llm"
    
    @property
    def is_fallback(self) -> bool:
        """Был ли результат fallback (LLM не сработал)."""
        return self.source == "fallback"
    
    @property
    def has_keywords(self) -> bool:
        """Есть ли ключевые слова."""
        return bool(self.keywords)
    
    @property
    def has_audience(self) -> bool:
        """Есть ли описание аудитории."""
        return bool(self.audience and self.audience.strip())
    
    @property
    def is_empty(self) -> bool:
        """Пустой ли результат."""
        return not self.has_keywords and not self.has_audience
    
    def to_dict(self) -> dict:
        """Преобразует в словарь для сериализации."""
        return {
            "audience": self.audience,
            "keywords": self.keywords,
            "tone": self.tone,
            "source": self.source,
            "confidence": self.confidence,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AnalysisResult":
        """Создаёт из словаря."""
        return cls(
            audience=data.get("audience", ""),
            keywords=data.get("keywords", []),
            tone=data.get("tone", ""),
            source=data.get("source", "llm"),
            confidence=data.get("confidence", 1.0),
        )
    
    @classmethod
    def empty(cls, reason: str = "Нет данных для анализа") -> "AnalysisResult":
        """
        Создаёт пустой результат анализа.
        Используется когда анализ невозможен.
        """
        return cls(
            audience=reason,
            keywords=[],
            tone="",
            source="fallback",
            confidence=0.0,
        )
    
    @classmethod
    def from_fallback(cls, keywords: List[str], reason: str = None) -> "AnalysisResult":
        """
        Создаёт fallback результат (когда LLM не сработал).
        """
        audience = reason or "Не удалось получить анализ от LLM"
        
        return cls(
            audience=audience,
            keywords=keywords,
            tone="",
            source="fallback",
            confidence=0.5,  # Средняя уверенность
        )
    
    def __str__(self) -> str:
        return f"AnalysisResult(keywords={len(self.keywords)}, source={self.source})"
    
    def __repr__(self) -> str:
        return (
            f"AnalysisResult("
            f"keywords={self.keywords!r}, "
            f"source={self.source!r}, "
            f"confidence={self.confidence})"
        )

