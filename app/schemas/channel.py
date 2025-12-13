"""
Channel Schemas

Pydantic models для работы с каналами.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import Field, field_validator, model_validator

from .base import BaseSchema, TimestampMixin
from app.domain import ChannelIdentifier, InvalidChannelIdentifierError


class ChannelIdentifierSchema(BaseSchema):
    """
    Schema для идентификатора канала.
    
    Интегрируется с domain.ChannelIdentifier.
    """
    
    raw_value: str = Field(
        ...,
        description="Сырое значение (username или ID)",
        min_length=1,
        examples=["@channel", "channel", "-1002508742544"]
    )
    
    @field_validator("raw_value")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Валидация через domain layer."""
        try:
            # Проверяем через domain layer
            ChannelIdentifier.from_raw(v)
            return v
        except InvalidChannelIdentifierError as e:
            raise ValueError(str(e))
    
    def to_domain(self) -> ChannelIdentifier:
        """Преобразует в domain model."""
        return ChannelIdentifier.from_raw(self.raw_value)


class ChannelCreateSchema(BaseSchema):
    """
    Schema для создания канала.
    
    Используется при добавлении нового канала в систему.
    """
    
    identifier: str = Field(
        ...,
        description="Идентификатор канала (username или ID)",
        examples=["@technews", "-1002508742544"]
    )
    title: Optional[str] = Field(
        None,
        description="Название канала",
        max_length=255
    )
    description: Optional[str] = Field(
        None,
        description="Описание канала",
        max_length=5000
    )
    subscribers: int = Field(
        0,
        ge=0,
        description="Количество подписчиков"
    )
    
    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Валидация идентификатора."""
        try:
            ChannelIdentifier.from_raw(v)
            return v
        except InvalidChannelIdentifierError as e:
            raise ValueError(f"Invalid identifier: {e}")
    
    @field_validator("title", "description")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Удаляет лишние пробелы."""
        if v:
            return v.strip()
        return v


class ChannelResponseSchema(BaseSchema, TimestampMixin):
    """
    Schema для ответа с данными канала.
    
    Возвращается из API/use cases.
    """
    
    id: int = Field(..., description="ID канала в БД")
    identifier: str = Field(..., description="Идентификатор канала")
    is_id_based: bool = Field(..., description="Канал по ID (без username)")
    title: str = Field(..., description="Название канала")
    description: Optional[str] = Field(None, description="Описание")
    subscribers: int = Field(..., description="Количество подписчиков")
    keywords: List[str] = Field(
        default_factory=list,
        description="Ключевые слова"
    )
    last_update: Optional[datetime] = Field(
        None,
        description="Дата последнего обновления данных"
    )
    
    # Computed fields
    @property
    def display_name(self) -> str:
        """Отображаемое имя канала."""
        if self.is_id_based:
            return f"ID: {self.identifier.replace('id:', '')}"
        return f"@{self.identifier}"
    
    @property
    def is_analyzed(self) -> bool:
        """Был ли канал проанализирован."""
        return bool(self.keywords) and self.last_update is not None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 123,
                "identifier": "technews",
                "is_id_based": False,
                "title": "Tech News",
                "description": "Latest tech news",
                "subscribers": 10000,
                "keywords": ["tech", "news", "innovation"],
                "last_update": "2025-12-13T10:00:00",
                "created_at": "2025-12-01T10:00:00"
            }
        }


class ChannelUpdateSchema(BaseSchema):
    """
    Schema для обновления канала.
    
    Все поля опциональны (partial update).
    """
    
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    subscribers: Optional[int] = Field(None, ge=0)
    keywords: Optional[List[str]] = None
    
    @model_validator(mode='after')
    def check_at_least_one_field(self):
        """Проверяет, что хотя бы одно поле заполнено."""
        if not any([
            self.title,
            self.description,
            self.subscribers is not None,
            self.keywords
        ]):
            raise ValueError("At least one field must be provided for update")
        return self


class PostSchema(BaseSchema):
    """Schema для поста канала."""
    
    date: datetime = Field(..., description="Дата публикации")
    views: int = Field(0, ge=0, description="Количество просмотров")
    forwards: int = Field(0, ge=0, description="Количество пересылок")
    text: str = Field("", description="Текст поста")
    forwarded_from_id: Optional[int] = Field(
        None,
        description="ID канала, откуда переслан пост"
    )


class ChannelWithPostsSchema(ChannelResponseSchema):
    """
    Schema канала с постами.
    
    Расширяет ChannelResponseSchema, добавляя список постов.
    """
    
    posts: List[PostSchema] = Field(
        default_factory=list,
        description="Последние посты канала"
    )
    posts_count: int = Field(0, ge=0, description="Общее количество постов")
    
    @property
    def avg_views(self) -> float:
        """Средние просмотры на пост."""
        if not self.posts:
            return 0.0
        return sum(p.views for p in self.posts) / len(self.posts)
    
    @property
    def avg_forwards(self) -> float:
        """Средние пересылки на пост."""
        if not self.posts:
            return 0.0
        return sum(p.forwards for p in self.posts) / len(self.posts)

