# ORBITA AI — Аналитик Telegram-каналов

🤖 Telegram-бот с AI для анализа целевой аудитории каналов и поиска похожих каналов для размещения рекламы.

## 🎯 Возможности

- **AI-анализ аудитории** — определяет ЦА, интересы, боли через GPT-4
- **Поиск похожих каналов** — находит до 500 релевантных каналов для рекламы
- **База 20 000+ каналов** — с возможностью расширения
- **Excel-отчёты** — готовые списки с метриками и описаниями
- **Автоматический workflow** — просто отправь ссылку или пост

## 📋 Требования

- Python 3.10+
- PostgreSQL 12+
- Telegram Bot API token
- Telegram API credentials (api_id, api_hash)
- OpenAI API key

## 🚀 Установка

### 1. Клонирование и подготовка

```bash
cd /home/alex/apps
git clone <your-repo> tg-analytics-bot
cd tg-analytics-bot
```

### 2. Виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. База данных

```bash
# Создать БД PostgreSQL
createdb tg_analytics

# Применить схему
psql -d tg_analytics -f app/db/schema.sql
```

### 4. Конфигурация

Создай файл `.env` в корне проекта:

```env
# Telegram Bot
BOT_TOKEN=your_bot_token_from_botfather

# Telegram API (получить на https://my.telegram.org)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash

# PostgreSQL
POSTGRES_DSN=postgresql+asyncpg://user:password@localhost/tg_analytics

# OpenAI
OPENAI_API_KEY=sk-your-openai-key

# Логирование (опционально)
LOG_LEVEL=INFO
```

### 5. Импорт базы каналов (опционально)

```bash
# Импортировать из Excel (с фильтром по подписчикам)
PYTHONPATH=/home/alex/apps/tg-analytics-bot python -m app.services.import_excel_cli \
  /path/to/channels.xlsx 0 1000

# где:
# - 0 - без лимита строк (или число для ограничения)
# - 1000 - минимум подписчиков
```

### 6. Расчёт similarity (если импортировали каналы)

```bash
# Режим chunk (рекомендуется для больших баз)
PYTHONPATH=/home/alex/apps/tg-analytics-bot python -m app.services.similarity_engine.cli chunk 10 2000

# где:
# - chunk - режим (batch/seq/chunk)
# - 10 - top_n похожих каналов
# - 2000 - размер чанка
```

## 🎮 Использование

### Запуск вручную

```bash
cd /home/alex/apps/tg-analytics-bot
source venv/bin/activate
PYTHONPATH=/home/alex/apps/tg-analytics-bot python -m app.main
```

### Запуск как systemd service (рекомендуется)

```bash
# Установка
sudo cp orbita-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable orbita-bot
sudo systemctl start orbita-bot

# Проверка статуса
sudo systemctl status orbita-bot

# Просмотр логов
tail -f /home/alex/apps/tg-analytics-bot/logs/bot.log

# Перезапуск
sudo systemctl restart orbita-bot
```

## 💬 Команды бота

### Основные команды

- `/start` — главное меню
- `/add_channel @username` — добавить канал в базу
- `/analyze @username` — анализ аудитории канала
- `/export @username` — скачать отчёт
- `/fetch @username` — проверить доступность канала

### Быстрый workflow

1. Отправь боту ссылку на канал или перешли пост
2. Выбери количество похожих каналов (10/25/50/100/500)
3. Получи анализ ЦА и Excel-отчёт с похожими каналами

## 🛠 Утилиты

### Health check

```bash
PYTHONPATH=/home/alex/apps/tg-analytics-bot python -m app.services.health_cli
```

### Импорт каналов из Excel

```bash
python -m app.services.import_excel_cli <file.xlsx> [max_rows] [min_subscribers]
```

### Пересчёт similarity

```bash
# Все каналы (chunk-режим для больших баз)
python -m app.services.similarity_engine.cli chunk 10 2000

# Последовательный режим (медленнее, меньше памяти)
python -m app.services.similarity_engine.cli seq 10

# Batch (требует много памяти)
python -m app.services.similarity_engine.cli batch 10
```

