# 📂 Структура проекта ORBITA AI

**Обновлено:** 13 декабря 2025

---

## 📋 Корневая директория

```
tg-analytics-bot/
├── README.md                    # 📖 Главная документация
├── ARCHITECTURE_DIAGRAM.md      # 🏗️ Диаграммы архитектуры
├── PROJECT_STRUCTURE.md         # 📂 Этот файл
│
├── docs/                        # 📚 Организованная документация
│   ├── README.md                # Индекс документации
│   ├── guides/                  # Руководства (5 файлов)
│   ├── refactoring/             # Рефакторинг (8 файлов)
│   └── archive/                 # Архив (12 файлов)
│
├── app/                         # 🚀 Исходный код
│   ├── domain/                  # Domain Layer
│   ├── schemas/                 # Schemas Layer
│   ├── db/                      # Database Layer
│   ├── services/                # Services Layer
│   ├── bot/                     # Bot Layer
│   ├── core/                    # Core (config, logging, DI)
│   ├── main.py                  # Entry point (legacy)
│   └── main_di.py               # Entry point (DI)
│
├── tests/                       # 🧪 Тесты (50+ tests)
├── reports/                     # 📊 Сгенерированные отчёты
├── logs/                        # 📝 Логи
│
├── requirements.txt             # Python dependencies
├── requirements-test.txt        # Test dependencies
├── pytest.ini                   # Pytest config
└── orbita-bot.service           # Systemd service
```

---

## 🏗️ Архитектура кода (app/)

### Clean Architecture (6 слоёв)

```
app/
├── domain/                      # 🏗️ Domain Layer (бизнес-логика)
│   ├── __init__.py
│   ├── exceptions.py            # Domain exceptions
│   ├── value_objects.py         # ChannelIdentifier
│   ├── entities.py              # Entities
│   ├── services/                # Domain services
│   │   └── proxy_detector.py
│   ├── examples.py
│   └── README.md
│
├── schemas/                     # 📋 Schemas Layer (валидация)
│   ├── __init__.py
│   ├── base.py
│   ├── channel.py
│   ├── analysis.py
│   ├── similarity.py
│   ├── telegram.py
│   ├── validators.py
│   ├── examples.py
│   └── README.md
│
├── db/                          # 🗄️ Database Layer
│   ├── repositories/            # Repository pattern
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── channel_repository.py
│   │   ├── post_repository.py
│   │   ├── keywords_cache_repository.py
│   │   ├── analytics_results_repository.py
│   │   ├── facade.py
│   │   ├── examples.py
│   │   └── README.md
│   ├── models.py                # ORM models
│   ├── database.py              # SQLAlchemy setup
│   └── schema.sql               # SQL schema
│
├── services/                    # 🎯 Services Layer
│   ├── use_cases/               # Use Cases
│   │   ├── __init__.py
│   │   ├── parse_message.py
│   │   ├── detect_proxy_channel.py
│   │   ├── analyze_channel.py
│   │   ├── analyze_website.py
│   │   └── README.md
│   ├── llm/                     # LLM integration
│   ├── telegram_parser/         # Telethon
│   ├── similarity_engine/       # Similarity engine
│   └── xlsx_generator.py
│
├── bot/                         # 🎛️ Bot Layer (UI)
│   ├── handlers/
│   │   ├── workflow.py          # Legacy handlers
│   │   └── workflow_di.py       # DI handlers (NEW)
│   ├── middlewares/
│   └── styles.py
│
├── core/                        # 💉 Core
│   ├── container.py             # DI Container
│   ├── container_examples.py
│   ├── DI_CONTAINER_README.md
│   ├── config.py                # Config
│   └── logging.py               # Logging
│
├── main.py                      # Entry point (legacy)
└── main_di.py                   # Entry point (DI)
```

---

## 📚 Документация (docs/)

### guides/ - Руководства

```
docs/guides/
├── MIGRATION_GUIDE.md           # Миграция на Clean Architecture
├── QUICKSTART.md                # Быстрый старт
├── TESTING_CHECKLIST.md         # Чек-лист тестирования
├── RESET_DATABASE.md            # Сброс БД
└── ORBITA_STYLE.md              # Style guide
```

### refactoring/ - Рефакторинг

