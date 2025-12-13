"""
Примеры использования Domain Layer

Этот файл демонстрирует, как использовать domain layer в коде.
После тестирования эти паттерны будут интегрированы в основной код.
"""

from typing import List, Dict, Any

from app.domain import (
    ChannelIdentifier,
    ChannelEntity,
    AnalysisResult,
    ProxyChannelDetector,
    InvalidChannelIdentifierError,
    ProxyChannelDetectedError,
)


# ============================================================================
# ПРИМЕР 1: Работа с ChannelIdentifier
# ============================================================================

def example_channel_identifier():
    """
    Пример использования ChannelIdentifier вместо ручной обработки username/ID.
    """
    
    # Создание из обычного username
    channel1 = ChannelIdentifier.from_raw("@technews")
    print(f"Username канал: {channel1.to_display_format()}")  # @technews
    print(f"Для БД: {channel1.to_db_format()}")  # technews
    print(f"Для файла: {channel1.to_file_name()}")  # technews
    
    # Создание из ID
    channel2 = ChannelIdentifier.from_raw("-1002508742544")
    print(f"\nID-based канал: {channel2.to_display_format()}")  # ID: -1002508742544
    print(f"Для БД: {channel2.to_db_format()}")  # id:-1002508742544
    print(f"Для файла: {channel2.to_file_name()}")  # id_-1002508742544
    
    # Создание из Telegram ID напрямую
    channel3 = ChannelIdentifier.from_telegram_id(-1002508742544, title="TERMINAL")
    print(f"\nИз Telegram ID: {channel3.to_display_format()}")
    
    # Валидация
    try:
        invalid = ChannelIdentifier.from_raw("@ab")  # Слишком короткий
    except InvalidChannelIdentifierError as e:
        print(f"\nОшибка валидации: {e}")


# ============================================================================
# ПРИМЕР 2: Работа с ChannelEntity
# ============================================================================

def example_channel_entity():
    """
    Пример использования ChannelEntity - доменной модели канала.
    """
    
    # Создание entity
    identifier = ChannelIdentifier.from_raw("@technews")
    channel = ChannelEntity(
        identifier=identifier,
        title="Tech News",
        description="Latest tech news and updates",
        subscribers=10000,
        keywords=["tech", "news", "innovation"]
    )
    
    print(f"Канал: {channel}")
    print(f"Приватный: {channel.is_private}")
    print(f"Проанализирован: {channel.is_analyzed}")
    
    # Обновление метаданных
    channel.update_metadata(subscribers=15000)
    print(f"\nПосле обновления: {channel.subscribers} подписчиков")
    
    # Обновление keywords
    channel.update_keywords(["technology", "gadgets", "AI"])
    print(f"Новые keywords: {channel.keywords}")
    
    # Сериализация
    channel_dict = channel.to_dict()
    print(f"\nСериализованный канал: {channel_dict}")
    
    # Десериализация
    restored_channel = ChannelEntity.from_dict(channel_dict)
    print(f"Восстановленный канал: {restored_channel}")


# ============================================================================
# ПРИМЕР 3: Определение прокладки с ProxyChannelDetector
# ============================================================================

def example_proxy_detection():
    """
    Пример использования ProxyChannelDetector.
    Заменяет логику из workflow.py.
    """
    
    # Симуляция постов канала-прокладки
    proxy_posts = [
        {"text": "Подписывайтесь на @channel1 и @channel2"},
        {"text": "Интересный контент: t.me/channel3"},
        {"text": "Еще один канал: @channel1"},
        {"text": "@channel2 - лучший!"},
        {"text": "Топ канал: @channel4"},
    ]
    
    # Создаем детектор
    detector = ProxyChannelDetector()
    
    # Проверяем канал
    result = detector.detect(proxy_posts, exclude_username="current_channel")
    
    print(f"Это прокладка: {result.is_proxy}")
    print(f"Средняя длина текста: {result.avg_text_length:.1f}")
    print(f"Доля постов со ссылками: {result.link_posts_ratio:.1%}")
    print(f"\nУпоминаемые каналы:")
    for username, count in result.linked_channels:
        print(f"  @{username}: {count} упоминаний")
    
    if result.is_proxy:
        print(f"\nПричина: {result.reason}")


# ============================================================================
# ПРИМЕР 4: Работа с AnalysisResult
# ============================================================================

def example_analysis_result():
    """
    Пример использования AnalysisResult.
    """
    
    # Успешный анализ от LLM
    analysis1 = AnalysisResult(
        audience="IT-специалисты 25-40 лет",
        keywords=["python", "django", "backend"],
        tone="Профессиональный",
        source="llm",
        confidence=0.9
    )
    
    print(f"Анализ 1: {analysis1}")
    print(f"Из LLM: {analysis1.is_from_llm}")
    print(f"Уверенность: {analysis1.confidence}")
    
    # Fallback анализ (LLM не сработал)
    analysis2 = AnalysisResult.from_fallback(
        keywords=["tech", "news"],
        reason="Ошибка парсинга JSON от LLM"
    )
    
    print(f"\nАнализ 2 (fallback): {analysis2}")
    print(f"Это fallback: {analysis2.is_fallback}")
    
    # Пустой результат
    analysis3 = AnalysisResult.empty(reason="Нет постов для анализа")
    
    print(f"\nАнализ 3 (пустой): {analysis3}")
    print(f"Пустой: {analysis3.is_empty}")


# ============================================================================
# ПРИМЕР 5: Интеграция в существующий workflow
# ============================================================================

def example_integration_with_old_code():
    """
    Пример постепенной интеграции domain layer в существующий код.
    Показывает, как использовать новый код вместе со старым.
    """
    
    # СТАРЫЙ КОД (было):
    # username = message.forward_from_chat.username
    # if not username:
    #     channel_id = message.forward_from_chat.id
    #     is_id_based = True
    # else:
    #     is_id_based = False
    
    # НОВЫЙ КОД (стало):
    # Получаем данные из Telegram message
    raw_username = "@technews"  # Или ID: "-1002508742544"
    
    try:
        identifier = ChannelIdentifier.from_raw(raw_username)
        
        # Используем в callback buttons
        if identifier.is_id_based:
            callback_data = f"analyze:id:{identifier.normalized_value.replace('id:', '')}:10"
        else:
            callback_data = f"analyze:{identifier.normalized_value}:10"
        
        print(f"Callback data: {callback_data}")
        
        # Используем для отображения
        display_name = identifier.to_display_format()
        print(f"Display: {display_name}")
        
        # Используем для сохранения в БД
        db_value = identifier.to_db_format()
        print(f"DB value: {db_value}")
        
    except InvalidChannelIdentifierError as e:
        print(f"Ошибка: {e}")


# ============================================================================
# ЗАПУСК ПРИМЕРОВ
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("ПРИМЕР 1: ChannelIdentifier")
    print("=" * 80)
    example_channel_identifier()
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 2: ChannelEntity")
    print("=" * 80)
    example_channel_entity()
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 3: ProxyChannelDetector")
    print("=" * 80)
    example_proxy_detection()
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 4: AnalysisResult")
    print("=" * 80)
    example_analysis_result()
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 5: Интеграция со старым кодом")
    print("=" * 80)
    example_integration_with_old_code()