## 📁 Структура проекта

```
tg-analytics-bot/
├── app/
│   ├── bot/
│   │   ├── handlers/          # Обработчики команд
│   │   └── middlewares/       # Middleware (error handling)
│   ├── core/
│   │   ├── config.py          # Конфигурация
│   │   └── logging.py         # Логирование
│   ├── db/
│   │   ├── database.py        # SQLAlchemy setup
│   │   ├── models.py          # ORM модели
│   │   ├── repo.py            # Репозиторий
│   │   └── schema.sql         # SQL схема
│   ├── services/
│   │   ├── llm/               # OpenAI интеграция
│   │   ├── telegram_parser/   # Telethon парсинг
│   │   ├── similarity_engine/ # Движок похожести
│   │   ├── usecases/          # Бизнес-логика
│   │   ├── helpers.py         # Вспомогательные функции
│   │   ├── health.py          # Health checks
│   │   └── xlsx_generator.py  # Генерация отчётов
│   └── main.py                # Точка входа
├── reports/                   # Сгенерированные отчёты
├── logs/                      # Логи
├── requirements.txt
├── orbita-bot.service        # Systemd service
└── README.md
```

## 🔧 Архитектура

### Слои приложения

1. **Handlers** — обработка команд от пользователя
2. **Usecases** — бизнес-логика и оркестрация
3. **Services** — специфичные сервисы (LLM, Telethon, Similarity)
4. **Repository** — работа с базой данных

### Пайплайн анализа

```
Ссылка на канал
    ↓
Telethon (парсинг постов)
    ↓
LLM (анализ ЦА + ключевые слова)
    ↓
Similarity Engine (поиск похожих)
    ↓
Excel Generator (отчёт)
    ↓
Отправка пользователю
```

## 🐛 Troubleshooting

### Бот не запускается

```bash
# Проверить логи
sudo journalctl -u orbita-bot -n 100

# Проверить конфигурацию
python -c "from app.core.config import validate_config; validate_config()"

# Health check
PYTHONPATH=/home/alex/apps/tg-analytics-bot python -m app.services.health_cli
```

### OOM при расчёте similarity

```bash
# Использовать chunk-режим с меньшим размером чанка
python -m app.services.similarity_engine.cli chunk 10 1000
```

### Проблемы с Telethon

```bash
# Удалить сессию и переавторизоваться
rm tg_parser.session
python -m app.main
```

## 📊 Мониторинг

### Логи

```bash
# Основные логи
tail -f /home/alex/apps/tg-analytics-bot/logs/bot.log

# Ошибки
tail -f /home/alex/apps/tg-analytics-bot/logs/bot-error.log

# Systemd journal
sudo journalctl -u orbita-bot -f
```

### Метрики БД

```sql
-- Количество каналов
SELECT COUNT(*) FROM channels;

-- Каналы с ключевыми словами
SELECT COUNT(*) FROM keywords_cache;

-- Каналы с результатами similarity
SELECT COUNT(DISTINCT channel_id) FROM analytics_results;
```

## 🔐 Безопасность

- **Секреты** — хранятся в `.env`, не коммитятся
- **Логи** — не содержат API ключей
- **Валидация** — проверка конфига при старте
- **Rate limits** — таймауты и ретраи для API

## 📝 Разработка

### Установка dev-зависимостей

```bash
pip install -r requirements-dev.txt  # если есть
```

### Линтинг

```bash
# Проверка через Cursor/VS Code встроенный linter
# Или вручную:
pylint app/
```

## 📄 Лицензия

Proprietary - All rights reserved

## 👨‍💻 Автор

Alex - [Telegram Bot](https://t.me/orbita_ai_bot)

## 🆘 Поддержка

Если возникли проблемы:
1. Проверь логи (`tail -f logs/bot.log`)
2. Проверь статус сервиса (`sudo systemctl status orbita-bot`)
3. Запусти health check (`python -m app.services.health_cli`)
4. Проверь .env конфигурацию
