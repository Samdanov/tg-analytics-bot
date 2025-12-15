#!/usr/bin/env python3
"""
Миграция: добавление колонки category в таблицу channels

Category хранит PRIMARY TOPIC канала (одну из 48 тем из Excel).
Это поле НЕ участвует в TF-IDF similarity, но используется как:
- Фильтр при поиске похожих каналов
- Якорь для category-boosting при ранжировании

Использование:
    python -m app.services.migrate_add_category
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


async def migrate_add_category_column():
    """Добавляет колонку category в таблицу channels"""
    logger.info("Начинаю миграцию: добавление колонки category в channels...")
    logger.info(f"Подключение к БД: {config.postgres_dsn.split('@')[-1] if '@' in config.postgres_dsn else 'скрыто'}")
    
    try:
        async with engine.begin() as conn:
            # Проверяем, существует ли колонка
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'channels' 
                AND column_name = 'category'
            """)
            result = await conn.execute(check_query)
            existing = result.fetchone()
            
            if existing:
                logger.info("✅ Колонка category уже существует в таблице channels")
                return True
            
            # Пытаемся добавить колонку
            try:
                alter_query = text("ALTER TABLE channels ADD COLUMN category TEXT")
                await conn.execute(alter_query)
                logger.info("✅ Колонка category успешно добавлена в таблицу channels")
                
                # Добавляем индекс для быстрой фильтрации по категории
                index_query = text("CREATE INDEX IF NOT EXISTS ix_channels_category ON channels(category)")
                await conn.execute(index_query)
                logger.info("✅ Индекс ix_channels_category создан")
                
            except Exception as perm_error:
                if "InsufficientPrivilegeError" in str(type(perm_error)) or "must be owner" in str(perm_error):
                    logger.error("❌ Недостаточно прав для изменения таблицы")
                    logger.error("")
                    logger.error("=" * 60)
                    logger.error("РЕШЕНИЕ: Выполните миграцию от имени суперпользователя PostgreSQL:")
                    logger.error("")
                    logger.error("  sudo -u postgres psql -d tg_analytics -c \\")
                    logger.error("    \"ALTER TABLE channels ADD COLUMN IF NOT EXISTS category TEXT;\"")
                    logger.error("")
                    logger.error("  sudo -u postgres psql -d tg_analytics -c \\")
                    logger.error("    \"CREATE INDEX IF NOT EXISTS ix_channels_category ON channels(category);\"")
                    logger.error("=" * 60)
                    logger.error("")
                    return False
                else:
                    raise
            
            # Проверяем результат
            result = await conn.execute(check_query)
            if result.fetchone():
                logger.info("✅ Проверка: колонка category присутствует в таблице")
                return True
            else:
                logger.error("❌ Ошибка: колонка category не найдена после добавления")
                return False
                
    except Exception as e:
        logger.error(f"❌ Ошибка при выполнении миграции: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Главная функция"""
    success = await migrate_add_category_column()
    if success:
        logger.info("🎉 Миграция завершена успешно!")
        logger.info("")
        logger.info("📋 СЛЕДУЮЩИЙ ШАГ:")
        logger.info("   Пересобрать базу каналов с category:")
        logger.info("   python reimport_database.py")
        sys.exit(0)
    else:
        logger.error("💥 Миграция завершилась с ошибкой")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
