# app/services/import_excel_cli.py

import asyncio
import sys
from pathlib import Path

from app.services.excel_importer import import_channels_from_excel


async def main():
    if len(sys.argv) < 2:
        print("Использование: python -m app.services.import_excel_cli /путь/к/файлу.xlsx [max_rows]")
        return

    path = sys.argv[1]
    max_rows = int(sys.argv[2]) if len(sys.argv) >= 3 else None

    if not Path(path).exists():
        print(f"Файл не найден: {path}")
        return

    print(f"Старт импорта из файла: {path}")
    if max_rows:
        print(f"Лимит строк: {max_rows}")

    imported = await import_channels_from_excel(path, max_rows=max_rows)
    print(f"Импорт завершён. Импортировано каналов: {imported}")


if __name__ == "__main__":
    asyncio.run(main())
