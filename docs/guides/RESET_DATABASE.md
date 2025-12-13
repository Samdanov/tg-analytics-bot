# Инструкция по очистке и перезаполнению базы данных

## ⚠️ ВНИМАНИЕ
Эта процедура **полностью удалит все данные** из базы данных:
- Все каналы
- Все посты
- Все ключевые слова
- Все результаты аналитики
- Все пользователи и запросы

## Шаги выполнения

### 1. Остановить бота (если запущен)

```bash
sudo systemctl stop orbita-bot
```

### 2. Очистить базу данных

```bash
cd /home/alex/apps/tg-analytics-bot
source venv/bin/activate
PYTHONPATH=/home/alex/apps/tg-analytics-bot python -m app.services.clear_database
```

При запросе введите `yes` для подтверждения.

### 3. Импортировать каналы из Excel (только с подписчиками >= 1000)

```bash
PYTHONPATH=/home/alex/apps/tg-analytics-bot python -m app.services.import_excel_cli \
  /home/alex/excel/DB_channel.xlsx \
  0 \
  1000
```

Параметры:
- `/home/alex/excel/DB_channel.xlsx` - путь к файлу
- `0` - без ограничения по количеству строк (0 = все строки)
- `1000` - минимум подписчиков (только каналы с >= 1000 подписчиков)

### 4. Пересчитать схожесть каналов (similarity)

Рекомендуется использовать режим `chunk` для больших баз:

```bash
PYTHONPATH=/home/alex/apps/tg-analytics-bot python -m app.services.similarity_engine.cli chunk 10 2000
```

Параметры:
- `chunk` - режим работы (рекомендуется для больших баз)
- `10` - количество похожих каналов (top_n)
- `2000` - размер чанка (количество каналов для обработки за раз)

Альтернативные режимы:
- `seq` - последовательный режим (медленнее, но меньше памяти):
  ```bash
  PYTHONPATH=/home/alex/apps/tg-analytics-bot python -m app.services.similarity_engine.cli seq 10
  ```

- `batch` - пакетный режим (быстрее, но требует много памяти):
  ```bash
  PYTHONPATH=/home/alex/apps/tg-analytics-bot python -m app.services.similarity_engine.cli batch 10
  ```

### 5. Запустить бота

```bash
sudo systemctl start orbita-bot
sudo systemctl status orbita-bot
```

## Проверка результатов

### Количество каналов в БД

```bash
psql -d tg_analytics -c "SELECT COUNT(*) FROM channels WHERE subscribers >= 1000;"
```

### Количество каналов с ключевыми словами

```bash
psql -d tg_analytics -c "SELECT COUNT(*) FROM keywords_cache;"
```

### Количество каналов с результатами similarity

```bash
psql -d tg_analytics -c "SELECT COUNT(DISTINCT channel_id) FROM analytics_results;"
```

## Примечания

- Импорт может занять время в зависимости от размера файла
- Пересчет similarity может занять много времени для больших баз (несколько часов)
- Рекомендуется запускать пересчет similarity в screen/tmux сессии
- После пересчета similarity бот будет готов к работе
