"""
Unit Tests for DI Container

Тесты для Dependency Injection контейнера.
"""

import pytest
from unittest.mock import Mock

from app.core.container import Container, get_container, reset_container


# ============================================================================
# Tests for Container
# ============================================================================

class TestContainer:
    """Тесты для DI Container."""
    
    def test_create_container(self):
        """Создание контейнера."""
        container = Container()
        assert container is not None
    
    def test_get_config(self):
        """Получение конфигурации."""
        container = Container()
        config = container.config
        
        assert config is not None
        assert hasattr(config, 'bot_token')
        assert hasattr(config, 'postgres_dsn')
    
    def test_get_logger(self):
        """Получение logger."""
        container = Container()
        logger = container.logger('test_module')
        
        assert logger.name == 'test_module'
    
    def test_logger_factory(self):
        """Logger как factory (каждый раз новый)."""
        container = Container()
        
        logger1 = container.logger('module1')
        logger2 = container.logger('module2')
        
        assert logger1 is not logger2
        assert logger1.name == 'module1'
        assert logger2.name == 'module2'
    
    def test_repository_singleton(self):
        """Repository как singleton (всегда один экземпляр)."""
        container = Container()
        
        repo1 = container.repository
        repo2 = container.repository
        
        assert repo1 is repo2
    
    def test_use_cases_registered(self):
        """Проверка регистрации use cases."""
        container = Container()
        
        # Все use cases должны быть зарегистрированы
        assert container.message_parser is not None
        assert container.detect_proxy_uc is not None
        assert container.analyze_channel_uc is not None
        assert container.analyze_website_uc is not None
    
    def test_custom_dependency(self):
        """Добавление кастомной зависимости."""
        container = Container()
        
        # Регистрируем
        mock_service = Mock()
        container._register_singleton('test_service', lambda: mock_service)
        
        # Получаем
        service = container.get('test_service')
        assert service is mock_service
    
    def test_unregistered_dependency(self):
        """Получение незарегистрированной зависимости."""
        container = Container()
        
        with pytest.raises(KeyError) as exc_info:
            container.get('non_existent')
        
        assert "not registered" in str(exc_info.value)


# ============================================================================
# Tests for Singleton Pattern
# ============================================================================

class TestSingletonContainer:
    """Тесты для singleton паттерна контейнера."""
    
    def test_get_container_singleton(self):
        """get_container() возвращает singleton."""
        container1 = get_container()
        container2 = get_container()
        
        assert container1 is container2
    
    def test_reset_container(self):
        """Сброс контейнера."""
        # Получаем контейнер
        container1 = get_container()
        container1_id = id(container1)
        
        # Сбрасываем
        reset_container()
        
        # Получаем новый
        container2 = get_container()
        container2_id = id(container2)
        
        assert container1_id != container2_id


# ============================================================================
# Tests for Testing with DI
# ============================================================================

class TestDIForTesting:
    """Тесты для использования DI в тестах."""
    
    def test_mock_repository(self):
        """Мокирование repository."""
        container = Container()
        
        # Создаем мок
        mock_repo = Mock()
        mock_repo.channels.get_by_username.return_value = None
        
        # Заменяем в контейнере
        container._singletons['repository_facade'] = mock_repo
        
        # Проверяем
        repo = container.repository
        assert repo is mock_repo
    
    def test_custom_config_for_tests(self):
        """Тестовая конфигурация."""
        from app.core.config import Config
        
        # Создаем тестовую конфигурацию
        test_config = Config()
        test_config.log_level = "DEBUG"
        
        # Создаем контейнер с ней
        container = Container(config=test_config)
        
        assert container.config.log_level == "DEBUG"


# ============================================================================
# Запуск тестов
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

