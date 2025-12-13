"""
Repositories Layer

Репозитории для работы с БД.
Каждый репозиторий отвечает за свою сущность.
"""

from .base import BaseRepository
from .channel_repository import ChannelRepository
from .post_repository import PostRepository
from .keywords_cache_repository import KeywordsCacheRepository
from .analytics_results_repository import AnalyticsResultsRepository
from .facade import RepositoryFacade, get_repository_facade

__all__ = [
    "BaseRepository",
    "ChannelRepository",
    "PostRepository",
    "KeywordsCacheRepository",
    "AnalyticsResultsRepository",
    "RepositoryFacade",
    "get_repository_facade",
]

