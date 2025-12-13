"""
Примеры использования Repositories

Демонстрирует как использовать новую архитектуру репозиториев.
"""

import asyncio
from datetime import datetime

from app.db.repositories import (
    ChannelRepository,
    PostRepository,
    KeywordsCacheRepository,
    AnalyticsResultsRepository,
    RepositoryFacade,
    get_repository_facade,
)
from app.schemas import ChannelCreateSchema, AnalysisResultSchema
from app.domain import ChannelIdentifier


# ============================================================================
# ПРИМЕР 1: Работа с ChannelRepository
# ============================================================================

async def example_channel_repository():
    """Примеры работы с ChannelRepository."""
    
    print("=" * 80)
    print("ПРИМЕР 1: ChannelRepository")
    print("=" * 80)
    
    repo = ChannelRepository()
    
    # 1.1 UPSERT канала
    print("\n1.1 UPSERT канала:")
    
    channel_data = ChannelCreateSchema(
        identifier="@example_channel",
        title="Example Channel",
        description="Test channel for examples",
        subscribers=1000
    )
    
    try:
        channel = await repo.upsert(channel_data)
        print(f"✓ Channel upserted: ID={channel.id}, username={channel.username}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # 1.2 Получение по username
    print("\n1.2 Получение по username:")
    
    channel = await repo.get_by_username("example_channel")
    if channel:
        print(f"✓ Found: {channel.title} ({channel.subscribers} subscribers)")
    else:
        print("✗ Not found")
    
    # 1.3 Получение через ChannelIdentifier (domain integration)
    print("\n1.3 Получение через domain.ChannelIdentifier:")
    
    identifier = ChannelIdentifier.from_raw("@example_channel")
    channel = await repo.get_by_identifier(identifier)
    if channel:
        print(f"✓ Found via domain object: {channel.title}")
    
    # 1.4 Преобразование в schema
    print("\n1.4 Преобразование в Pydantic schema:")
    
    if channel:
        schema = repo.to_schema(channel)
        print(f"✓ Schema: {schema.display_name} (analyzed: {schema.is_analyzed})")
    
    # 1.5 Поиск по названию
    print("\n1.5 Поиск по названию:")
    
    results = await repo.search_by_title("example")
    print(f"✓ Found {len(results)} channels matching 'example'")


# ============================================================================
# ПРИМЕР 2: Работа с PostRepository
# ============================================================================

async def example_post_repository():
    """Примеры работы с PostRepository."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 2: PostRepository")
    print("=" * 80)
    
    # Получаем канал для работы
    channel_repo = ChannelRepository()
    channel = await channel_repo.get_by_username("example_channel")
    
    if not channel:
        print("✗ Channel not found, skipping post examples")
        return
    
    post_repo = PostRepository()
    
    # 2.1 Замена постов
    print("\n2.1 Замена постов канала:")
    
    posts_data = [
        {
            "date": datetime.utcnow(),
            "views": 100,
            "forwards": 5,
            "text": "Test post 1"
        },
        {
            "date": datetime.utcnow(),
            "views": 200,
            "forwards": 10,
            "text": "Test post 2"
        },
    ]
    
    count = await post_repo.replace_posts(channel.id, posts_data)
    print(f"✓ Replaced posts: {count}")
    
    # 2.2 Получение постов канала
    print("\n2.2 Получение постов:")
    
    posts = await post_repo.get_by_channel(channel.id, limit=10)
    print(f"✓ Found {len(posts)} posts")
    
    # 2.3 Статистика по постам
    print("\n2.3 Статистика:")
    
    stats = await post_repo.get_posts_stats(channel.id)
    print(f"✓ Total posts: {stats['total_posts']}")
    print(f"✓ Avg views: {stats['avg_views']:.1f}")
    print(f"✓ Avg forwards: {stats['avg_forwards']:.1f}")


# ============================================================================
# ПРИМЕР 3: Работа с KeywordsCacheRepository
# ============================================================================

async def example_keywords_repository():
    """Примеры работы с KeywordsCacheRepository."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 3: KeywordsCacheRepository")
    print("=" * 80)
    
    # Получаем канал
    channel_repo = ChannelRepository()
    channel = await channel_repo.get_by_username("example_channel")
    
    if not channel:
        print("✗ Channel not found, skipping keywords examples")
        return
    
    keywords_repo = KeywordsCacheRepository()
    
    # 3.1 Сохранение результатов анализа
    print("\n3.1 Сохранение результатов LLM:")
    
    analysis = AnalysisResultSchema(
        audience="Test audience",
        keywords=["test", "example", "demo"],
        tone="Professional",
        source="llm",
        confidence=0.9
    )
    
    cache = await keywords_repo.upsert_analysis(channel.id, analysis)
    print(f"✓ Analysis saved for channel_id={channel.id}")
    
    # 3.2 Получение keywords
    print("\n3.2 Получение keywords:")
    
    keywords = await keywords_repo.get_keywords_list(channel.id)
    print(f"✓ Keywords: {keywords}")
    
    # 3.3 Преобразование в schema
    print("\n3.3 Преобразование в schema:")
    
    cache = await keywords_repo.get_by_channel_id(channel.id)
    if cache:
        schema = keywords_repo.to_schema(cache)
        print(f"✓ Audience: {schema.audience}")
        print(f"✓ Keywords count: {len(schema.keywords)}")


