#!/usr/bin/env python3
"""
Изменение категории канала вручную.

Использование:
    python fix_category.py <username или id> <новая_категория>
"""

import asyncio
import sys
from sqlalchemy import select, update

sys.path.insert(0, "/home/alex/apps/tg-analytics-bot")

from app.db.database import async_session_maker
from app.db.models import Channel
from app.services.llm.prompt import VALID_CATEGORIES


async def fix_category(identifier: str, new_category: str):
    """
    Изменяет категорию канала.
    
    Args:
        identifier: username (без @) или id:CHANNEL_ID
        new_category: новая категория из списка валидных
    """
    # Валидация категории
    if new_category not in VALID_CATEGORIES:
        print(f"❌ Категория '{new_category}' не найдена в списке валидных категорий!")
        print(f"\nДоступные категории:")
        for idx, cat in enumerate(VALID_CATEGORIES, 1):
            print(f"  {idx:2d}. {cat}")
        return False
    
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
            return False
        
        old_category = channel.category or "НЕ НАЗНАЧЕНА"
        
        print(f"\n{'='*60}")
        print(f"Канал: @{channel.username or f'id:{channel.id}'}")
        print(f"Название: {channel.title or 'N/A'}")
        print(f"{'='*60}")
        print(f"Старая категория: {old_category}")
        print(f"Новая категория:  {new_category}")
        print(f"{'='*60}\n")
        
        # Обновляем категорию
        channel.category = new_category
        await session.commit()
        
        print(f"✅ Категория успешно обновлена!")
        print(f"\n⚠️  ВАЖНО: Теперь нужно пересчитать similarity:")
        print(f"   1. Для этого канала:")
        print(f"      cd /home/alex/apps/tg-analytics-bot")
        print(f"      python3 -m app.services.similarity_engine.cli single {channel.id}")
        print(f"\n   2. Или для всей категории:")
        print(f"      python3 -m app.services.similarity_engine.cli batch")
        
        return True


async def main():
    if len(sys.argv) < 3:
        print("Использование: python fix_category.py <username или id> <категория>")
        print("\nПримеры:")
        print("  python fix_category.py technews 'видео и фильмы'")
        print("  python fix_category.py @gamenews 'игры'")
        print("  python fix_category.py id:-1002508742544 'технологии'")
        print("\nДоступные категории:")
        for idx, cat in enumerate(VALID_CATEGORIES, 1):
            print(f"  {idx:2d}. {cat}")
        sys.exit(1)
    
    identifier = sys.argv[1]
    new_category = sys.argv[2]
    
    await fix_category(identifier, new_category)


if __name__ == "__main__":
    asyncio.run(main())
