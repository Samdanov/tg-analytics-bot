# 🚀 Migration Guide: Переход на новую архитектуру

**Пошаговое руководство по миграции с legacy кода на новую архитектуру.**

---

## 📋 Содержание

1. [Обзор изменений](#обзор-изменений)
2. [Стратегии миграции](#стратегии-миграции)
3. [Пошаговая миграция](#пошаговая-миграция)
4. [Примеры миграции](#примеры-миграции)
5. [Тестирование](#тестирование)
6. [Откат изменений](#откат-изменений)

---

## 📊 Обзор изменений

### Что было (legacy):
```
app/
├── db/
│   └── repo.py                 # 3 функции, Dict[str, Any]
├── bot/handlers/
│   └── workflow.py             # 481 строка, вся логика внутри
└── services/
    └── (разрозненные сервисы)
```

### Что стало (new):
```
app/
├── domain/                     # Бизнес-логика (11 файлов)
├── schemas/                    # Валидация данных (9 файлов)
├── db/repositories/            # Доступ к БД (8 файлов)
├── services/use_cases/         # Оркестрация (5 файлов)
├── core/container.py           # DI Container
└── bot/handlers/
    ├── workflow.py             # Старая версия
    ├── workflow_new.py         # Без DI
    └── workflow_di.py          # С DI (рекомендуется)
```

---

## 🎯 Стратегии миграции

### Стратегия 1: Постепенная миграция ⭐ (Рекомендуется)

**Подход:** Новый код использует новую архитектуру, старый остается.

**Преимущества:**
- ✅ Нет breaking changes
- ✅ Минимальный риск
- ✅ Можно откатить в любой момент
- ✅ Производство не страдает

**Недостатки:**
- ⚠️ Дублирование (временное)
- ⚠️ Две версии кода параллельно

**Для кого:** Production systems, большие проекты

---

### Стратегия 2: "Big Bang" миграция

**Подход:** Заменить всё сразу.

**Преимущества:**
- ✅ Чистый код сразу
- ✅ Нет дублирования
- ✅ Быстро

**Недостатки:**
- ❌ Высокий риск
- ❌ Сложно откатить
- ❌ Может сломать production

**Для кого:** Небольшие проекты, dev окружение

---

### Стратегия 3: Feature-based миграция

**Подход:** Мигрировать по фичам (сначала анализ каналов, потом сайты, etc).

**Преимущества:**
- ✅ Контролируемый риск
- ✅ Постепенное внедрение
- ✅ Легко тестировать

**Недостатки:**
- ⚠️ Требует времени
- ⚠️ Смешанная архитектура временно

**Для кого:** Средние проекты

---

## 📝 Пошаговая миграция (Рекомендуется)

### ШАГ 1: Включение DI handlers (безопасно)

**Текущее состояние:** Бот использует `workflow.py` (старый)

**Действие:** Переключиться на `workflow_di.py` (новый с DI)

```bash
# Вариант 1: Через переменную окружения (БЕЗОПАСНО)
export USE_DI_HANDLERS=true

# Вариант 2: Использовать main_di.py вместо main.py
python -m app.main_di
```

**Или в systemd service:**
```ini
# orbita-bot.service
[Service]
Environment="USE_DI_HANDLERS=true"
ExecStart=/home/alex/apps/tg-analytics-bot/venv/bin/python -m app.main_di
```

**Тестирование:**
1. Запустить бота локально с `USE_DI_HANDLERS=true`
2. Проверить основные функции (анализ канала, сайта)
3. Если всё ОК - деплоить на production

**Откат:**
```bash
# Если что-то пошло не так
export USE_DI_HANDLERS=false
# или вернуться к app.main
```

---

### ШАГ 2: Миграция кода на repositories (опционально)

**Цель:** Заменить вызовы `app.db.repo.py` на repositories.

**Где менять:**
- `app/services/usecases/channel_service.py`
- `app/services/workflow_pipeline.py`
- Другие сервисы, использующие `repo.py`

**До:**
```python
from app.db.repo import save_channel, save_posts

channel_id = await save_channel(channel_data)
await save_posts(channel_id, posts)
```

**После:**
```python
from app.db.repositories import get_repository_facade
from app.schemas import ChannelCreateSchema

repo = get_repository_facade()
channel = await repo.channels.upsert(ChannelCreateSchema(**channel_data))
await repo.posts.replace_posts(channel.id, posts)
```

**Тестирование:**
- Unit-тесты с моками
- Integration-тесты с реальной БД

---

### ШАГ 3: Добавление unit-тестов

**Действие:** Запустить тесты для проверки новой архитектуры.

```bash
cd /home/alex/apps/tg-analytics-bot
source venv/bin/activate

# Установить зависимости для тестов
pip install -r requirements-test.txt

# Запустить тесты
pytest tests/ -v

# Запустить конкретный тест
pytest tests/test_domain.py -v
pytest tests/test_schemas.py -v
pytest tests/test_di_container.py -v
pytest tests/test_use_cases.py -v
```

**Ожидаемый результат:**
- ✅ Все тесты проходят
- ✅ Coverage > 80%

---

### ШАГ 4: Cleanup старого кода (опционально)

**ВНИМАНИЕ:** Делать только после полной уверенности в новой архитектуре!

**Файлы для удаления:**
- `app/bot/handlers/workflow.py` (старый монолитный)
- `app/bot/handlers/workflow_old.py` (бэкап)
- `app/bot/handlers/workflow_new.py` (промежуточная версия)
- `app/db/repo.py` (старый repository)

**Оставить:**
- `app/bot/handlers/workflow_di.py` (финальная версия)
- Вся новая архитектура

---

## 💡 Примеры миграции

### Пример 1: Миграция handler

#### До (legacy):
```python
from app.db.repo import save_channel, get_channel_id_by_username
from app.core.config import config
from app.core.logging import get_logger

logger = get_logger(__name__)

@router.message(Command("analyze"))
async def analyze_handler(message: Message):
    # Вся логика внутри handler
    channel_data = {"username": "technews", ...}
    channel_id = await save_channel(channel_data)
    
    # ... 100+ строк логики ...
```

#### После (new):
```python
from app.core.container import get_container
from app.domain import ChannelIdentifier

@router.message(Command("analyze"))
async def analyze_handler(message: Message):
    # Получаем зависимости через DI
    container = get_container()
    analyze_uc = container.analyze_channel_uc
    logger = container.logger(__name__)
    
    # Вся логика в use case
    identifier = ChannelIdentifier.from_raw("@technews")
    report = await analyze_uc.execute(identifier, top_n=10)
    
    # Handler - только адаптер (<10 строк)
    await message.answer_document(report)
```

---

### Пример 2: Миграция service

#### До (legacy):
```python
async def analyze_channel(username: str):
    # Смешанная логика
    channel_data, posts, error = await get_channel_with_posts(username)
    channel_id = await save_channel(channel_data)
    await save_posts(channel_id, posts)
    
    result = await llm_analyze(channel_data, posts)
    await save_analysis(channel_id, result)
    
    # ... и т.д.
```

#### После (new):
```python
from app.core.container import get_container

async def analyze_channel(username: str):
    # Use case делает всё
    container = get_container()
    analyze_uc = container.analyze_channel_uc
    
    identifier = ChannelIdentifier.from_raw(username)
    report = await analyze_uc.execute(identifier, top_n=10)
    
    return report
```

---

### Пример 3: Миграция работы с БД

#### До (legacy):
```python
from app.db.repo import save_channel, get_channel_id_by_username

# Dict[str, Any]
channel_data = {"username": "technews", "title": "Tech News"}
channel_id = await save_channel(channel_data)

channel_id = await get_channel_id_by_username("technews")
```

#### После (new):
```python
from app.db.repositories import get_repository_facade
from app.schemas import ChannelCreateSchema

repo = get_repository_facade()

# Типизированные данные
channel_create = ChannelCreateSchema(
    identifier="@technews",
    title="Tech News"
)
channel = await repo.channels.upsert(channel_create)

channel = await repo.channels.get_by_username("technews")
```

---

## 🧪 Тестирование после миграции

### 1. Unit-тесты

```bash
# Запустить все unit-тесты
pytest tests/ -m unit -v

# Запустить конкретный модуль
pytest tests/test_domain.py -v
```

### 2. Smoke-тесты

```bash
# Проверить импорты
python -c "from app.domain import *"
python -c "from app.schemas import *"
python -c "from app.db.repositories import *"
python -c "from app.services.use_cases import *"

# Проверить DI
python -c "from app.core.container import get_container; c = get_container()"

# Проверить handlers
python -c "from app.bot.handlers.workflow_di import router"
```

### 3. Integration-тесты

```bash
# Запустить бота локально
USE_DI_HANDLERS=true python -m app.main_di

# Протестировать:
# 1. /start - команда старта
# 2. Отправить пост канала
# 3. Отправить ссылку на канал
# 4. Отправить ссылку на сайт
# 5. /health - проверка статуса
```

---

## 🔄 Откат изменений

### Если новая архитектура не работает:

#### Вариант 1: Переменная окружения
```bash
# Вернуться к старым handlers
export USE_DI_HANDLERS=false
python -m app.main_di

# Или использовать старый main.py
python -m app.main
```

#### Вариант 2: Git revert (полный откат)
```bash
# Откатить все изменения
git log --oneline  # Найти commit до рефакторинга
git revert <commit_hash>

# Или hard reset (ОСТОРОЖНО!)
git reset --hard <commit_hash>
```

#### Вариант 3: Удалить новые файлы
```bash
# Удалить новую архитектуру
rm -rf app/domain/
rm -rf app/schemas/
rm -rf app/db/repositories/
rm -rf app/services/use_cases/
rm app/core/container.py
rm app/bot/handlers/workflow_di.py

# Вернуться к старым файлам
mv app/bot/handlers/workflow_old.py app/bot/handlers/workflow.py
```

---

## ✅ Чек-лист миграции

### Перед началом:
- [ ] Сделать backup БД
- [ ] Создать git branch для миграции
- [ ] Запустить все существующие тесты
- [ ] Убедиться что production работает

### Во время миграции:
- [ ] Установить `requirements-test.txt`
- [ ] Запустить новые unit-тесты
- [ ] Протестировать локально с `USE_DI_HANDLERS=true`
- [ ] Проверить все основные функции
- [ ] Сравнить результаты (старый vs новый)

### После миграции:
- [ ] Деплой на production с `USE_DI_HANDLERS=true`
- [ ] Мониторинг логов (первые 24 часа)
- [ ] Проверка метрик (ошибки, время отклика)
- [ ] Если всё ОК - удалить старый код (опционально)

---

## 📈 Сравнение версий

### Версии handlers:

| Версия | Файл | Строк | Архитектура | Статус |
|--------|------|-------|-------------|--------|
| **Legacy** | workflow.py | 481 | Монолитная | ⚠️ Deprecated |
| **Refactored (no DI)** | workflow_new.py | 351 | Use Cases | ✅ OK |
| **Refactored (DI)** | workflow_di.py | 342 | Clean Architecture | ⭐ Recommended |

### Сравнение функциональности:

| Функция | Legacy | New (DI) | Улучшения |
|---------|--------|----------|-----------|
| Анализ канала | ✅ | ✅ | +Типизация, +Тесты |
| Анализ сайта | ✅ | ✅ | +Валидация |
| Прокладки | ✅ | ✅ | +Domain service |
| Ошибки | Базовый | ✅ | +Error boundaries |
| Тесты | ❌ | ✅ | Unit + Integration |

---

## 🚀 Быстрый старт (для нетерпеливых)

### Вариант 1: Только DI handlers (минимальная миграция)

```bash
cd /home/alex/apps/tg-analytics-bot

# 1. Использовать main_di.py с переменной окружения
export USE_DI_HANDLERS=true

# 2. Запустить
python -m app.main_di

# 3. Протестировать
# - Отправить пост канала
# - Проверить /health

# 4. Если OK - обновить systemd service
sudo systemctl edit orbita-bot.service
# Добавить:
# Environment="USE_DI_HANDLERS=true"
# ExecStart=.../python -m app.main_di

sudo systemctl restart orbita-bot
```

---

### Вариант 2: Полная миграция (экспертам)

```bash
cd /home/alex/apps/tg-analytics-bot

# 1. Backup
git checkout -b migration-full
git add .
git commit -m "Before full migration"

# 2. Заменить main.py
mv app/main.py app/main_legacy.py
mv app/main_di.py app/main.py

# 3. Обновить imports в main.py
# from app.bot.handlers.workflow import router  # Удалить
# from app.bot.handlers.workflow_di import router  # Добавить

# 4. Удалить старое (ОПЦИОНАЛЬНО!)
# rm app/bot/handlers/workflow.py
# rm app/db/repo.py

# 5. Тестировать
pytest tests/ -v
python -m app.main

# 6. Deploy
git add .
git commit -m "Migrated to new architecture"
git push
```

---

## 📋 Migration Checklist

### Phase 1: Preparation
- [x] ✅ Domain Layer создан
- [x] ✅ Schemas Layer создан
- [x] ✅ Repositories созданы
- [x] ✅ Use Cases созданы
- [x] ✅ DI Container создан
- [x] ✅ Handlers с DI созданы
- [ ] Unit-тесты написаны
- [ ] Integration-тесты написаны

### Phase 2: Integration
- [ ] `main_di.py` протестирован локально
- [ ] Smoke-тесты пройдены
- [ ] Все функции работают
- [ ] Performance не ухудшился

### Phase 3: Deployment
- [ ] Деплой на staging (если есть)
- [ ] Мониторинг 24 часа
- [ ] Деплой на production
- [ ] Мониторинг 7 дней

### Phase 4: Cleanup (optional)
- [ ] Удалить `workflow.py` (legacy)
- [ ] Удалить `workflow_old.py` (backup)
- [ ] Удалить `workflow_new.py` (intermediate)
- [ ] Удалить `repo.py` (legacy)
- [ ] Обновить документацию

---

## ⚠️ Потенциальные проблемы

### Проблема 1: Импорты не работают

**Симптом:**
```python
ImportError: cannot import name 'ChannelIdentifier' from 'app.domain'
```

**Решение:**
```bash
# Проверить PYTHONPATH
export PYTHONPATH=/home/alex/apps/tg-analytics-bot

# Переустановить в dev mode
pip install -e .
```

---

### Проблема 2: БД конфликты

**Симптом:**
```
IntegrityError: duplicate key value violates unique constraint
```

**Решение:**
- Repositories используют UPSERT (безопасно)
- Если проблема - откатиться на `workflow.py`

---

### Проблема 3: Performance деградация

**Симптом:** Анализ работает медленнее.

**Решение:**
- DI добавляет <1ms overhead (незначительно)
- Проверить логи на таймауты
- Если проблема - вернуться к legacy

---

## 📊 Мониторинг после миграции

### Что проверять:

1. **Логи:**
   ```bash
   tail -f /home/alex/apps/tg-analytics-bot/logs/bot.log
   
   # Искать:
   # - "Using DI handlers (workflow_di.py)" - подтверждение DI
   # - Ошибки импортов
   # - Исключения
   ```

2. **Метрики:**
   - Время отклика (не должно увеличиться)
   - Количество ошибок (не должно увеличиться)
   - Использование памяти (может немного вырасти)

3. **Функциональность:**
   - Анализ каналов работает
   - Анализ сайтов работает
   - Определение прокладок работает
   - Отчеты генерируются

---

## 🆘 Контакты для помощи

### Если что-то пошло не так:

1. **Проверить логи:**
   ```bash
   tail -100 /home/alex/apps/tg-analytics-bot/logs/bot-error.log
   ```

2. **Откатиться:**
   ```bash
   export USE_DI_HANDLERS=false
   sudo systemctl restart orbita-bot
   ```

3. **Создать issue:**
   - Приложить логи
   - Описать проблему
   - Указать версию

---

## 📚 Дополнительные ресурсы

### Документация:
- [REFACTORING_OVERVIEW.md](REFACTORING_OVERVIEW.md) - общий обзор
- [app/domain/README.md](app/domain/README.md) - Domain Layer
- [app/schemas/README.md](app/schemas/README.md) - Schemas Layer
- [app/db/repositories/README.md](app/db/repositories/README.md) - Repositories
- [app/services/use_cases/README.md](app/services/use_cases/README.md) - Use Cases
- [app/core/DI_CONTAINER_README.md](app/core/DI_CONTAINER_README.md) - DI Container

### Примеры:
- [app/domain/examples.py](app/domain/examples.py)
- [app/schemas/examples.py](app/schemas/examples.py)
- [app/db/repositories/examples.py](app/db/repositories/examples.py)
- [app/core/container_examples.py](app/core/container_examples.py)

---

## ✅ Успешная миграция = Production Ready

**Признаки успешной миграции:**
- ✅ Бот работает без ошибок 7 дней
- ✅ Все unit-тесты проходят
- ✅ Performance не ухудшился
- ✅ Код стал читаемее
- ✅ Легко добавлять новые фичи

**Поздравляем! 🎉**

---

*Migration Guide создан: 13 декабря 2025*

