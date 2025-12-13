"""
Channel Entity

Доменная модель канала с бизнес-логикой.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from app.domain.value_objects import ChannelIdentifier


@dataclass
class ChannelEntity:
    """
    Доменная сущность Telegram канала.
    
    Содержит бизнес-логику работы с каналом.
    Независима от БД (не содержит ORM-специфичных полей).
    """
    
    identifier: ChannelIdentifier
    title: str
    description: str = ""
    subscribers: int = 0
    keywords: List[str] = field(default_factory=list)
    last_update: Optional[datetime] = None
    
    # ID в базе данных (опционально, заполняется после сохранения)
    db_id: Optional[int] = None
    
    def __post_init__(self):
        """Валидация после инициализации."""
        if self.subscribers < 0:
            self.subscribers = 0
        
        if not self.title:
            # Fallback: используем identifier как title
            self.title = self.identifier.to_display_format()
    
    @property
    def is_private(self) -> bool:
        """Является ли канал приватным (без публичного username)."""
        return self.identifier.is_id_based
    
    @property
    def has_keywords(self) -> bool:
        """Есть ли у канала ключевые слова."""
        return bool(self.keywords)
    
    @property
    def is_analyzed(self) -> bool:
        """Был ли канал проанализирован (есть keywords и last_update)."""
        return self.has_keywords and self.last_update is not None
    
    def update_metadata(
        self,
        title: str = None,
        description: str = None,
        subscribers: int = None
    ) -> None:
        """Обновляет метаданные канала."""
        if title is not None:
            self.title = title
        
        if description is not None:
            self.description = description
        
        if subscribers is not None and subscribers >= 0:
            self.subscribers = subscribers
        
        self.last_update = datetime.utcnow()
    
    def update_keywords(self, keywords: List[str]) -> None:
        """Обновляет ключевые слова канала."""
        self.keywords = keywords
        self.last_update = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """
        Преобразует entity в словарь для передачи между слоями.
        """
        return {
            "identifier": self.identifier.normalized_value,
            "is_id_based": self.identifier.is_id_based,
            "title": self.title,
            "description": self.description,
            "subscribers": self.subscribers,
            "keywords": self.keywords,
            "last_update": self.last_update,
            "db_id": self.db_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ChannelEntity":
        """
        Создаёт entity из словаря.
        """
        identifier = ChannelIdentifier.from_raw(data["identifier"])
        
        return cls(
            identifier=identifier,
            title=data.get("title", ""),
            description=data.get("description", ""),
            subscribers=data.get("subscribers", 0),
            keywords=data.get("keywords", []),
            last_update=data.get("last_update"),
            db_id=data.get("db_id"),
        )
    
    def __str__(self) -> str:
        """Строковое представление для логов."""
        return f"Channel({self.identifier}, {self.subscribers} subscribers)"
    
    def __repr__(self) -> str:
        return (
            f"ChannelEntity("
            f"identifier={self.identifier!r}, "
            f"title={self.title!r}, "
            f"subscribers={self.subscribers})"
        )

