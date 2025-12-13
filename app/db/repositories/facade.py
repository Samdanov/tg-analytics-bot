"""
Repository Facade

Унифицированный интерфейс для доступа ко всем репозиториям.
Паттерн Facade упрощает работу с несколькими репозиториями.
"""

from typing import Optional

from .channel_repository import ChannelRepository
from .post_repository import PostRepository
from .keywords_cache_repository import KeywordsCacheRepository
from .analytics_results_repository import AnalyticsResultsRepository


class RepositoryFacade:
    """
    Facade для доступа ко всем репозиториям.
    
    Предоставляет единую точку входа для работы с БД.
    Упрощает dependency injection и тестирование.
    
    Usage:
        repo = RepositoryFacade()
        
        # Работа с каналами
        channel = await repo.channels.get_by_username("technews")
        
        # Работа с постами
        posts = await repo.posts.get_by_channel(channel.id)
        
        # Работа с keywords
        keywords = await repo.keywords.get_keywords_list(channel.id)
        
        # Работа с similarity
        similar = await repo.analytics.get_top_similar(channel.id, top_n=10)
    """
    
    def __init__(
        self,
        channels: Optional[ChannelRepository] = None,
        posts: Optional[PostRepository] = None,
        keywords: Optional[KeywordsCacheRepository] = None,
        analytics: Optional[AnalyticsResultsRepository] = None
    ):
        """
        Args:
            channels: ChannelRepository (создается автоматически если None)
            posts: PostRepository (создается автоматически если None)
            keywords: KeywordsCacheRepository (создается автоматически если None)
            analytics: AnalyticsResultsRepository (создается автоматически если None)
        """
        self._channels = channels
        self._posts = posts
        self._keywords = keywords
        self._analytics = analytics
    
    @property
    def channels(self) -> ChannelRepository:
        """Репозиторий каналов."""
        if self._channels is None:
            self._channels = ChannelRepository()
        return self._channels
    
    @property
    def posts(self) -> PostRepository:
        """Репозиторий постов."""
        if self._posts is None:
            self._posts = PostRepository()
        return self._posts
    
    @property
    def keywords(self) -> KeywordsCacheRepository:
        """Репозиторий keywords cache."""
        if self._keywords is None:
            self._keywords = KeywordsCacheRepository()
        return self._keywords
    
    @property
    def analytics(self) -> AnalyticsResultsRepository:
        """Репозиторий analytics results."""
        if self._analytics is None:
            self._analytics = AnalyticsResultsRepository()
        return self._analytics
    
    # Convenience методы (high-level операции)
    
    async def get_channel_full_info(self, username: str) -> Optional[dict]:
        """
        Получить полную информацию о канале (канал + посты + keywords + similar).
        
        Args:
            username: Username канала
        
        Returns:
            Словарь с полной информацией или None
        """
        channel = await self.channels.get_by_username(username)
        if not channel:
            return None
        
        # Получаем связанные данные
        posts = await self.posts.get_by_channel(channel.id, limit=50)
        keywords = await self.keywords.get_keywords_list(channel.id)
        similar = await self.analytics.get_similar_channels(channel.id, limit=10)
        posts_stats = await self.posts.get_posts_stats(channel.id)
        
        return {
            "channel": self.channels.to_schema(channel),
            "posts": posts,
            "posts_stats": posts_stats,
            "keywords": keywords,
            "similar_channels": similar,
        }
    
    async def delete_channel_full(self, channel_id: int) -> bool:
        """
        Удалить канал и все связанные данные.
        
        Args:
            channel_id: ID канала
        
        Returns:
            True если удалено
        """
        # Каскадное удаление работает на уровне БД,
        # но явно удаляем для логирования
        
        # Удаляем посты
        await self.posts.delete_by_channel(channel_id)
        
        # Удаляем keywords cache (ON DELETE CASCADE)
        # Удаляем analytics results (ON DELETE CASCADE)
        
        # Удаляем сам канал
        return await self.channels.delete(channel_id)
    
    async def get_statistics(self) -> dict:
        """
        Получить общую статистику по БД.
        
        Returns:
            Словарь со статистикой
        """
        total_channels = await self.channels.count()
        channels_with_keywords = len(await self.channels.get_with_keywords())
        total_posts = await self.posts.count()
        
        return {
            "total_channels": total_channels,
            "channels_with_keywords": channels_with_keywords,
            "channels_analyzed": channels_with_keywords,
            "total_posts": total_posts,
            "avg_posts_per_channel": total_posts / total_channels if total_channels > 0 else 0
        }


# Singleton instance для удобного использования
_facade_instance: Optional[RepositoryFacade] = None


def get_repository_facade() -> RepositoryFacade:
    """
    Получить singleton instance RepositoryFacade.
    
    Returns:
        RepositoryFacade
    
    Usage:
        from app.db.repositories import get_repository_facade
        
        repo = get_repository_facade()
        channel = await repo.channels.get_by_username("technews")
    """
    global _facade_instance
    if _facade_instance is None:
        _facade_instance = RepositoryFacade()
    return _facade_instance

