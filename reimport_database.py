#!/usr/bin/env python3
"""
Скрипт для ПОЛНОЙ пересборки базы данных каналов.

ВАЖНО: Этот скрипт обновляет:
1. Category в таблице channels (PRIMARY TOPIC - не участвует в TF-IDF!)
2. Keywords в таблице keywords_cache (только из title + description)

Каналы, проанализированные через LLM, НЕ будут затронуты (у них есть audience).

ПЕРЕД ЗАПУСКОМ:
    python -m app.services.migrate_add_category  # Добавить колонку category

Использование:
    python reimport_database.py [max_rows] [min_subscribers]

Примеры:
    python reimport_database.py                    # Все каналы
    python reimport_database.py 10000              # Первые 10000
    python reimport_database.py 100000 1000        # 100К с >1000 подписчиков
"""

import asyncio
import sys
import json
from pathlib import Path
from typing import Optional

# Добавляем путь к проекту
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from sqlalchemy import select, update

from app.core.logging import setup_logging, get_logger
from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache
from app.services.excel_importer import extract_keywords_v2  # Чистая версия без category в keywords!

logger = get_logger(__name__)

EXCEL_PATH = "/home/alex/excel/DB_channel.xlsx"


async def update_database_from_excel(
    max_rows: Optional[int] = None,
    min_subscribers: int = 0,
    skip_llm_analyzed: bool = True
):
    """
    ПОЛНАЯ пересборка базы: обновляет category + keywords для каналов.
    
    ВАЖНО:
    - Category сохраняется в Channel.category (PRIMARY TOPIC)
    - Keywords извлекаются ТОЛЬКО из title + description (без category!)
    - Category НЕ участвует в TF-IDF similarity
    
    Args:
        max_rows: Максимум строк
        min_subscribers: Минимум подписчиков
        skip_llm_analyzed: Пропускать каналы с LLM анализом (audience не пустой)
    """
    logger.info("="*60)
    logger.info("ПОЛНАЯ ПЕРЕСБОРКА БАЗЫ КАНАЛОВ")
    logger.info("="*60)
    logger.info("📌 Category → Channel.category (PRIMARY TOPIC, не участвует в TF-IDF)")
    logger.info("📌 Keywords → только из title + description")
    logger.info("="*60)
    
    logger.info(f"📂 Читаю Excel: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, header=1)
    
    if max_rows:
        df = df.iloc[:max_rows]
    
    logger.info(f"📊 Строк в Excel: {len(df)}")
    
    # Создаём маппинг username -> (category, title, description)
    excel_data = {}
    categories_found = set()
    
    for _, row in df.iterrows():
        username = str(row.get("username") or "").strip()
        username = username.replace("@", "").replace("https://t.me/", "").replace("http://t.me/", "")
        
        if not username:
            continue
            
        try:
            subscribers = int(row.get("subscribers") or 0)
        except Exception:
            subscribers = 0
            
        if subscribers < min_subscribers:
            continue
        
        title = str(row.get("title") or "").strip()
        description = str(row.get("description") or "").strip()
        category = str(row.get("category") or "").strip()
        
        if title.lower() in ("nan", "none"):
            title = ""
        if description.lower() in ("nan", "none"):
            description = ""
        if category.lower() in ("nan", "none"):
            category = ""
        
        if category:
            categories_found.add(category)
        
        excel_data[username.lower()] = {
            "title": title,
            "description": description,
            "category": category,
        }
    
    logger.info(f"📋 Каналов в Excel с данными: {len(excel_data)}")
    logger.info(f"📋 Уникальных категорий: {len(categories_found)}")
    
    # Статистика
    updated_channels = 0
    updated_keywords = 0
    skipped_llm = 0
    skipped_not_found = 0
    
    async with async_session_maker() as session:
        # Загружаем все каналы с keywords
        q = select(
            Channel.id,
            Channel.username,
            KeywordsCache.audience
        ).join(KeywordsCache, KeywordsCache.channel_id == Channel.id)
        
        rows = (await session.execute(q)).all()
        logger.info(f"📊 Каналов в БД с keywords: {len(rows)}")
        
        batch_size = 1000
        channel_batch = []
        keywords_batch = []
        
        for channel_id, username, audience in rows:
            # Пропускаем LLM-анализированные
            if skip_llm_analyzed and audience and len(audience) > 50:
                skipped_llm += 1
                continue
            
            # Ищем в Excel
            excel_info = excel_data.get(username.lower() if username else "")
            if not excel_info:
                skipped_not_found += 1
                continue
            
            # 1. Обновляем category в Channel (PRIMARY TOPIC)
            channel_batch.append({
                "channel_id": channel_id,
                "category": excel_info["category"],
            })
            
            # 2. Генерируем ЧИСТЫЕ keywords (только title + description!)
            new_keywords = extract_keywords_v2(
                excel_info["title"],
                excel_info["description"],
                limit=20
            )
            
            # Fallback: если keywords пустые - берём username
            if not new_keywords:
                new_keywords = [username.lower()] if username else []
            
            keywords_batch.append({
                "channel_id": channel_id,
                "keywords_json": json.dumps(new_keywords, ensure_ascii=False)
            })
            
            # Batch commit
            if len(channel_batch) >= batch_size:
                # Update channels (category)
                for item in channel_batch:
                    await session.execute(
                        update(Channel)
                        .where(Channel.id == item["channel_id"])
                        .values(category=item["category"])
                    )
                
                # Update keywords_cache
                for item in keywords_batch:
                    await session.execute(
                        update(KeywordsCache)
                        .where(KeywordsCache.channel_id == item["channel_id"])
                        .values(keywords_json=item["keywords_json"])
                    )
                
                await session.commit()
                updated_channels += len(channel_batch)
                updated_keywords += len(keywords_batch)
                logger.info(f"✅ Обновлено: {updated_channels} каналов, {updated_keywords} keywords")
                channel_batch = []
                keywords_batch = []
        
        # Остаток
        if channel_batch:
            for item in channel_batch:
                await session.execute(
                    update(Channel)
                    .where(Channel.id == item["channel_id"])
                    .values(category=item["category"])
                )
            
            for item in keywords_batch:
                await session.execute(
                    update(KeywordsCache)
                    .where(KeywordsCache.channel_id == item["channel_id"])
                    .values(keywords_json=item["keywords_json"])
                )
            
            await session.commit()
            updated_channels += len(channel_batch)
            updated_keywords += len(keywords_batch)
    
    logger.info("="*60)
    logger.info("📊 РЕЗУЛЬТАТЫ:")
    logger.info(f"   ✅ Обновлено Channel.category: {updated_channels}")
    logger.info(f"   ✅ Обновлено keywords (чистые): {updated_keywords}")
    logger.info(f"   ⏭️  Пропущено (LLM): {skipped_llm}")
    logger.info(f"   ⏭️  Не найдено в Excel: {skipped_not_found}")
    logger.info("="*60)
    
    return updated_channels, updated_keywords


async def main():
    setup_logging()
    
    max_rows = int(sys.argv[1]) if len(sys.argv) >= 2 else None
    min_subs = int(sys.argv[2]) if len(sys.argv) >= 3 else 0
    
    logger.info(f"🚀 Старт полной пересборки базы")
    if max_rows:
        logger.info(f"   Лимит строк: {max_rows}")
    if min_subs:
        logger.info(f"   Минимум подписчиков: {min_subs}")
    
    updated_channels, updated_keywords = await update_database_from_excel(
        max_rows=max_rows,
        min_subscribers=min_subs,
        skip_llm_analyzed=True
    )
    
    logger.info("🎉 Готово!")
    logger.info("")
    logger.info("📋 ЧТО ИЗМЕНИЛОСЬ:")
    logger.info("   1. Channel.category = PRIMARY TOPIC (48 тем из Excel)")
    logger.info("   2. Keywords = ТОЛЬКО title + description (без category!)")
    logger.info("   3. Category НЕ участвует в TF-IDF similarity")
    logger.info("")
    logger.info("📋 СЛЕДУЮЩИЙ ШАГ:")
    logger.info("   Пересчитать similarity с новыми данными:")
    logger.info("   python -m app.services.similarity_engine.cli seq 500")


if __name__ == "__main__":
    asyncio.run(main())

