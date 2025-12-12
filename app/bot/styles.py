# app/bot/styles.py

"""
Стилизация бота "ОРБИТА" на основе космической темы.
Цветовая палитра и иконки вдохновлены аватаркой бота.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Tuple


# ============================================================================
# ЦВЕТОВАЯ ПАЛИТРА (на основе аватарки)
# ============================================================================

class Colors:
    """Цветовая палитра в стиле ОРБИТА."""
    
    # Основные цвета фона (глубокий космос)
    SPACE_DARK = "#0a0e27"  # Глубокий индиго/темно-синий
    SPACE_PURPLE = "#1a0f2e"  # Насыщенный фиолетовый
    
    # Неоновые акценты (светящиеся элементы)
    NEON_CYAN = "#00ffff"  # Яркий циан
    NEON_BLUE = "#0080ff"  # Электрический синий
    NEON_MAGENTA = "#ff00ff"  # Яркий пурпурный/розовый
    NEON_GOLD = "#ffd700"  # Золотой акцент
    
    # Вторичные цвета
    TEXT_WHITE = "#ffffff"  # Белый для текста
    TEXT_MUTED = "#6b7280"  # Приглушенный серый


# ============================================================================
# ИКОНКИ (космические и аналитические)
# ============================================================================

class Icons:
    """Иконки в стиле ОРБИТА."""
    
    # Основные иконки
    BOT = "🚀"  # Ракета (астронавт/бот)
    ORBIT = "🌌"  # Орбита/космос
    ANALYTICS = "📊"  # Аналитика (столбчатая диаграмма)
    CHART = "📈"  # График
    PIE_CHART = "🥧"  # Круговая диаграмма
    DATA = "💾"  # Данные
    
    # Действия
    SEARCH = "🔍"  # Поиск
    START = "▶️"  # Старт
    LOADING = "⏳"  # Загрузка
    SUCCESS = "✅"  # Успех
    ERROR = "❌"  # Ошибка
    WARNING = "⚠️"  # Предупреждение
    
    # Каналы и пользователи
    CHANNEL = "📢"  # Канал
    USERS = "👥"  # Пользователи
    SUBSCRIBERS = "👤"  # Подписчики
    KEYWORDS = "🔑"  # Ключевые слова
    TARGET = "🎯"  # Целевая аудитория
    
    # Космические элементы
    STAR = "⭐"  # Звезда
    PLANET = "🪐"  # Планета
    SATELLITE = "🛰️"  # Спутник
    COMET = "☄️"  # Комета
    
    # Числа для кнопок (космические символы)
    NUM_10 = "⭐"  # 10 - звезда
    NUM_25 = "🪐"  # 25 - планета
    NUM_50 = "🛰️"  # 50 - спутник
    NUM_100 = "🌌"  # 100 - галактика
    NUM_500 = "🚀"  # 500 - ракета (максимум)


# ============================================================================
# ФУНКЦИИ ДЛЯ СОЗДАНИЯ СТИЛИЗОВАННЫХ КНОПОК
# ============================================================================

def create_orbita_button(text: str, callback_data: str, icon: str = None) -> InlineKeyboardButton:
    """
    Создает стилизованную кнопку в стиле ОРБИТА.
    
    Args:
        text: Текст кнопки
        callback_data: Данные для callback
        icon: Иконка (опционально)
    
    Returns:
        InlineKeyboardButton
    """
    if icon:
        button_text = f"{icon} {text}"
    else:
        button_text = text
    
    return InlineKeyboardButton(text=button_text, callback_data=callback_data)


def create_analysis_buttons(identifier: str, is_id_based: bool = False) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора количества каналов для анализа.
    Стилизована в стиле ОРБИТА.
    
    Args:
        identifier: username или ID канала
        is_id_based: True если это ID-based канал
    
    Returns:
        InlineKeyboardMarkup
    """
    callback_prefix = f"id:{identifier}" if is_id_based else identifier
    
    buttons = [
        [
            create_orbita_button("10 каналов", f"analyze:{callback_prefix}:10", Icons.NUM_10),
            create_orbita_button("25 каналов", f"analyze:{callback_prefix}:25", Icons.NUM_25),
        ],
        [
            create_orbita_button("50 каналов", f"analyze:{callback_prefix}:50", Icons.NUM_50),
            create_orbita_button("100 каналов", f"analyze:{callback_prefix}:100", Icons.NUM_100),
        ],
        [
            create_orbita_button("500 каналов (макс)", f"analyze:{callback_prefix}:500", Icons.NUM_500),
        ],
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_channel_selection_buttons(channels: List[Tuple[str, int]], top_n: int, current_identifier: str = None, is_id_based: bool = False) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора канала из списка похожих.
    Стилизована в стиле ОРБИТА.
    
    Args:
        channels: Список кортежей (username, count)
        top_n: Количество каналов для анализа
        current_identifier: Идентификатор текущего канала (для принудительного анализа)
        is_id_based: True если текущий канал ID-based
    
    Returns:
        InlineKeyboardMarkup
    """
    buttons = []
    
    for username, count in channels[:8]:  # Показываем топ-8
        button_text = f"{Icons.CHANNEL} @{username}"
        if count > 1:
            button_text += f" ({count} упоминаний)"
        buttons.append([
            create_orbita_button(button_text, f"analyze:{username}:{top_n}")
        ])
    
    # Кнопка "Принудительный анализ"
    if current_identifier:
        if is_id_based:
            force_callback = f"force_analyze:id:{current_identifier}:{top_n}"
            button_text = f"Все равно анализировать (ID: {current_identifier})"
        else:
            force_callback = f"force_analyze:{current_identifier}:{top_n}"
            button_text = f"Все равно анализировать @{current_identifier}"
        buttons.append([
            create_orbita_button(button_text, force_callback, Icons.WARNING)
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================================================
# ФУНКЦИИ ДЛЯ ФОРМАТИРОВАНИЯ ТЕКСТА
# ============================================================================

def format_header(text: str) -> str:
    """
    Форматирует заголовок в стиле ОРБИТА.
    
    Args:
        text: Текст заголовка
    
    Returns:
        Отформатированный текст
    """
    return f"{Icons.ORBIT} <b>{text}</b> {Icons.ORBIT}"


def format_section(title: str, content: str, icon: str = None) -> str:
    """
    Форматирует секцию сообщения в стиле ОРБИТА.
    
    Args:
        title: Заголовок секции
        content: Содержимое секции
        icon: Иконка (опционально)
    
    Returns:
        Отформатированный текст
    """
    if icon:
        header = f"{icon} <b>{title}:</b>"
    else:
        header = f"<b>{title}:</b>"
    
    return f"{header}\n{content}"


def format_channel_info(identifier: str, title: str = None, is_id_based: bool = False) -> str:
    """
    Форматирует информацию о канале в стиле ОРБИТА.
    
    Args:
        identifier: username или ID канала
        title: Название канала
        is_id_based: True если это ID-based канал
    
    Returns:
        Отформатированный текст
    """
    if is_id_based:
        return (
            f"{Icons.SATELLITE} <b>Найден канал без публичной ссылки:</b>\n"
            f"<b>{title or 'Неизвестный канал'}</b>\n"
            f"{Icons.DATA} ID: <code>{identifier}</code>\n\n"
            f"{Icons.ANALYTICS} Выбери количество похожих каналов для анализа:"
        )
    else:
        return (
            f"{Icons.CHANNEL} <b>Найден канал:</b>\n"
            f"<b>{title or identifier}</b>\n"
            f"{Icons.ORBIT} @{identifier}\n\n"
            f"{Icons.ANALYTICS} Выбери количество похожих каналов для анализа:"
        )


def format_loading_message(identifier: str, is_id_based: bool = False) -> str:
    """
    Форматирует сообщение о загрузке в стиле ОРБИТА.
    
    Args:
        identifier: username или ID канала
        is_id_based: True если это ID-based канал
    
    Returns:
        Отформатированный текст
    """
    if is_id_based:
        return f"{Icons.SEARCH} {Icons.LOADING} Проверяю канал (ID: <code>{identifier}</code>)..."
    else:
        return f"{Icons.SEARCH} {Icons.LOADING} Проверяю канал @{identifier}..."


def format_error_message(error: str) -> str:
    """
    Форматирует сообщение об ошибке в стиле ОРБИТА.
    
    Args:
        error: Текст ошибки
    
    Returns:
        Отформатированный текст
    """
    return f"{Icons.ERROR} <b>Ошибка:</b> {error}"


def format_success_message(message: str) -> str:
    """
    Форматирует сообщение об успехе в стиле ОРБИТА.
    
    Args:
        message: Текст сообщения
    
    Returns:
        Отформатированный текст
    """
    return f"{Icons.SUCCESS} {message}"


def format_proxy_channel_message(linked_channels: List[Tuple[str, int]], top_n: int) -> str:
    """
    Форматирует сообщение о канале-прокладке в стиле ОРБИТА.
    
    Args:
        linked_channels: Список кортежей (username, count)
        top_n: Количество каналов для анализа
    
    Returns:
        Отформатированный текст
    """
    channels_list = "\n".join([
        f"{Icons.STAR} @{username} (упоминается {count} раз)"
        for username, count in linked_channels[:5]
    ])
    
    return (
        f"{Icons.WARNING} <b>Обнаружен канал-прокладка</b>\n\n"
        f"{Icons.SATELLITE} Этот канал в основном содержит ссылки на другие каналы:\n\n"
        f"{channels_list}\n\n"
        f"{Icons.ANALYTICS} Выбери канал для анализа или принудительно проанализируй текущий:"
    )


# ============================================================================
# РАЗДЕЛИТЕЛИ (орбитальные кольца)
# ============================================================================

def get_separator(length: int = 20) -> str:
    """
    Возвращает разделитель в стиле орбитальных колец.
    
    Args:
        length: Длина разделителя
    
    Returns:
        Строка-разделитель
    """
    return "━" * length


def format_card_header(title: str) -> str:
    """
    Форматирует заголовок карточки в стиле ОРБИТА.
    
    Args:
        title: Заголовок
    
    Returns:
        Отформатированный текст
    """
    separator = get_separator(20)
    return f"{separator}\n{Icons.ORBIT} {title}\n{separator}"
