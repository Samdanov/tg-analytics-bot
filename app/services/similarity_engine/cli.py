# app/services/similarity_engine/cli.py
"""
CLI для запуска similarity расчётов.

Использует новую архитектуру:
- Similarity считается ВНУТРИ категорий
- Каналы разных категорий НЕ сравниваются
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.logging import setup_logging, get_logger
from app.services.similarity_engine.engine import SimilarityEngine
from app.services.similarity_engine.engine_single import calculate_similarity_for_channel

logger = get_logger(__name__)


async def run_batch(top_n: int = 500):
    """
    Batch-расчёт similarity по всем категориям.
    
    Новая архитектура:
    - Группировка по category
    - TF-IDF внутри каждой категории
    - Каналы разных категорий НЕ сравниваются
    """
    logger.info("=" * 60)
    logger.info("BATCH SIMILARITY (по категориям)")
    logger.info("top_n=%d", top_n)
    logger.info("=" * 60)
    
    engine = SimilarityEngine(top_n=top_n)
    await engine.calculate_similarity()
    
    logger.info("=" * 60)
    logger.info("ГОТОВО")
    logger.info("=" * 60)


async def run_single(channel_id: int, top_n: int = 10):
    """
    Расчёт similarity для одного канала.
    
    Новая архитектура:
    - Берёт category канала
    - Считает similarity ТОЛЬКО внутри этой категории
    """
    logger.info("=" * 60)
    logger.info("SINGLE CHANNEL SIMILARITY")
    logger.info("channel_id=%d, top_n=%d", channel_id, top_n)
    logger.info("=" * 60)
    
    result = await calculate_similarity_for_channel(channel_id, top_n=top_n)
    
    if result:
        logger.info("Успешно!")
    else:
        logger.warning("Нет данных для расчёта")


async def main():
    setup_logging()
    
    if len(sys.argv) < 2:
        print("""
Использование: python -m app.services.similarity_engine.cli <mode> [options]

Режимы:
  batch [top_n]           - Batch-расчёт по всем категориям (default: top_n=500)
  single <channel_id> [top_n] - Расчёт для одного канала (default: top_n=500)

Примеры:
  python -m app.services.similarity_engine.cli batch 10
  python -m app.services.similarity_engine.cli single 12345 10

ВАЖНО:
  - Similarity считается ТОЛЬКО внутри категорий
  - Каналы разных категорий НЕ сравниваются
  - category = PRIMARY TOPIC (жёсткий фильтр)
""")
        return
    
    mode = sys.argv[1]
    
    if mode == "batch":
        top_n = int(sys.argv[2]) if len(sys.argv) >= 3 else 500
        await run_batch(top_n=top_n)
    
    elif mode == "single":
        if len(sys.argv) < 3:
            print("Ошибка: укажите channel_id")
            print("Пример: python -m app.services.similarity_engine.cli single 12345")
            return
        
        channel_id = int(sys.argv[2])
        top_n = int(sys.argv[3]) if len(sys.argv) >= 4 else 500
        await run_single(channel_id, top_n=top_n)
    
    else:
        print(f"Неизвестный режим: {mode}")
        print("Используйте: batch или single")


if __name__ == "__main__":
    asyncio.run(main())
