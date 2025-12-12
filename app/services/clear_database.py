# app/services/clear_database.py

"""
Скрипт для полной очистки базы данных.
Удаляет все данные из всех таблиц в правильном порядке (с учетом внешних ключей).
"""

import asyncio
from sqlalchemy import delete, text

from app.db.database import async_session_maker
from app.core.logging import setup_logging, get_logger
from app.db.models import (
    AnalyticsResults,
    KeywordsCache,
    Post,
    Channel,
)

logger = get_logger(__name__)


async def clear_all_data():
    """Очищает все данные из БД в правильном порядке."""
    async with async_session_maker() as session:
        try:
            logger.info("Начинаю очистку базы данных...")
            
            # 1. Удаляем analytics_results (зависит от channels)
            result = await session.execute(delete(AnalyticsResults))
            count_analytics = result.rowcount
            logger.info(f"Удалено записей из analytics_results: {count_analytics}")
            
            # 2. Удаляем keywords_cache (зависит от channels)
            result = await session.execute(delete(KeywordsCache))
            count_keywords = result.rowcount
            logger.info(f"Удалено записей из keywords_cache: {count_keywords}")
            
            # 3. Удаляем posts (зависит от channels)
            result = await session.execute(delete(Post))
            count_posts = result.rowcount
            logger.info(f"Удалено записей из posts: {count_posts}")
            
            # 4. Удаляем channels (основная таблица)
            result = await session.execute(delete(Channel))
            count_channels = result.rowcount
            logger.info(f"Удалено записей из channels: {count_channels}")
            
            # 5. Очищаем user_requests и users (если нужно)
            await session.execute(text("DELETE FROM user_requests"))
            await session.execute(text("DELETE FROM users"))
            logger.info("Удалено записей из user_requests и users")
            
            # Сбрасываем последовательности (auto-increment счетчики)
            # Это не критично - если нет прав, просто пропускаем
            sequences = [
                "channels_id_seq",
                "posts_id_seq",
                "analytics_results_id_seq",
                "users_id_seq",
                "user_requests_id_seq"
            ]
            
            reset_count = 0
            for seq_name in sequences:
                try:
                    await session.execute(text(f"ALTER SEQUENCE {seq_name} RESTART WITH 1"))
                    reset_count += 1
                except Exception as e:
                    logger.warning(f"Не удалось сбросить последовательность {seq_name}: {e}")
                    # Продолжаем работу - это не критично
            
            if reset_count > 0:
                logger.info(f"Сброшено последовательностей: {reset_count}/{len(sequences)}")
            else:
                logger.warning("Не удалось сбросить последовательности (недостаточно прав). Это не критично - нумерация продолжится автоматически.")
            
            await session.commit()
            logger.info("✅ База данных успешно очищена!")
            
            return {
                "channels": count_channels,
                "posts": count_posts,
                "keywords_cache": count_keywords,
                "analytics_results": count_analytics,
            }
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка при очистке БД: {e}")
            raise


async def main():
    """Точка входа."""
    setup_logging()
    
    print("⚠️  ВНИМАНИЕ: Это удалит ВСЕ данные из базы данных!")
    print("Таблицы: channels, posts, keywords_cache, analytics_results, users, user_requests")
    response = input("Продолжить? (yes/no): ")
    
    if response.lower() not in ["yes", "y", "да", "д"]:
        print("Отменено.")
        return
    
    try:
        stats = await clear_all_data()
        print("\n✅ Очистка завершена успешно!")
        print(f"Удалено:")
        print(f"  - Каналов: {stats['channels']}")
        print(f"  - Постов: {stats['posts']}")
        print(f"  - Ключевых слов: {stats['keywords_cache']}")
        print(f"  - Результатов аналитики: {stats['analytics_results']}")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
