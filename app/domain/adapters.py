"""
Domain Adapters

Функции-адаптеры для интеграции domain layer с существующим кодом.
Позволяют постепенно мигрировать на новую архитектуру.
"""

from typing import Tuple, Optional

from .value_objects import ChannelIdentifier
from .exceptions import InvalidChannelIdentifierError


def parse_channel_identifier(raw_value: str) -> Tuple[str, str, bool]:
    """
    Адаптер для существующего кода.
    Парсит идентификатор канала и возвращает кортеж (identifier, title, is_id_based).
    
    Используется для постепенной замены старой функции _extract_channel_from_message.
    
    Args:
        raw_value: Сырое значение (username, ID, или @username)
    
    Returns:
        (identifier, title, is_id_based) - как в старом коде
    
    Raises:
        InvalidChannelIdentifierError: если значение некорректно
    
    Example:
        >>> parse_channel_identifier("@channel")
        ("channel", "channel", False)
        >>> parse_channel_identifier("-1002508742544")
        ("-1002508742544", "ID: -1002508742544", True)
    """
    try:
        channel_id = ChannelIdentifier.from_raw(raw_value)
    except InvalidChannelIdentifierError:
        raise
    
    # Для совместимости со старым кодом
    if channel_id.is_id_based:
        # Для ID: возвращаем чистый ID (без префикса "id:")
        clean_id = channel_id.normalized_value.replace("id:", "")
        title = f"ID: {clean_id}"
        identifier = clean_id
    else:
        identifier = channel_id.normalized_value
        title = identifier
    
    return identifier, title, channel_id.is_id_based


def create_callback_data_for_analysis(
    identifier: str,
    is_id_based: bool,
    top_n: int
) -> str:
    """
    Создаёт callback_data для кнопок анализа.
    
    Формат:
    - Обычный канал: "analyze:channel:10"
    - ID-based канал: "analyze:id:CHANNEL_ID:10"
    
    Args:
        identifier: username или ID
        is_id_based: True если это ID
        top_n: количество похожих каналов
    
    Returns:
        Строка callback_data
    
    Example:
        >>> create_callback_data_for_analysis("channel", False, 10)
        "analyze:channel:10"
        >>> create_callback_data_for_analysis("-1002508742544", True, 10)
        "analyze:id:-1002508742544:10"
    """
    if is_id_based:
        return f"analyze:id:{identifier}:{top_n}"
    else:
        return f"analyze:{identifier}:{top_n}"


def parse_callback_data_from_analysis(callback_data: str) -> Tuple[str, int, bool]:
    """
    Парсит callback_data от кнопок анализа.
    
    Args:
        callback_data: Строка формата "analyze:..." или "analyze:id:..."
    
    Returns:
        (identifier, top_n, is_id_based)
    
    Raises:
        ValueError: если формат неверный
    
    Example:
        >>> parse_callback_data_from_analysis("analyze:channel:10")
        ("channel", 10, False)
        >>> parse_callback_data_from_analysis("analyze:id:-1002508742544:10")
        ("-1002508742544", 10, True)
    """
    parts = callback_data.split(":")
    
    if len(parts) == 3:
        # Формат: analyze:username:N
        _, identifier, top_n_str = parts
        is_id_based = False
    elif len(parts) == 4 and parts[1] == "id":
        # Формат: analyze:id:CHANNEL_ID:N
        _, _, identifier, top_n_str = parts
        is_id_based = True
    else:
        raise ValueError(f"Invalid callback data format: {callback_data}")
    
    try:
        top_n = int(top_n_str)
    except ValueError:
        raise ValueError(f"Invalid top_n value in callback data: {top_n_str}")
    
    return identifier, top_n, is_id_based


def normalize_identifier_for_db(raw_value: str) -> str:
    """
    Нормализует идентификатор для сохранения в БД.
    
    Args:
        raw_value: Сырое значение
    
    Returns:
        Нормализованное значение для БД
    
    Example:
        >>> normalize_identifier_for_db("@channel")
        "channel"
        >>> normalize_identifier_for_db("-1002508742544")
        "id:-1002508742544"
    """
    try:
        channel_id = ChannelIdentifier.from_raw(raw_value)
        return channel_id.to_db_format()
    except InvalidChannelIdentifierError:
        # Fallback: возвращаем как есть (для обратной совместимости)
        return raw_value.strip().lstrip("@")


def get_display_name(identifier: str, is_id_based: bool) -> str:
    """
    Возвращает отображаемое имя канала.
    
    Args:
        identifier: username или ID
        is_id_based: True если это ID
    
    Returns:
        Отображаемое имя
    
    Example:
        >>> get_display_name("channel", False)
        "@channel"
        >>> get_display_name("-1002508742544", True)
        "ID: -1002508742544"
    """
    if is_id_based:
        return f"ID: {identifier}"
    else:
        return f"@{identifier}"

