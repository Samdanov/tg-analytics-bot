import asyncio
import sys
from pathlib import Path

from app.core.logging import setup_logging
from app.services.excel_importer import import_channels_from_excel


async def main():
    setup_logging()

    if len(sys.argv) < 2:
        print("Использование: python -m app.services.import_excel_cli /путь/к/файлу.xlsx [max_rows] [min_subscribers]")
        return

    path = sys.argv[1]
    max_rows = int(sys.argv[2]) if len(sys.argv) >= 3 else None
    min_subs = int(sys.argv[3]) if len(sys.argv) >= 4 else 0

    if not Path(path).exists():
        print(f"Файл не найден: {path}")
        return

    print(f"Старт импорта из файла: {path}")
    if max_rows:
        print(f"Лимит строк: {max_rows}")
    if min_subs:
        print(f"Минимум подписчиков: {min_subs}")

    imported = await import_channels_from_excel(path, max_rows=max_rows, min_subscribers=min_subs)
    print(f"Импорт завершён. Импортировано каналов: {imported}")


if __name__ == "__main__":
    asyncio.run(main())
