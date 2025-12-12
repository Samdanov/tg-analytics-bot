#!/usr/bin/env python3
"""
Миграция: добавление колонки tone в таблицу keywords_cache
Использует те же настройки подключения, что и приложение
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db.database import engine
from app.core.config import config
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def migrate_add_tone_column():
    """Добавляет колонку tone в таблицу keywords_cache"""
    logger.info("Начинаю миграцию: добавление колонки tone в keywords_cache...")
    logger.info(f"Подключение к БД: {config.postgres_dsn.split('@')[-1] if '@' in config.postgres_dsn else 'скрыто'}")
    
    try:
        async with engine.begin() as conn:
            # Проверяем, существует ли колонка
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'keywords_cache' 
                AND column_name = 'tone'
            """)
            result = await conn.execute(check_query)
            existing = result.fetchone()
            
            if existing:
                logger.info("✅ Колонка tone уже существует в таблице keywords_cache")
                return True
            
            # Пытаемся добавить колонку
            try:
                alter_query = text("ALTER TABLE keywords_cache ADD COLUMN tone TEXT")
                await conn.execute(alter_query)
                logger.info("✅ Колонка tone успешно добавлена в таблицу keywords_cache")
            except Exception as perm_error:
                if "InsufficientPrivilegeError" in str(type(perm_error)) or "must be owner" in str(perm_error):
                    logger.error("❌ Недостаточно прав для изменения таблицы")
                    logger.error("")
                    logger.error("=" * 60)
                    logger.error("РЕШЕНИЕ: Выполните миграцию от имени суперпользователя PostgreSQL:")
                    logger.error("")
                    logger.error("  sudo -u postgres psql -d tg_analytics -c \\")
                    logger.error("    \"ALTER TABLE keywords_cache ADD COLUMN IF NOT EXISTS tone TEXT;\"")
                    logger.error("")
                    logger.error("Или используйте файл миграции:")
                    logger.error("  sudo -u postgres psql -d tg_analytics -f app/db/migrations/add_tone_column.sql")
                    logger.error("=" * 60)
                    logger.error("")
                    return False
                else:
                    raise
            
            # Проверяем результат
            result = await conn.execute(check_query)
            if result.fetchone():
                logger.info("✅ Проверка: колонка tone присутствует в таблице")
                return True
            else:
                logger.error("❌ Ошибка: колонка tone не найдена после добавления")
                return False
                
    except Exception as e:
        logger.error(f"❌ Ошибка при выполнении миграции: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Главная функция"""
    success = await migrate_add_tone_column()
    if success:
        logger.info("🎉 Миграция завершена успешно!")
        sys.exit(0)
    else:
        logger.error("💥 Миграция завершилась с ошибкой")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