# ============================================================================
# ПРИМЕР 4: Работа с AnalyticsResultsRepository
# ============================================================================

async def example_analytics_repository():
    """Примеры работы с AnalyticsResultsRepository."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 4: AnalyticsResultsRepository")
    print("=" * 80)
    
    # Получаем канал
    channel_repo = ChannelRepository()
    channel = await channel_repo.get_by_username("example_channel")
    
    if not channel:
        print("✗ Channel not found, skipping analytics examples")
        return
    
    analytics_repo = AnalyticsResultsRepository()
    
    # 4.1 Сохранение результатов similarity
    print("\n4.1 Сохранение результатов similarity:")
    
    similar_channels = [
        (2, 0.95),  # (channel_id, score)
        (3, 0.85),
        (4, 0.75),
    ]
    
    result = await analytics_repo.upsert_results(channel.id, similar_channels)
    print(f"✓ Similarity results saved: {len(similar_channels)} channels")
    
    # 4.2 Получение топ-N похожих
    print("\n4.2 Получение топ-3 похожих:")
    
    top_similar = await analytics_repo.get_top_similar(channel.id, top_n=3)
    for channel_id, score in top_similar:
        print(f"  Channel ID={channel_id}, Score={score:.2f}")
    
    # 4.3 Проверка наличия результатов
    print("\n4.3 Проверка результатов:")
    
    has_results = await analytics_repo.has_results(channel.id)
    print(f"✓ Has results: {has_results}")


# ============================================================================
# ПРИМЕР 5: Работа с RepositoryFacade
# ============================================================================

async def example_repository_facade():
    """Примеры работы с RepositoryFacade."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 5: RepositoryFacade (Unified Access)")
    print("=" * 80)
    
    # 5.1 Создание facade
    print("\n5.1 Создание facade:")
    
    facade = RepositoryFacade()
    print("✓ Facade created")
    
    # 5.2 Доступ к репозиториям через facade
    print("\n5.2 Доступ через facade:")
    
    channel = await facade.channels.get_by_username("example_channel")
    if channel:
        print(f"✓ Channel: {channel.title}")
        
        posts = await facade.posts.get_by_channel(channel.id, limit=5)
        print(f"✓ Posts: {len(posts)}")
        
        keywords = await facade.keywords.get_keywords_list(channel.id)
        print(f"✓ Keywords: {len(keywords)}")
        
        similar = await facade.analytics.get_top_similar(channel.id, top_n=3)
        print(f"✓ Similar channels: {len(similar)}")
    
    # 5.3 High-level метод (полная информация)
    print("\n5.3 Получение полной информации:")
    
    full_info = await facade.get_channel_full_info("example_channel")
    if full_info:
        print(f"✓ Channel: {full_info['channel'].title}")
        print(f"✓ Posts: {len(full_info['posts'])}")
        print(f"✓ Posts stats: {full_info['posts_stats']}")
        print(f"✓ Keywords: {len(full_info['keywords'])}")
        print(f"✓ Similar: {len(full_info['similar_channels'])}")
    
    # 5.4 Общая статистика
    print("\n5.4 Общая статистика БД:")
    
    stats = await facade.get_statistics()
    print(f"✓ Total channels: {stats['total_channels']}")
    print(f"✓ Channels analyzed: {stats['channels_analyzed']}")
    print(f"✓ Total posts: {stats['total_posts']}")
    print(f"✓ Avg posts per channel: {stats['avg_posts_per_channel']:.1f}")


# ============================================================================
# ПРИМЕР 6: Использование Singleton Facade
# ============================================================================

async def example_singleton_facade():
    """Примеры использования singleton facade."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 6: Singleton Facade")
    print("=" * 80)
    
    # 6.1 Получение singleton instance
    print("\n6.1 Получение singleton:")
    
    repo = get_repository_facade()
    print("✓ Singleton facade obtained")
    
    # 6.2 Использование в разных частях кода
    print("\n6.2 Переиспользование singleton:")
    
    repo2 = get_repository_facade()
    print(f"✓ Same instance: {repo is repo2}")
    
    # 6.3 Работа через singleton
    print("\n6.3 Работа через singleton:")
    
    channels_count = await repo.channels.count()
    print(f"✓ Total channels: {channels_count}")


# ============================================================================
# ЗАПУСК ПРИМЕРОВ
# ============================================================================

async def main():
    """Запуск всех примеров."""
    
    print("\n" + "🚀 " * 20)
    print("ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ REPOSITORIES")
    print("🚀 " * 20 + "\n")
    
    try:
        await example_channel_repository()
        await example_post_repository()
        await example_keywords_repository()
        await example_analytics_repository()
        await example_repository_facade()
        await example_singleton_facade()
        
        print("\n" + "=" * 80)
        print("✓ Все примеры выполнены успешно!")
        print("=" * 80)
    
    except Exception as e:
        print(f"\n✗ Ошибка при выполнении примеров: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

