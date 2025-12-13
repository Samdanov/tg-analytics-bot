# 📚 Документация проекта ORBITA AI

Организованная документация проекта по категориям.

---

## 📋 Оглавление

### 🚀 Guides (Руководства)

Практические руководства для разработчиков:

| Документ | Описание |
|----------|----------|
| [MIGRATION_GUIDE.md](guides/MIGRATION_GUIDE.md) | Руководство по миграции на Clean Architecture |
| [QUICKSTART.md](guides/QUICKSTART.md) | Быстрый старт для новых разработчиков |
| [TESTING_CHECKLIST.md](guides/TESTING_CHECKLIST.md) | Чек-лист тестирования |
| [RESET_DATABASE.md](guides/RESET_DATABASE.md) | Сброс и пересоздание БД |
| [ORBITA_STYLE.md](guides/ORBITA_STYLE.md) | Style guide проекта |

### 🏗️ Refactoring (Рефакторинг)

Документация по рефакторингу проекта в Clean Architecture:

| Документ | Описание |
|----------|----------|
| [REFACTORING_OVERVIEW.md](refactoring/REFACTORING_OVERVIEW.md) | Общий обзор рефакторинга |
| [REFACTORING_COMPLETE.md](refactoring/REFACTORING_COMPLETE.md) | Финальный отчёт (Achievement Unlocked!) |
| [REFACTORING_STAGE_1_SUMMARY.md](refactoring/REFACTORING_STAGE_1_SUMMARY.md) | Этап 1: Domain Layer |
| [REFACTORING_STAGE_2_SUMMARY.md](refactoring/REFACTORING_STAGE_2_SUMMARY.md) | Этап 2: Schemas Layer |
| [REFACTORING_STAGE_3_SUMMARY.md](refactoring/REFACTORING_STAGE_3_SUMMARY.md) | Этап 3: Repositories |
| [REFACTORING_STAGE_4_SUMMARY.md](refactoring/REFACTORING_STAGE_4_SUMMARY.md) | Этап 4: Handlers + Use Cases |
| [REFACTORING_STAGE_5_SUMMARY.md](refactoring/REFACTORING_STAGE_5_SUMMARY.md) | Этап 5: DI Container |
| [REFACTORING_STAGE_6_SUMMARY.md](refactoring/REFACTORING_STAGE_6_SUMMARY.md) | Этап 6: Integration & Tests |

**Статус:** ✅ Все 6 этапов завершены (100%)

### 📦 Archive (Архив)

Устаревшие документы (оставлены для истории):

| Документ | Описание |
|----------|----------|
| [ADD_TONE_MIGRATION.md](archive/ADD_TONE_MIGRATION.md) | Миграция tone (устарело) |
| [MIGRATE_TONE.md](archive/MIGRATE_TONE.md) | Миграция tone v2 (устарело) |
| [DATABASE_ID_FIX.md](archive/DATABASE_ID_FIX.md) | Исправление ID (устарело) |
| [PRIVATE_CHANNELS_FIX.md](archive/PRIVATE_CHANNELS_FIX.md) | Приватные каналы (устарело) |
| [PROXY_CHANNELS_FIX.md](archive/PROXY_CHANNELS_FIX.md) | Каналы-прокладки (устарело) |
| [WEBSITE_FEATURE.md](archive/WEBSITE_FEATURE.md) | Фича сайтов (устарело) |
| [WEBSITE_PARSING.md](archive/WEBSITE_PARSING.md) | Парсинг сайтов (устарело) |
| [CHANGELOG_v2.md](archive/CHANGELOG_v2.md) | Старый changelog |
| Русские инструкции | 3 файла (устарело) |

---

## 🔍 Быстрая навигация

### Для новых разработчиков:
1. 📖 [README.md](../README.md) - начни здесь
2. 🚀 [QUICKSTART.md](guides/QUICKSTART.md) - быстрый старт
3. 🏗️ [ARCHITECTURE_DIAGRAM.md](../ARCHITECTURE_DIAGRAM.md) - архитектура

### Для миграции на новую архитектуру:
1. 📋 [MIGRATION_GUIDE.md](guides/MIGRATION_GUIDE.md) - пошаговое руководство
2. 📊 [REFACTORING_OVERVIEW.md](refactoring/REFACTORING_OVERVIEW.md) - обзор изменений
3. 🎉 [REFACTORING_COMPLETE.md](refactoring/REFACTORING_COMPLETE.md) - что получилось

### Документация по слоям:
- [Domain Layer](../app/domain/README.md) - бизнес-логика
- [Schemas Layer](../app/schemas/README.md) - валидация данных
- [Repositories](../app/db/repositories/README.md) - доступ к БД
- [Use Cases](../app/services/use_cases/README.md) - оркестрация
- [DI Container](../app/core/DI_CONTAINER_README.md) - зависимости

---

## 📊 Статистика документации

| Категория | Файлов | Размер |
|-----------|--------|--------|
| **Guides** | 5 | ~50 KB |
| **Refactoring** | 8 | ~131 KB |
| **Archive** | 12 | ~90 KB |
| **Layer Docs** | 5 | ~40 KB |
| **ИТОГО** | **30** | **~311 KB** |

---

## 🔄 История изменений

### 13 декабря 2025
- ✅ Организована вся документация по категориям
- ✅ Создана структура docs/{guides,refactoring,archive}
- ✅ Удалены временные файлы
- ✅ Оставлены только ключевые файлы в корне

### Ранее
- Завершён рефакторинг в Clean Architecture (6 этапов)
- Создано 30 markdown файлов документации
- 88 Python файлов, 12,130 строк кода
- 50+ unit-тестов, 80%+ coverage

---

*Документация организована: 13 декабря 2025*

