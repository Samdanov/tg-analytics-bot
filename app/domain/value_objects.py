"""
Value Objects

Неизменяемые объекты со своей логикой и валидацией.
"""

import re
from dataclasses import dataclass
from typing import Optional

from .exceptions import InvalidChannelIdentifierError


@dataclass(frozen=True)
class ChannelIdentifier:
    """
    Value Object для идентификации Telegram канала.
    
    Может представлять:
    - Обычный канал с username (@channel или channel)
    - Приватный канал с ID (числовой ID или id:12345)
    
    Immutable: после создания изменить нельзя.
    """
    
    raw_value: str
    normalized_value: str
    is_id_based: bool
    
    @classmethod
    def from_raw(cls, raw_value: str) -> "ChannelIdentifier":
        """
        Создаёт ChannelIdentifier из сырого значения.
        
        Примеры:
        - "@channel" -> ChannelIdentifier(raw="@channel", normalized="channel", is_id_based=False)
        - "channel" -> ChannelIdentifier(raw="channel", normalized="channel", is_id_based=False)
        - "-1002508742544" -> ChannelIdentifier(raw="-1002508742544", normalized="id:-1002508742544", is_id_based=True)
        - "id:-1002508742544" -> ChannelIdentifier(raw="id:-1002508742544", normalized="id:-1002508742544", is_id_based=True)
        
        Args:
            raw_value: Сырое значение (username или ID)
        
        Returns:
            ChannelIdentifier
        
        Raises:
            InvalidChannelIdentifierError: если значение некорректно
        """
        if not raw_value or not isinstance(raw_value, str):
            raise InvalidChannelIdentifierError(
                str(raw_value),
                "Value must be a non-empty string"
            )
        
        cleaned = raw_value.strip()
        if not cleaned:
            raise InvalidChannelIdentifierError(
                raw_value,
                "Value cannot be empty or whitespace"
            )
        
        # Проверка на ID канала (число, возможно с минусом)
        # ID могут быть: -1002508742544 или id:-1002508742544
        if cleaned.startswith("id:"):
            # Формат: "id:-1002508742544"
            channel_id_part = cleaned[3:]  # Убираем префикс "id:"
            if not channel_id_part.lstrip('-').isdigit():
                raise InvalidChannelIdentifierError(
                    raw_value,
                    "ID-based identifier must be numeric after 'id:' prefix"
                )
            return cls(
                raw_value=raw_value,
                normalized_value=cleaned,  # Оставляем как есть
                is_id_based=True
            )
        
        elif cleaned.lstrip('-').isdigit():
            # Формат: "-1002508742544" (чистое число)
            normalized = f"id:{cleaned}"
            return cls(
                raw_value=raw_value,
                normalized_value=normalized,
                is_id_based=True
            )
        
        else:
            # Обычный username
            # Убираем @ если есть, проверяем формат
            username = cleaned.lstrip("@")
            
            # Валидация username (3-32 символа, латиница, цифры, подчеркивания)
            if not re.match(r'^[A-Za-z0-9_]{3,32}$', username):
                raise InvalidChannelIdentifierError(
                    raw_value,
                    "Username must be 3-32 characters, alphanumeric and underscores only"
                )
            
            return cls(
                raw_value=raw_value,
                normalized_value=username,  # Без @
                is_id_based=False
            )
    
    @classmethod
    def from_telegram_id(cls, telegram_id: int, title: str = None) -> "ChannelIdentifier":
        """
        Создаёт ChannelIdentifier из Telegram ID.
        Используется для приватных каналов.
        
        Args:
            telegram_id: Числовой ID канала (например, -1002508742544)
            title: Название канала (опционально, для логирования)
        
        Returns:
            ChannelIdentifier
        """
        raw = str(telegram_id)
        normalized = f"id:{telegram_id}"
        return cls(
            raw_value=raw,
            normalized_value=normalized,
            is_id_based=True
        )
    
    def to_db_format(self) -> str:
        """
        Возвращает формат для сохранения в БД.
        
        Для БД всегда используем normalized_value:
        - Username: "channel" (без @)
        - ID: "id:-1002508742544"
        """
        return self.normalized_value
    
    def to_display_format(self) -> str:
        """
        Возвращает формат для отображения пользователю.
        
        - Username: "@channel"
        - ID: "ID: -1002508742544"
        """
        if self.is_id_based:
            # Убираем префикс "id:" для отображения
            channel_id = self.normalized_value.replace("id:", "")
            return f"ID: {channel_id}"
        else:
            return f"@{self.normalized_value}"
    
    def to_file_name(self) -> str:
        """
        Возвращает безопасное имя для использования в именах файлов.
        
        - Username: "channel"
        - ID: "id_-1002508742544"
        """
        if self.is_id_based:
            # Заменяем : на _ для имен файлов
            return self.normalized_value.replace(":", "_")
        else:
            return self.normalized_value
    
    def to_telethon_format(self) -> str:
        """
        Возвращает формат для использования с Telethon API.
        
        - Username: "channel" (без @)
        - ID: "-1002508742544" (число как строка, без префикса "id:")
        """
        if self.is_id_based:
            # Убираем префикс "id:" для Telethon
            return self.normalized_value.replace("id:", "")
        else:
            # Для username возвращаем без @
            return self.normalized_value
    
    @property
    def username(self) -> Optional[str]:
        """
        Возвращает username канала (без @) или None для ID-based каналов.
        
        - Username канал: "channel"
        - ID канал: None
        """
        if self.is_id_based:
            return None
        return self.normalized_value
    
    @property
    def channel_id(self) -> Optional[int]:
        """
        Возвращает числовой ID канала или None для username-based каналов.
        
        - Username канал: None
        - ID канал: -1002508742544
        """
        if not self.is_id_based:
            return None
        # Убираем префикс "id:" и конвертируем в int
        id_str = self.normalized_value.replace("id:", "")
        return int(id_str)
    
    def __str__(self) -> str:
        """Строковое представление."""
        return self.to_display_format()
    
    def __repr__(self) -> str:
        """Representation для дебага."""
        return f"ChannelIdentifier(value={self.normalized_value!r}, is_id_based={self.is_id_based})"

