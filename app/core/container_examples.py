"""
Примеры использования DI Container

Демонстрирует как использовать Dependency Injection в проекте.
"""

from app.core.container import Container, get_container, reset_container


# ============================================================================
# ПРИМЕР 1: Базовое использование
# ============================================================================

def example_basic_usage():
    """Базовое использование контейнера."""
    
    print("=" * 80)
    print("ПРИМЕР 1: Базовое использование DI Container")
    print("=" * 80)
    
    # Получаем глобальный контейнер
    container = get_container()
    
    # 1.1 Получение конфигурации
    print("\n1.1 Конфигурация:")
    config = container.config
    print(f"✓ Bot token: {config.bot_token[:20]}...")
    print(f"✓ Log level: {config.log_level}")
    
    # 1.2 Получение logger
    print("\n1.2 Logger:")
    logger = container.logger(__name__)
    logger.info("This is a test log message")
    print(f"✓ Logger created: {logger.name}")
    
    # 1.3 Получение repository
    print("\n1.3 Repository:")
    repo = container.repository
    print(f"✓ Repository: {type(repo).__name__}")
    
    # 1.4 Получение use cases
    print("\n1.4 Use Cases:")
    message_parser = container.message_parser
    analyze_uc = container.analyze_channel_uc
    print(f"✓ Message Parser: {type(message_parser).__name__}")
    print(f"✓ Analyze UC: {type(analyze_uc).__name__}")


# ============================================================================
# ПРИМЕР 2: Singleton vs Factory
# ============================================================================

def example_singleton_vs_factory():
    """Демонстрация разницы между singleton и factory."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 2: Singleton vs Factory")
    print("=" * 80)
    
    container = get_container()
    
    # 2.1 Singleton - всегда один экземпляр
    print("\n2.1 Singleton (repository):")
    repo1 = container.repository
    repo2 = container.repository
    print(f"✓ Same instance: {repo1 is repo2}")
    
    # 2.2 Factory - каждый раз новый экземпляр
    print("\n2.2 Factory (logger):")
    logger1 = container.logger('module1')
    logger2 = container.logger('module2')
    print(f"✓ Different instances: {logger1 is not logger2}")
    print(f"✓ Logger1 name: {logger1.name}")
    print(f"✓ Logger2 name: {logger2.name}")


# ============================================================================
# ПРИМЕР 3: Использование в handlers
# ============================================================================

async def example_in_handlers():
    """Пример использования в handlers."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 3: Использование в handlers")
    print("=" * 80)
    
    from aiogram.types import Message
    
    # Псевдо-handler
    async def detect_content_handler(message: Message):
        # Получаем зависимости через DI
        container = get_container()
        message_parser = container.message_parser
        logger = container.logger(__name__)
        
        # Используем
        logger.info("Processing message")
        content_type, info = message_parser.detect_content_type(message)
        
        return content_type, info
    
    print("✓ Handler использует DI для получения зависимостей")
    print("✓ Нет глобальных переменных")
    print("✓ Легко мокировать для тестов")


# ============================================================================
# ПРИМЕР 4: Тестирование с DI
# ============================================================================

def example_testing_with_di():
    """Пример тестирования с использованием DI."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 4: Тестирование с DI")
    print("=" * 80)
    
    # 4.1 Создаем тестовый контейнер
    print("\n4.1 Создание тестового контейнера:")
    
    from app.core.config import Config
    
    # Тестовая конфигурация
    test_config = Config()
    test_config.log_level = "DEBUG"
    
    # Создаем контейнер с тестовой конфигурацией
    test_container = Container(config=test_config)
    
    # Проверяем
    assert test_container.config.log_level == "DEBUG"
    print("✓ Тестовый контейнер создан с кастомной конфигурацией")
    
    # 4.2 Мокирование зависимостей
    print("\n4.2 Мокирование:")
    
    from unittest.mock import Mock
    
    # Создаем мок
    mock_parser = Mock()
    mock_parser.detect_content_type.return_value = ("channel", None)
    
    # Заменяем в контейнере (для тестов можно добавить метод override)
    # test_container._singletons['message_parser'] = mock_parser
    
    print("✓ Зависимости легко мокируются")
    print("✓ Изолированное тестирование")


# ============================================================================
# ПРИМЕР 5: Reset контейнера
# ============================================================================

def example_reset_container():
    """Пример сброса контейнера."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 5: Reset контейнера")
    print("=" * 80)
    
    # Получаем контейнер
    container1 = get_container()
    container1_id = id(container1)
    
    # Сбрасываем
    reset_container()
    
    # Получаем новый
    container2 = get_container()
    container2_id = id(container2)
    
    print(f"✓ Container1 ID: {container1_id}")
    print(f"✓ Container2 ID: {container2_id}")
    print(f"✓ Different containers: {container1_id != container2_id}")
    print("✓ Полезно для тестов (clean state)")


# ============================================================================
# ПРИМЕР 6: Convenience properties
# ============================================================================

def example_convenience_properties():
    """Пример использования convenience properties."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 6: Convenience Properties")
    print("=" * 80)
    
    container = get_container()
    
    print("\n6.1 Доступ через properties:")
    
    # Через properties (удобнее)
    config = container.config
    repo = container.repository
    parser = container.message_parser
    
    print(f"✓ container.config: {type(config).__name__}")
    print(f"✓ container.repository: {type(repo).__name__}")
    print(f"✓ container.message_parser: {type(parser).__name__}")
    
    print("\n6.2 Доступ через get() (универсальный):")
    
    # Через get() (более гибкий)
    config2 = container.get('config')
    logger = container.get('logger', 'my_module')
    
    print(f"✓ container.get('config'): {type(config2).__name__}")
    print(f"✓ container.get('logger', 'my_module'): {logger.name}")


# ============================================================================
# ПРИМЕР 7: Добавление кастомных зависимостей
# ============================================================================

def example_custom_dependencies():
    """Пример добавления кастомных зависимостей."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 7: Кастомные зависимости")
    print("=" * 80)
    
    # Создаем свой контейнер
    container = Container()
    
    # Добавляем кастомную зависимость
    class MyService:
        def do_something(self):
            return "Hello from MyService"
    
    container._register_singleton('my_service', lambda: MyService())
    
    # Используем
    my_service = container.get('my_service')
    result = my_service.do_something()
    
    print(f"✓ Custom service registered")
    print(f"✓ Result: {result}")


# ============================================================================
# ЗАПУСК ПРИМЕРОВ
# ============================================================================

def main():
    """Запуск всех примеров."""
    
    print("\n" + "🚀 " * 20)
    print("ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ DI CONTAINER")
    print("🚀 " * 20 + "\n")
    
    example_basic_usage()
    example_singleton_vs_factory()
    # example_in_handlers()  # Async, пропускаем
    example_testing_with_di()
    example_reset_container()
    example_convenience_properties()
    example_custom_dependencies()
    
    print("\n" + "=" * 80)
    print("✓ Все примеры выполнены успешно!")
    print("=" * 80)


if __name__ == "__main__":
    main()

