#!/usr/bin/env python3
"""
Скрипт для переимпорта базы данных каналов с новым алгоритмом keywords.

ВНИМАНИЕ: Этот скрипт обновит ВСЕ keywords в базе данных!
Каналы, проанализированные через LLM, НЕ будут затронуты (у них есть audience).

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
import re
from pathlib import Path
from typing import Set, List, Optional

# Добавляем путь к проекту
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from sqlalchemy import select, update, text

from app.core.logging import setup_logging, get_logger
from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache
from app.services.excel_importer import extract_keywords_v2, CATEGORY_KEYWORDS

logger = get_logger(__name__)

EXCEL_PATH = "/home/alex/excel/DB_channel.xlsx"


async def update_keywords_from_excel(
    max_rows: Optional[int] = None,
    min_subscribers: int = 0,
    skip_llm_analyzed: bool = True
):
    """
    Обновляет keywords для каналов из Excel файла.
    
    Args:
        max_rows: Максимум строк
        min_subscribers: Минимум подписчиков
        skip_llm_analyzed: Пропускать каналы с LLM анализом (audience не пустой)
    """
    logger.info("="*60)
    logger.info("ПЕРЕИМПОРТ KEYWORDS С НОВЫМ АЛГОРИТМОМ")
    logger.info("="*60)
    
    logger.info(f"📂 Читаю Excel: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, header=1)
    
    if max_rows:
        df = df.iloc[:max_rows]
    
    logger.info(f"📊 Строк в Excel: {len(df)}")
    
    # Создаём маппинг username -> (category, title, description)
    excel_data = {}
    for _, row in df.iterrows():
        username = str(row.get("username") or "").strip()
        username = username.replace("@", "").replace("https://t.me/", "").replace("http://t.me/", "")
        
        if not username:
            continue
            
        try:
            subscribers = int(row.get("subscribers") or 0)
        except:
            subscribers = 0
            
        if subscribers < min_subscribers:
            continue
        
        title = str(row.get("title") or "").strip()
        description = str(row.get("description") or "").strip()
        category = str(row.get("category") or "").strip()
        
        if title.lower() == "nan":
            title = ""
        if description.lower() == "nan":
            description = ""
        if category.lower() == "nan":
            category = ""
        
        excel_data[username.lower()] = {
            "title": title,
            "description": description,
            "category": category,
        }
    
    logger.info(f"📋 Каналов в Excel с данными: {len(excel_data)}")
    
    # Обновляем keywords в БД
    updated = 0
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
        batch = []
        
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
            
            # Генерируем новые keywords
            new_keywords = extract_keywords_v2(
                excel_info["title"],
                excel_info["description"],
                excel_info["category"],
                limit=20
            )
            
            if not new_keywords:
                new_keywords = [excel_info["category"]] if excel_info["category"] else [username]
            
            batch.append({
                "channel_id": channel_id,
                "keywords_json": json.dumps(new_keywords, ensure_ascii=False)
            })
            
            if len(batch) >= batch_size:
                # Batch update
                for item in batch:
                    await session.execute(
                        update(KeywordsCache)
                        .where(KeywordsCache.channel_id == item["channel_id"])
                        .values(keywords_json=item["keywords_json"])
                    )
                await session.commit()
                updated += len(batch)
                logger.info(f"✅ Обновлено: {updated}")
                batch = []
        
        # Остаток
        if batch:
            for item in batch:
                await session.execute(
                    update(KeywordsCache)
                    .where(KeywordsCache.channel_id == item["channel_id"])
                    .values(keywords_json=item["keywords_json"])
                )
            await session.commit()
            updated += len(batch)
    
    logger.info("="*60)
    logger.info("📊 РЕЗУЛЬТАТЫ:")
    logger.info(f"   ✅ Обновлено keywords: {updated}")
    logger.info(f"   ⏭️  Пропущено (LLM): {skipped_llm}")
    logger.info(f"   ⏭️  Не найдено в Excel: {skipped_not_found}")
    logger.info("="*60)
    
    return updated


async def main():
    setup_logging()
    
    max_rows = int(sys.argv[1]) if len(sys.argv) >= 2 else None
    min_subs = int(sys.argv[2]) if len(sys.argv) >= 3 else 0
    
    logger.info(f"🚀 Старт переимпорта")
    if max_rows:
        logger.info(f"   Лимит строк: {max_rows}")
    if min_subs:
        logger.info(f"   Минимум подписчиков: {min_subs}")
    
    await update_keywords_from_excel(
        max_rows=max_rows,
        min_subscribers=min_subs,
        skip_llm_analyzed=True
    )
    
    logger.info("🎉 Готово!")
    logger.info("")
    logger.info("📋 СЛЕДУЮЩИЙ ШАГ:")
    logger.info("   Пересчитать similarity:")
    logger.info("   python -m app.services.similarity_engine.cli seq 500")


if __name__ == "__main__":
    asyncio.run(main())

