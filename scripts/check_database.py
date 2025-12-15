import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# app/services/check_database.py

"""
Скрипт для проверки базы данных на наличие и полноту данных.
"""

import asyncio
from sqlalchemy import select, func, text

from app.db.database import async_session_maker
from app.core.logging import setup_logging, get_logger
from app.db.models import (
    Channel,
    Post,
    KeywordsCache,
    AnalyticsResults,
)

logger = get_logger(__name__)


async def check_database():
    """Проверяет базу данных на наличие и полноту данных."""
    async with async_session_maker() as session:
        try:
            print("\n" + "="*60)
            print("ПРОВЕРКА БАЗЫ ДАННЫХ")
            print("="*60 + "\n")
            
            # 1. Каналы
            result = await session.execute(select(func.count(Channel.id)))
            total_channels = result.scalar() or 0
            
            result = await session.execute(
                select(func.count(Channel.id)).where(Channel.subscribers >= 1000)
            )
            channels_1000_plus = result.scalar() or 0
            
            result = await session.execute(
                select(
                    func.min(Channel.subscribers),
                    func.max(Channel.subscribers),
                    func.avg(Channel.subscribers)
                )
            )
            min_subs, max_subs, avg_subs = result.first() or (None, None, None)
            
            result = await session.execute(
                select(func.count(Channel.id)).where(Channel.subscribers.is_(None))
            )
            channels_no_subs = result.scalar() or 0
            
            result = await session.execute(
                select(func.count(Channel.id)).where(Channel.username.is_(None))
            )
            channels_no_username = result.scalar() or 0
            
            print("📊 КАНАЛЫ:")
            print(f"  Всего каналов: {total_channels:,}")
            print(f"  С подписчиками >= 1000: {channels_1000_plus:,}")
            print(f"  Без подписчиков: {channels_no_subs:,}")
            print(f"  Без username: {channels_no_username:,}")
            if min_subs is not None:
                print(f"  Минимум подписчиков: {int(min_subs):,}")
                print(f"  Максимум подписчиков: {int(max_subs):,}")
                print(f"  Среднее подписчиков: {int(avg_subs):,}")
            
            # 2. Посты
            result = await session.execute(select(func.count(Post.id)))
            total_posts = result.scalar() or 0
            
            result = await session.execute(
                select(func.count(func.distinct(Post.channel_id)))
            )
            channels_with_posts = result.scalar() or 0
            
            print(f"\n📝 ПОСТЫ:")
            print(f"  Всего постов: {total_posts:,}")
            print(f"  Каналов с постами: {channels_with_posts:,}")
            if total_channels > 0:
                print(f"  Процент каналов с постами: {(channels_with_posts/total_channels)*100:.1f}%")
            
            # 3. Ключевые слова
            result = await session.execute(select(func.count(KeywordsCache.channel_id)))
            total_keywords = result.scalar() or 0
            
            result = await session.execute(
                select(func.count(KeywordsCache.channel_id)).where(
                    KeywordsCache.keywords_json.isnot(None)
                )
            )
            keywords_with_data = result.scalar() or 0
            
            print(f"\n🔑 КЛЮЧЕВЫЕ СЛОВА:")
            print(f"  Каналов с ключевыми словами: {total_keywords:,}")
            print(f"  С данными keywords_json: {keywords_with_data:,}")
            if total_channels > 0:
                print(f"  Процент каналов с ключевыми словами: {(total_keywords/total_channels)*100:.1f}%")
            
            # 4. Результаты аналитики (similarity)
            result = await session.execute(select(func.count(AnalyticsResults.id)))
            total_analytics = result.scalar() or 0
            
            result = await session.execute(
                select(func.count(func.distinct(AnalyticsResults.channel_id)))
            )
            channels_with_analytics = result.scalar() or 0
            
            result = await session.execute(
                select(func.count(AnalyticsResults.id)).where(
                    AnalyticsResults.similar_channels_json.isnot(None)
                )
            )
            analytics_with_data = result.scalar() or 0
            
            print(f"\n📈 РЕЗУЛЬТАТЫ АНАЛИТИКИ (SIMILARITY):")
            print(f"  Всего записей: {total_analytics:,}")
            print(f"  Каналов с результатами: {channels_with_analytics:,}")
            print(f"  С данными similar_channels_json: {analytics_with_data:,}")
            if total_channels > 0:
                print(f"  Процент каналов с результатами: {(channels_with_analytics/total_channels)*100:.1f}%")
            
            # 5. Статистика по подписчикам (распределение)
            print(f"\n📊 РАСПРЕДЕЛЕНИЕ ПО ПОДПИСЧИКАМ:")
            
            ranges = [
                (0, 999, "0-999"),
                (1000, 4999, "1,000-4,999"),
                (5000, 9999, "5,000-9,999"),
                (10000, 49999, "10,000-49,999"),
                (50000, 99999, "50,000-99,999"),
                (100000, None, "100,000+"),
            ]
            
            for min_val, max_val, label in ranges:
                if max_val is None:
                    query = select(func.count(Channel.id)).where(
                        Channel.subscribers >= min_val
                    )
                else:
                    query = select(func.count(Channel.id)).where(
                        Channel.subscribers >= min_val,
                        Channel.subscribers <= max_val
                    )
                result = await session.execute(query)
                count = result.scalar() or 0
                if total_channels > 0:
                    percentage = (count / total_channels) * 100
                    print(f"  {label:20s}: {count:6,} ({percentage:5.1f}%)")
                else:
                    print(f"  {label:20s}: {count:6,}")
            
            # 6. Проверка целостности
            print(f"\n🔍 ПРОВЕРКА ЦЕЛОСТНОСТИ:")
            
            # Каналы без ключевых слов
            result = await session.execute(
                select(func.count(Channel.id))
                .outerjoin(KeywordsCache, Channel.id == KeywordsCache.channel_id)
                .where(KeywordsCache.channel_id.is_(None))
            )
            channels_no_keywords = result.scalar() or 0
            print(f"  Каналов без ключевых слов: {channels_no_keywords:,}")
            
            # Каналы без результатов аналитики
            result = await session.execute(
                select(func.count(Channel.id))
                .outerjoin(AnalyticsResults, Channel.id == AnalyticsResults.channel_id)
                .where(AnalyticsResults.channel_id.is_(None))
            )
            channels_no_analytics = result.scalar() or 0
            print(f"  Каналов без результатов аналитики: {channels_no_analytics:,}")
            
            # Итоговая оценка
            print(f"\n" + "="*60)
            print("ИТОГОВАЯ ОЦЕНКА:")
            print("="*60)
            
            if total_channels == 0:
                print("❌ База данных пуста - нет каналов")
            elif channels_1000_plus == 0:
                print("⚠️  В базе нет каналов с подписчиками >= 1000")
            elif channels_with_analytics == 0:
                print("⚠️  База заполнена каналами, но нет результатов similarity")
                print("   Необходимо запустить пересчет similarity")
            elif channels_with_analytics < total_channels * 0.5:
                print("⚠️  Меньше 50% каналов имеют результаты similarity")
                print("   Рекомендуется запустить пересчет similarity")
            else:
                print("✅ База данных заполнена и готова к работе")
                print(f"   - {total_channels:,} каналов")
                print(f"   - {channels_1000_plus:,} каналов с >= 1000 подписчиков")
                print(f"   - {channels_with_analytics:,} каналов с результатами similarity")
            
            print("="*60 + "\n")
            
        except Exception as e:
            logger.error(f"Ошибка при проверке БД: {e}")
            raise


async def main():
    """Точка входа."""
    setup_logging()
    await check_database()


if __name__ == "__main__":
    asyncio.run(main())
