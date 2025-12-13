"""
Telegram Schemas

Pydantic models для Telegram-специфичных данных.
"""

from typing import Optional, Literal
from pydantic import Field, field_validator

from .base import BaseSchema


class CallbackDataSchema(BaseSchema):
    """
    Schema для парсинга callback_data от inline кнопок.
    
    Форматы:
    - analyze:username:10
    - analyze:id:CHANNEL_ID:10
    - force_analyze:username:10
    - analyze_website|URL|10
    """
    
    action: Literal["analyze", "force_analyze", "analyze_website"] = Field(
        ...,
        description="Тип действия"
    )
    identifier: str = Field(
        ...,
        description="Идентификатор (username, ID или URL)"
    )
    top_n: int = Field(
        ...,
        ge=1,
        le=500,
        description="Количество похожих каналов"
    )
    is_id_based: bool = Field(
        False,
        description="Это ID канала (не username)"
    )
    
    @classmethod
    def from_callback_string(cls, callback_data: str) -> "CallbackDataSchema":
        """
        Парсит callback_data string в schema.
        
        Args:
            callback_data: Строка формата "action:identifier:top_n" или "action:id:ID:top_n"
        
        Returns:
            CallbackDataSchema
        
        Raises:
            ValueError: если формат неверный
        
        Examples:
            >>> CallbackDataSchema.from_callback_string("analyze:channel:10")
            >>> CallbackDataSchema.from_callback_string("analyze:id:-1002508742544:10")
            >>> CallbackDataSchema.from_callback_string("analyze_website|https://example.com|10")
        """
        # Для website используем | как разделитель (: может быть в URL)
        if callback_data.startswith("analyze_website"):
            parts = callback_data.split("|")
            if len(parts) != 3:
                raise ValueError(f"Invalid website callback format: {callback_data}")
            
            import urllib.parse
            url = urllib.parse.unquote(parts[1])
            
            return cls(
                action="analyze_website",
                identifier=url,
                top_n=int(parts[2]),
                is_id_based=False
            )
        
        # Для каналов используем :
        parts = callback_data.split(":")
        
        if len(parts) == 3:
            # Формат: action:username:N
            action, identifier, top_n_str = parts
            is_id_based = False
        elif len(parts) == 4 and parts[1] == "id":
            # Формат: action:id:CHANNEL_ID:N
            action, _, identifier, top_n_str = parts
            is_id_based = True
        else:
            raise ValueError(f"Invalid callback format: {callback_data}")
        
        try:
            top_n = int(top_n_str)
        except ValueError:
            raise ValueError(f"Invalid top_n value: {top_n_str}")
        
        return cls(
            action=action,
            identifier=identifier,
            top_n=top_n,
            is_id_based=is_id_based
        )
    
    def to_callback_string(self) -> str:
        """
        Преобразует schema обратно в callback_data string.
        
        Returns:
            Строка для callback_data
        """
        if self.action == "analyze_website":
            import urllib.parse
            url_encoded = urllib.parse.quote(self.identifier, safe='')
            return f"analyze_website|{url_encoded}|{self.top_n}"
        
        if self.is_id_based:
            return f"{self.action}:id:{self.identifier}:{self.top_n}"
        else:
            return f"{self.action}:{self.identifier}:{self.top_n}"
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "action": "analyze",
                    "identifier": "technews",
                    "top_n": 10,
                    "is_id_based": False
                },
                {
                    "action": "analyze",
                    "identifier": "-1002508742544",
                    "top_n": 25,
                    "is_id_based": True
                },
                {
                    "action": "analyze_website",
                    "identifier": "https://example.com",
                    "top_n": 50,
                    "is_id_based": False
                }
            ]
        }


class ChannelInfoSchema(BaseSchema):
    """
    Schema для информации о канале из Telegram API.
    
    Получается через Telethon при парсинге канала.
    """
    
    id: int = Field(..., description="Telegram ID канала")
    username: Optional[str] = Field(
        None,
        description="Username канала (без @)"
    )
    title: str = Field(..., description="Название канала")
    about: Optional[str] = Field(
        None,
        description="Описание канала",
        alias="description"
    )
    participants_count: int = Field(
        0,
        ge=0,
        description="Количество подписчиков",
        alias="subscribers"
    )
    
    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: Optional[str]) -> Optional[str]:
        """Нормализует username (удаляет @)."""
        if v:
            return v.lstrip("@")
        return v
    
    @property
    def is_private(self) -> bool:
        """Является ли канал приватным (без username)."""
        return not bool(self.username)
    
    @property
    def identifier_for_db(self) -> str:
        """Идентификатор для сохранения в БД."""
        if self.username:
            return self.username
        return f"id:{self.id}"
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "id": -1002508742544,
                "username": "technews",
                "title": "Tech News",
                "about": "Latest technology news and updates",
                "participants_count": 10000
            }
        }


class TelegramPostSchema(BaseSchema):
    """
    Schema для поста из Telegram.
    
    Получается через Telethon.
    """
    
    message_id: int = Field(..., description="ID сообщения")
    date: str = Field(..., description="Дата публикации (ISO format)")
    views: int = Field(0, ge=0, description="Просмотры")
    forwards: int = Field(0, ge=0, description="Пересылки")
    text: str = Field("", description="Текст поста")
    forwarded_from_id: Optional[int] = Field(
        None,
        description="ID канала-источника (если переслано)"
    )
    
    @property
    def has_text(self) -> bool:
        """Есть ли текст в посте."""
        return bool(self.text.strip())
    
    @property
    def engagement_rate(self) -> float:
        """Engagement rate = (forwards / views) если есть просмотры."""
        if self.views == 0:
            return 0.0
        return self.forwards / self.views

