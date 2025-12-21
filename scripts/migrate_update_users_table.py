#!/usr/bin/env python3
"""
Миграция: Обновление таблицы users до новой структуры.

Обновляет существующую таблицу users, добавляя недостающие колонки.
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from app.db.database import async_session_maker
from app.core.logging import get_logger

logger = get_logger(__name__)


async def migrate():
    """Обновляет структуру таблицы users."""
    
    logger.info("=" * 60)
    logger.info("МИГРАЦИЯ: Обновление таблицы users")
    logger.info("=" * 60)
    
    async with async_session_maker() as session:
        try:
            # Проверяем текущую структуру
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users'
            """))
            existing_cols = {row[0] for row in result.all()}
            
            logger.info(f"Существующие колонки: {sorted(existing_cols)}")
            
            # Если есть telegram_id, переименовываем в user_id
            if 'telegram_id' in existing_cols and 'user_id' not in existing_cols:
                logger.info("Переименование telegram_id → user_id...")
                try:
                    await session.execute(text("ALTER TABLE users RENAME COLUMN telegram_id TO user_id"))
                    await session.commit()
                    logger.info("✅ Колонка переименована")
                    existing_cols.remove('telegram_id')
                    existing_cols.add('user_id')
                except Exception as e:
                    await session.rollback()
                    logger.warning(f"⚠️  Не удалось переименовать: {e}")
            
            # Добавляем недостающие колонки
            new_columns = [
                ("username", "TEXT"),
                ("first_name", "TEXT"),
                ("subscription_type", "TEXT DEFAULT 'free'"),
                ("subscription_expires_at", "TIMESTAMP"),
                ("queries_used", "INTEGER DEFAULT 0"),
                ("queries_limit", "INTEGER DEFAULT 10"),
                ("queries_reset_at", "TIMESTAMP"),
                ("is_active", "BOOLEAN DEFAULT TRUE"),
                ("is_banned", "BOOLEAN DEFAULT FALSE"),
                ("last_activity_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                ("notes", "TEXT"),
            ]
            
            for col_name, col_def in new_columns:
                if col_name not in existing_cols:
                    try:
                        logger.info(f"Добавление колонки {col_name}...")
                        await session.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
                        await session.commit()
                        logger.info(f"✅ Колонка {col_name} добавлена")
                    except Exception as e:
                        await session.rollback()
                        logger.warning(f"⚠️  Не удалось добавить {col_name}: {e}")
            
            # Обновляем существующие записи
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            
            if user_count > 0:
                logger.info(f"Обновление {user_count} существующих записей...")
                try:
                    await session.execute(text("""
                        UPDATE users 
                        SET 
                            subscription_type = COALESCE(subscription_type, 'free'),
                            queries_limit = COALESCE(queries_limit, 10),
                            queries_used = COALESCE(queries_used, 0),
                            is_active = COALESCE(is_active, TRUE),
                            is_banned = COALESCE(is_banned, FALSE),
                            last_activity_at = COALESCE(last_activity_at, created_at)
                        WHERE subscription_type IS NULL OR queries_limit IS NULL
                    """))
                    await session.commit()
                    logger.info("✅ Записи обновлены")
                except Exception as e:
                    await session.rollback()
                    logger.warning(f"⚠️  Не удалось обновить записи: {e}")
            
            logger.info("✅ Миграция завершена успешно!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка миграции: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("МИГРАЦИЯ: Обновление таблицы users")
    print("=" * 60 + "\n")
    
    asyncio.run(migrate())
    
    print("\n" + "=" * 60)
    print("Готово! Теперь перезапустите бота.")
    print("=" * 60 + "\n")
