"""
Custom Validators

Кастомные валидаторы для Pydantic schemas.
"""

import re
from typing import Any
from pydantic import field_validator


def validate_telegram_username(v: str) -> str:
    """
    Валидатор для Telegram username.
    
    Правила:
    - 3-32 символа
    - Только латиница, цифры, подчеркивания
    - Может начинаться с @
    
    Args:
        v: Username для валидации
    
    Returns:
        Нормализованный username (без @)
    
    Raises:
        ValueError: если username некорректный
    """
    if not v:
        raise ValueError("Username cannot be empty")
    
    # Убираем @ если есть
    username = v.lstrip("@")
    
    # Проверяем длину
    if len(username) < 3 or len(username) > 32:
        raise ValueError("Username must be 3-32 characters long")
    
    # Проверяем формат (только латиница, цифры, подчеркивания)
    if not re.match(r'^[A-Za-z0-9_]+$', username):
        raise ValueError("Username can only contain letters, numbers, and underscores")
    
    return username


def validate_channel_id(v: Any) -> int:
    """
    Валидатор для Telegram channel ID.
    
    Channel ID обычно отрицательные большие числа.
    
    Args:
        v: Channel ID для валидации
    
    Returns:
        Валидированный channel ID
    
    Raises:
        ValueError: если ID некорректный
    """
    try:
        channel_id = int(v)
    except (ValueError, TypeError):
        raise ValueError(f"Channel ID must be an integer, got: {type(v).__name__}")
    
    # Telegram channel IDs обычно < -1000000000000
    if channel_id >= 0:
        raise ValueError("Channel ID must be negative")
    
    return channel_id


def validate_keywords_list(v: list) -> list:
    """
    Валидатор для списка ключевых слов.
    
    - Удаляет пустые значения
    - Удаляет дубликаты
    - Ограничивает длину каждого keyword
    
    Args:
        v: Список keywords
    
    Returns:
        Очищенный список keywords
    """
    if not isinstance(v, list):
        raise ValueError("Keywords must be a list")
    
    cleaned = []
    seen = set()
    
    for kw in v:
        if not isinstance(kw, str):
            continue
        
        kw = kw.strip()
        
        # Пропускаем пустые
        if not kw:
            continue
        
        # Пропускаем слишком длинные
        if len(kw) > 100:
            continue
        
        # Пропускаем дубликаты (case-insensitive)
        kw_lower = kw.lower()
        if kw_lower in seen:
            continue
        
        seen.add(kw_lower)
        cleaned.append(kw)
    
    return cleaned


def validate_url(v: str) -> str:
    """
    Валидатор для URL.
    
    Проверяет базовый формат URL.
    
    Args:
        v: URL для валидации
    
    Returns:
        Нормализованный URL
    
    Raises:
        ValueError: если URL некорректный
    """
    if not v:
        raise ValueError("URL cannot be empty")
    
    v = v.strip()
    
    # Проверяем базовый формат
    url_pattern = re.compile(
        r'^https?://'  # http:// или https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # опциональный порт
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    if not url_pattern.match(v):
        raise ValueError(f"Invalid URL format: {v}")
    
    return v


def validate_score(v: float) -> float:
    """
    Валидатор для similarity score.
    
    Score должен быть в диапазоне [0.0, 1.0].
    
    Args:
        v: Score для валидации
    
    Returns:
        Валидированный score
    
    Raises:
        ValueError: если score некорректный
    """
    try:
        score = float(v)
    except (ValueError, TypeError):
        raise ValueError(f"Score must be a number, got: {type(v).__name__}")
    
    if score < 0.0 or score > 1.0:
        raise ValueError(f"Score must be between 0.0 and 1.0, got: {score}")
    
    # Округляем до 4 знаков после запятой
    return round(score, 4)


def validate_positive_int(v: Any, field_name: str = "value") -> int:
    """
    Валидатор для положительного целого числа.
    
    Args:
        v: Значение для валидации
        field_name: Название поля (для сообщения об ошибке)
    
    Returns:
        Валидированное целое число
    
    Raises:
        ValueError: если значение некорректно
    """
    try:
        value = int(v)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be an integer, got: {type(v).__name__}")
    
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative, got: {value}")
    
    return value


# Декораторы для использования в schemas
class TelegramUsernameValidator:
    """Декоратор-валидатор для Telegram username."""
    
    @field_validator("username")
    @classmethod
    def validate(cls, v: str) -> str:
        return validate_telegram_username(v)


class KeywordsValidator:
    """Декоратор-валидатор для keywords."""
    
    @field_validator("keywords")
    @classmethod
    def validate(cls, v: list) -> list:
        return validate_keywords_list(v)


class ScoreValidator:
    """Декоратор-валидатор для score."""
    
    @field_validator("score")
    @classmethod
    def validate(cls, v: float) -> float:
        return validate_score(v)

