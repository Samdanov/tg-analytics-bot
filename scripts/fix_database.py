import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# app/services/fix_database.py

"""
Скрипт для исправления проблем в базе данных:
1. Добавляет ключевые слова каналам без них
2. Пересчитывает similarity для каналов без результатов аналитики
"""

import asyncio
from sqlalchemy import select, func

from app.db.database import async_session_maker
from app.core.logging import setup_logging, get_logger
from app.db.models import Channel, KeywordsCache, AnalyticsResults
from app.services.excel_importer import extract_keywords
from app.services.llm.analyzer import save_analysis
from app.services.use_cases.similarity_service import recalc_for_channel

logger = get_logger(__name__)


async def fix_missing_keywords():
    """Добавляет ключевые слова каналам без них."""
    async with async_session_maker() as session:
        # Находим каналы без ключевых слов
        result = await session.execute(
            select(Channel)
            .outerjoin(KeywordsCache, Channel.id == KeywordsCache.channel_id)
            .where(KeywordsCache.channel_id.is_(None))
        )
        channels_without_keywords = result.scalars().all()
        
        total = len(channels_without_keywords)
        if total == 0:
            logger.info("Нет каналов без ключевых слов")
            return 0
        
        logger.info(f"Найдено каналов без ключевых слов: {total}")
        
        fixed = 0
        for i, channel in enumerate(channels_without_keywords, 1):
            try:
                # Извлекаем ключевые слова из title и description
                title = channel.title or ""
                description = channel.description or ""
                username = channel.username or ""
                
                full_text = f"{title} {description} {username}"
                keywords = extract_keywords(title, description, limit=20)
                
                if not keywords:
                    # Если не удалось извлечь, используем username
                    keywords = [username] if username else []
                
                if keywords:
                    # Сохраняем ключевые слова
                    await save_analysis(channel.id, {
                        "audience": "",
                        "keywords": keywords
                    })
                    fixed += 1
                    
                    if i % 100 == 0:
                        logger.info(f"Обработано: {i}/{total}, исправлено: {fixed}")
            except Exception as e:
                logger.error(f"Ошибка при обработке канала {channel.id} (@{channel.username}): {e}")
                continue
        
        logger.info(f"✅ Исправлено каналов: {fixed}/{total}")
        return fixed


async def fix_missing_analytics(top_n: int = 10):
    """Пересчитывает similarity для каналов без результатов аналитики."""
    async with async_session_maker() as session:
        # Находим каналы без результатов аналитики
        result = await session.execute(
            select(Channel)
            .outerjoin(AnalyticsResults, Channel.id == AnalyticsResults.channel_id)
            .where(AnalyticsResults.channel_id.is_(None))
        )
        channels_without_analytics = result.scalars().all()
        
        total = len(channels_without_analytics)
        if total == 0:
            logger.info("Нет каналов без результатов аналитики")
            return 0
        
        logger.info(f"Найдено каналов без результатов аналитики: {total}")
        logger.info(f"Начинаю пересчет similarity (top_n={top_n})...")
        
        fixed = 0
        for i, channel in enumerate(channels_without_analytics, 1):
            try:
                # Проверяем, есть ли у канала ключевые слова
                keywords_result = await session.execute(
                    select(KeywordsCache).where(KeywordsCache.channel_id == channel.id)
                )
                keywords_cache = keywords_result.scalar_one_or_none()
                
                if not keywords_cache or not keywords_cache.keywords_json:
                    logger.warning(f"Канал {channel.id} (@{channel.username}) не имеет ключевых слов, пропускаю")
                    continue
                
                # Пересчитываем similarity
                success = await recalc_for_channel(channel.id, top_n=top_n)
                if success:
                    fixed += 1
                
                if i % 100 == 0:
                    logger.info(f"Обработано: {i}/{total}, исправлено: {fixed}")
            except Exception as e:
                logger.error(f"Ошибка при обработке канала {channel.id} (@{channel.username}): {e}")
                continue
        
        logger.info(f"✅ Исправлено каналов: {fixed}/{total}")
        return fixed


async def main():
    """Точка входа."""
    import sys
    
    setup_logging()
    
    print("\n" + "="*60)
    print("ИСПРАВЛЕНИЕ БАЗЫ ДАННЫХ")
    print("="*60 + "\n")
    
    # Параметры
    fix_keywords = True
    fix_analytics = True
    top_n = 10
    
    if len(sys.argv) > 1:
        if "keywords" in sys.argv[1].lower():
            fix_analytics = False
        elif "analytics" in sys.argv[1].lower():
            fix_keywords = False
    
    if len(sys.argv) > 2:
        try:
            top_n = int(sys.argv[2])
        except ValueError:
            pass
    
    try:
        # 1. Исправляем ключевые слова
        if fix_keywords:
            print("1. Исправление ключевых слов...")
            keywords_fixed = await fix_missing_keywords()
            print(f"   ✅ Исправлено: {keywords_fixed}\n")
        else:
            print("1. Пропущено (ключевые слова)\n")
        
        # 2. Исправляем результаты аналитики
        if fix_analytics:
            print("2. Пересчет similarity...")
            print(f"   Это может занять много времени...")
            analytics_fixed = await fix_missing_analytics(top_n=top_n)
            print(f"   ✅ Исправлено: {analytics_fixed}\n")
        else:
            print("2. Пропущено (результаты аналитики)\n")
        
        print("="*60)
        print("✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО")
        print("="*60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