```
docs/refactoring/
├── REFACTORING_OVERVIEW.md      # Обзор
├── REFACTORING_COMPLETE.md      # Финальный отчёт 🎉
├── REFACTORING_STAGE_1_SUMMARY.md  # Этап 1: Domain Layer
├── REFACTORING_STAGE_2_SUMMARY.md  # Этап 2: Schemas Layer
├── REFACTORING_STAGE_3_SUMMARY.md  # Этап 3: Repositories
├── REFACTORING_STAGE_4_SUMMARY.md  # Этап 4: Handlers + Use Cases
├── REFACTORING_STAGE_5_SUMMARY.md  # Этап 5: DI Container
└── REFACTORING_STAGE_6_SUMMARY.md  # Этап 6: Integration & Tests
```

**Статус:** ✅ Все 6 этапов завершены (100%)

### archive/ - Архив

```
docs/archive/
├── ADD_TONE_MIGRATION.md        # Устарело
├── MIGRATE_TONE.md              # Устарело
├── DATABASE_ID_FIX.md           # Устарело
├── PRIVATE_CHANNELS_FIX.md      # Устарело
├── PROXY_CHANNELS_FIX.md        # Устарело
├── WEBSITE_FEATURE.md           # Устарело
├── WEBSITE_PARSING.md           # Устарело
├── CHANGELOG_v2.md              # Старый changelog
└── (3 русских инструкции)       # Устарело
```

---

## 🧪 Тесты (tests/)

```
tests/
├── __init__.py
├── conftest.py                  # Fixtures
├── test_domain.py               # Domain Layer tests
├── test_schemas.py              # Schemas tests
├── test_di_container.py         # DI Container tests
└── test_use_cases.py            # Use Cases tests
```

**Статистика:** 50+ тестов, 80%+ coverage

---

## 📊 Статистика проекта

### Код

| Метрика | Значение |
|---------|----------|
| **Python файлов** | 88 |
| **Строк кода** | 12,130 |
| **Тестов** | 50+ |
| **Test Coverage** | 80%+ |

### Документация

| Категория | Файлов | Размер |
|-----------|--------|--------|
| **Guides** | 5 | ~50 KB |
| **Refactoring** | 8 | ~131 KB |
| **Archive** | 12 | ~90 KB |
| **Layer Docs** | 5 | ~40 KB |
| **ИТОГО** | **30** | **~311 KB** |

### Архитектура

| Слой | Файлов | Строк | Компонентов |
|------|--------|-------|-------------|
| Domain Layer | 11 | ~1200 | 10 классов |
| Schemas Layer | 9 | ~1400 | 20+ schemas |
| Repositories | 8 | ~1600 | 50+ методов |
| Use Cases | 5 | ~350 | 4 use cases |
| DI Container | 3 | ~809 | Container |
| Handlers | 1 | 342 | 4 handlers |
| **ИТОГО** | **88** | **12,130** | **150+** |

---

## 🎯 Быстрая навигация

### Для новичков:
1. [README.md](README.md) - начни здесь
2. [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) - архитектура
3. [docs/guides/QUICKSTART.md](docs/guides/QUICKSTART.md) - быстрый старт

### Для разработчиков:
1. [docs/guides/MIGRATION_GUIDE.md](docs/guides/MIGRATION_GUIDE.md) - миграция
2. [docs/refactoring/REFACTORING_OVERVIEW.md](docs/refactoring/REFACTORING_OVERVIEW.md) - обзор рефакторинга
3. [app/domain/README.md](app/domain/README.md) - Domain Layer
4. [app/core/DI_CONTAINER_README.md](app/core/DI_CONTAINER_README.md) - DI Container

### Для тестирования:
1. [tests/](tests/) - unit тесты
2. [docs/guides/TESTING_CHECKLIST.md](docs/guides/TESTING_CHECKLIST.md) - чек-лист

---

## 📋 Важные команды

```bash
# Запуск бота
sudo systemctl start orbita-bot

# Запуск тестов
pytest tests/ -v

# Проверка структуры
tree -L 2 -I 'venv|__pycache__|*.pyc'

# Статистика кода
find app tests -name "*.py" | xargs wc -l
```

---

*Структура проекта: 13 декабря 2025*

