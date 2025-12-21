#!/usr/bin/env python3
"""
Миграция: Создание таблицы users для подписок и лимитов.

Запуск:
    python3 scripts/migrate_add_users_table.py
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from app.db.database import async_session_maker, engine
from app.core.logging import get_logger

logger = get_logger(__name__)


async def migrate():
    """Создает таблицу users."""
    
    logger.info("=" * 60)
    logger.info("МИГРАЦИЯ: Создание таблицы users")
    logger.info("=" * 60)
    
    # SQL для создания таблицы
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        
        subscription_type TEXT DEFAULT 'free',
        subscription_expires_at TIMESTAMP,
        
        queries_used INTEGER DEFAULT 0,
        queries_limit INTEGER DEFAULT 10,
        queries_reset_at TIMESTAMP,
        
        is_active BOOLEAN DEFAULT TRUE,
        is_banned BOOLEAN DEFAULT FALSE,
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        notes TEXT
    );
    """
    
    # SQL для создания индексов (отдельно, т.к. asyncpg не поддерживает множественные команды)
    create_index1_sql = "CREATE INDEX IF NOT EXISTS idx_users_subscription_type ON users(subscription_type);"
    create_index2_sql = "CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);"
    
    async with async_session_maker() as session:
        try:
            # Проверяем, существует ли таблица
            check_table_sql = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'users'
                );
            """
            result = await session.execute(text(check_table_sql))
            table_exists = result.scalar()
            
            if table_exists:
                logger.info("⚠️  Таблица users уже существует, пропускаем создание...")
            else:
                # Создаем таблицу
                logger.info("Создание таблицы users...")
                await session.execute(text(create_table_sql))
                await session.commit()
                logger.info("✅ Таблица users создана")
            
            # Пытаемся создать индексы (может не получиться, если нет прав)
            logger.info("Создание индексов...")
            try:
                await session.execute(text(create_index1_sql))
                await session.commit()
                logger.info("✅ Индекс idx_users_subscription_type создан")
            except Exception as e:
                await session.rollback()
                logger.warning(f"⚠️  Не удалось создать индекс idx_users_subscription_type: {e}")
            
            try:
                await session.execute(text(create_index2_sql))
                await session.commit()
                logger.info("✅ Индекс idx_users_is_active создан")
            except Exception as e:
                await session.rollback()
                logger.warning(f"⚠️  Не удалось создать индекс idx_users_is_active: {e}")
            
            logger.info("✅ Миграция завершена!")
            logger.info("")
            logger.info("Структура таблицы users:")
            logger.info("  - user_id (PK) - Telegram user ID")
            logger.info("  - username - Telegram username")
            logger.info("  - subscription_type - 'free', 'premium', 'admin'")
            logger.info("  - queries_used - использовано запросов")
            logger.info("  - queries_limit - лимит запросов (10 для free)")
            logger.info("")
            logger.info("По умолчанию все новые пользователи:")
            logger.info("  - subscription_type = 'free'")
            logger.info("  - queries_limit = 10")
            logger.info("  - queries_used = 0")
            
        except Exception as e:
            logger.error(f"❌ Ошибка миграции: {e}")
            await session.rollback()
            raise
    
    logger.info("=" * 60)


async def check_table():
    """Проверяет, что таблица создана."""
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT COUNT(*) as count FROM information_schema.tables 
                WHERE table_name = 'users'
            """))
            count = result.scalar()
            
            if count > 0:
                logger.info("✅ Таблица users существует")
                
                # Проверяем количество записей
                result = await session.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                logger.info(f"   Записей в таблице: {user_count}")
            else:
                logger.warning("⚠️  Таблица users не найдена")
    except Exception as e:
        logger.warning(f"⚠️  Не удалось проверить таблицу: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("МИГРАЦИЯ: Добавление таблицы users")
    print("=" * 60 + "\n")
    
    asyncio.run(migrate())
    asyncio.run(check_table())
    
    print("\n" + "=" * 60)
    print("Следующие шаги:")
    print("=" * 60)
    print("1. Перезапустите бота")
    print("2. Используйте /admin_user команды для управления подписками")
    print("3. Протестируйте лимиты с бесплатным аккаунтом")
    print("=" * 60 + "\n")
