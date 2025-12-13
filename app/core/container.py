"""
Dependency Injection Container

Простой, но эффективный DI контейнер для управления зависимостями.
"""

from typing import Optional, Callable, Any, TypeVar, Generic
import logging

from app.core.config import Config
from app.db.repositories import RepositoryFacade
from app.services.use_cases import (
    MessageParserService,
    AnalyzeChannelUseCase,
    AnalyzeWebsiteUseCase,
    DetectProxyChannelUseCase,
)

T = TypeVar('T')


class Container:
    """
    DI Container для управления зависимостями.
    
    Реализует паттерн Service Locator с lazy initialization.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Args:
            config: Конфигурация приложения (по умолчанию создается из .env)
        """
        self._config = config
        self._singletons = {}
        self._factories = {}
        
        # Регистрация провайдеров
        self._register_providers()
    
    def _register_providers(self):
        """Регистрация всех провайдеров."""
        
        # Config (singleton)
        self._register_singleton('config', lambda: self._get_config())
        
        # Logger factory (каждый раз новый logger с разным именем)
        self._register_factory('logger', lambda name='app': self._create_logger(name))
        
        # Repositories (singleton)
        self._register_singleton('repository_facade', lambda: RepositoryFacade())
        
        # Use Cases (singleton, т.к. stateless)
        self._register_singleton('message_parser', lambda: MessageParserService())
        self._register_singleton('detect_proxy_uc', lambda: DetectProxyChannelUseCase())
        self._register_singleton(
            'analyze_channel_uc',
            lambda: AnalyzeChannelUseCase(repo=self.get('repository_facade'))
        )
        self._register_singleton('analyze_website_uc', lambda: AnalyzeWebsiteUseCase())
    
    def _register_singleton(self, name: str, provider: Callable):
        """
        Регистрация singleton (создается один раз).
        
        Args:
            name: Имя зависимости
            provider: Функция-провайдер
        """
        self._factories[name] = ('singleton', provider)
    
    def _register_factory(self, name: str, provider: Callable):
        """
        Регистрация factory (создается каждый раз).
        
        Args:
            name: Имя зависимости
            provider: Функция-провайдер
        """
        self._factories[name] = ('factory', provider)
    
    def get(self, name: str, *args, **kwargs) -> Any:
        """
        Получить зависимость.
        
        Args:
            name: Имя зависимости
            *args, **kwargs: Параметры для factory
        
        Returns:
            Экземпляр зависимости
        
        Raises:
            KeyError: если зависимость не зарегистрирована
        """
        if name not in self._factories:
            raise KeyError(f"Dependency '{name}' not registered in container")
        
        scope, provider = self._factories[name]
        
        if scope == 'singleton':
            # Singleton - создаем один раз
            if name not in self._singletons:
                self._singletons[name] = provider()
            return self._singletons[name]
        
        else:  # factory
            # Factory - создаем каждый раз
            return provider(*args, **kwargs)
    
    def _get_config(self) -> Config:
        """Получить конфигурацию."""
        if self._config is None:
            self._config = Config()
        return self._config
    
    def _create_logger(self, name: str) -> logging.Logger:
        """
        Создать logger.
        
        Args:
            name: Имя logger
        
        Returns:
            Logger instance
        """
        return logging.getLogger(name)
    
    # Convenience methods для популярных зависимостей
    
    @property
    def config(self) -> Config:
        """Получить конфигурацию."""
        return self.get('config')
    
    def logger(self, name: str = 'app') -> logging.Logger:
        """
        Получить logger.
        
        Args:
            name: Имя logger
        
        Returns:
            Logger instance
        """
        return self.get('logger', name)
    
    @property
    def repository(self) -> RepositoryFacade:
        """Получить repository facade."""
        return self.get('repository_facade')
    
    @property
    def message_parser(self) -> MessageParserService:
        """Получить message parser."""
        return self.get('message_parser')
    
    @property
    def detect_proxy_uc(self) -> DetectProxyChannelUseCase:
        """Получить detect proxy use case."""
        return self.get('detect_proxy_uc')
    
    @property
    def analyze_channel_uc(self) -> AnalyzeChannelUseCase:
        """Получить analyze channel use case."""
        return self.get('analyze_channel_uc')
    
    @property
    def analyze_website_uc(self) -> AnalyzeWebsiteUseCase:
        """Получить analyze website use case."""
        return self.get('analyze_website_uc')


# Глобальный контейнер (singleton)
_container: Optional[Container] = None


def get_container() -> Container:
    """
    Получить глобальный DI контейнер.
    
    Returns:
        Container instance
    """
    global _container
    if _container is None:
        _container = Container()
    return _container


def reset_container():
    """
    Сбросить глобальный контейнер.
    
    Полезно для тестов.
    """
    global _container
    _container = None

