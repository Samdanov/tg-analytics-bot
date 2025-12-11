import asyncio

from app.core.logging import setup_logging
from app.services.health import check_db, check_telegram


async def main():
    setup_logging()
    db_ok, db_msg = await check_db()
    tg_ok, tg_msg = await check_telegram()

    print(db_msg)
    print(tg_msg)

    if not (db_ok and tg_ok):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
