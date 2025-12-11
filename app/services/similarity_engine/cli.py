import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.logging import setup_logging
from app.services.usecases.similarity_service import recalc_all


async def main():
    setup_logging()
    await recalc_all(top_n=10)


if __name__ == "__main__":
    asyncio.run(main())
