#!/usr/bin/env python3
"""
Диагностика similarity для конкретного канала.

Показывает:
- Категорию канала
- Ключевые слова
- С какими каналами его сравнивают
- Похожие каналы из выдачи
"""

import asyncio
import sys
import json
from sqlalchemy import select

sys.path.insert(0, "/home/alex/apps/tg-analytics-bot")

from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache, AnalyticsResults


async def diagnose_channel(identifier: str):
    """
    Диагностирует similarity для канала.
    
    Args:
        identifier: username (без @) или id:CHANNEL_ID
    """
    print(f"\n{'='*80}")
    print(f"ДИАГНОСТИКА КАНАЛА: {identifier}")
    print(f"{'='*80}\n")
    
    async with async_session_maker() as session:
        # Находим канал
        if identifier.startswith("id:"):
            channel_id = int(identifier[3:])
            query = select(Channel).where(Channel.id == channel_id)
        else:
            username = identifier.lstrip("@")
            query = select(Channel).where(Channel.username == username)
        
        result = await session.execute(query)
        channel = result.scalar_one_or_none()
        
        if not channel:
            print(f"❌ Канал '{identifier}' не найден в базе данных")
            return
        
        print(f"✅ Канал найден:")
        print(f"   ID: {channel.id}")
        print(f"   Username: {channel.username or 'N/A'}")
        print(f"   Название: {channel.title or 'N/A'}")
        print(f"   Категория: {channel.category or 'НЕ НАЗНАЧЕНА'}")
        print(f"   Подписчики: {channel.subscribers or 0}")
        print()
        
        # Проверяем keywords
        kw_query = select(KeywordsCache).where(KeywordsCache.channel_id == channel.id)
        kw_result = await session.execute(kw_query)
        kw_cache = kw_result.scalar_one_or_none()
        
        if kw_cache:
            keywords = json.loads(kw_cache.keywords_json or "[]")
            print(f"📋 Ключевые слова ({len(keywords)}):")
            print(f"   {', '.join(keywords[:20])}")
            if len(keywords) > 20:
                print(f"   ... и еще {len(keywords) - 20}")
            print()
            print(f"👥 Целевая аудитория:")
            print(f"   {kw_cache.audience or 'N/A'}")
            print()
        else:
            print("❌ Ключевые слова не найдены\n")
        
        # Проверяем, с какими каналами сравнивают (каналы той же категории)
        if channel.category:
            same_category_query = (
                select(Channel.id, Channel.username, Channel.title, Channel.category)
                .where(Channel.category == channel.category)
                .where(Channel.id != channel.id)
                .limit(10)
            )
            same_cat_result = await session.execute(same_category_query)
            same_cat_channels = same_cat_result.all()
            
            print(f"🔍 Каналы в той же категории '{channel.category}' (примеры):")
            for ch_id, ch_username, ch_title, ch_cat in same_cat_channels[:10]:
                print(f"   • @{ch_username or f'id:{ch_id}'}: {ch_title or 'N/A'}")
            print()
            
            # Считаем общее количество каналов в категории
            count_query = select(Channel.id).where(Channel.category == channel.category)
            count_result = await session.execute(count_query)
            total_in_category = len(count_result.all())
            print(f"📊 Всего каналов в категории '{channel.category}': {total_in_category}")
            print()
        else:
            print("❌ Категория не назначена - similarity не будет работать!\n")
        
        # Проверяем результаты similarity
        similarity_query = select(AnalyticsResults).where(AnalyticsResults.channel_id == channel.id)
        similarity_result = await session.execute(similarity_query)
        analytics = similarity_result.scalar_one_or_none()
        
        if analytics:
            similar_channels = json.loads(analytics.similar_channels_json or "[]")
            print(f"🎯 Похожие каналы ({len(similar_channels)}):")
            
            if similar_channels:
                # Загружаем информацию о похожих каналах
                similar_ids = [item["channel_id"] for item in similar_channels[:10]]
                similar_query = select(Channel).where(Channel.id.in_(similar_ids))
                similar_result = await session.execute(similar_query)
                similar_map = {ch.id: ch for ch in similar_result.scalars().all()}
                
                for idx, item in enumerate(similar_channels[:10], 1):
                    ch_id = item["channel_id"]
                    score = item["score"]
                    ch = similar_map.get(ch_id)
                    
                    if ch:
                        print(f"   {idx}. @{ch.username or f'id:{ch_id}'}: {ch.title or 'N/A'}")
                        print(f"      Score: {score:.3f}, Категория: {ch.category or 'N/A'}")
                    else:
                        print(f"   {idx}. ID {ch_id}: Score {score:.3f} (не найден в БД)")
                print()
            else:
                print("   Нет похожих каналов\n")
        else:
            print("❌ Результаты similarity не найдены (канал не проанализирован)\n")
        
        # Рекомендации
        print(f"\n{'='*80}")
        print("💡 РЕКОМЕНДАЦИИ:")
        print(f"{'='*80}\n")
        
        if not channel.category:
            print("⚠️  КРИТИЧНО: Категория не назначена!")
            print("   → Запустите анализ канала через бота")
            print("   → Или вручную назначьте категорию в БД")
        elif not kw_cache or not keywords:
            print("⚠️  КРИТИЧНО: Нет ключевых слов!")
            print("   → Запустите анализ канала через бота")
        elif len(keywords) < 5:
            print("⚠️  Мало ключевых слов (рекомендуется 10-15)")
            print("   → Переанализируйте канал с большим количеством постов")
        
        if channel.category and channel.category in ["новости и сми", "другое", "познавательное"]:
            print("\n⚠️  Слишком общая категория!")
            print(f"   Категория '{channel.category}' объединяет разные темы")
            print("   → Попробуйте вручную уточнить категорию:")
            print("      • Для трейлеров/сериалов → 'видео и фильмы'")
            print("      • Для игр → 'игры'")
            print("      • Для IT-новостей → 'технологии'")


async def main():
    if len(sys.argv) < 2:
        print("Использование: python diagnose_similarity.py <username или id:CHANNEL_ID>")
        print("\nПримеры:")
        print("  python diagnose_similarity.py technews")
        print("  python diagnose_similarity.py @technews")
        print("  python diagnose_similarity.py id:-1002508742544")
        sys.exit(1)
    
    identifier = sys.argv[1]
    await diagnose_channel(identifier)


if __name__ == "__main__":
    asyncio.run(main())
