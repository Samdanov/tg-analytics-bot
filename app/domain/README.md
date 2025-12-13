# Domain Layer

**Бизнес-логика приложения, независимая от инфраструктуры.**

---

## 📁 Структура

```
domain/
├── __init__.py                  # Публичный API domain layer
├── README.md                    # Этот файл
├── exceptions.py                # Доменные исключения
├── value_objects.py             # Value Objects (ChannelIdentifier)
├── adapters.py                  # Адаптеры для интеграции
├── examples.py                  # Примеры использования
├── entities/                    # Доменные сущности
│   ├── __init__.py
│   ├── channel.py              # ChannelEntity
│   └── analysis.py             # AnalysisResult
└── services/                    # Доменные сервисы
    ├── __init__.py
    └── proxy_detector.py       # ProxyChannelDetector
```

---

## 🎯 Основные компоненты

### 1. **Value Objects**

#### `ChannelIdentifier`
Неизменяемый объект для работы с идентификаторами каналов (username или ID).

**Зачем нужен:**
- Инкапсулирует логику работы с username и ID
- Валидация при создании
- Единообразное преобразование для БД, отображения, файлов

**Пример:**
```python
from app.domain import ChannelIdentifier

# Из username
identifier = ChannelIdentifier.from_raw("@channel")
identifier.to_db_format()      # "channel"
identifier.to_display_format() # "@channel"
identifier.is_id_based          # False

# Из ID
identifier = ChannelIdentifier.from_raw("-1002508742544")
identifier.to_db_format()      # "id:-1002508742544"
identifier.to_display_format() # "ID: -1002508742544"
identifier.is_id_based          # True
```

---

### 2. **Entities**

#### `ChannelEntity`
Доменная модель канала с бизнес-логикой.

**Преимущества:**
- Инкапсулирует бизнес-правила
- Независима от БД (нет ORM)
- Легко тестировать

**Пример:**
```python
from app.domain import ChannelEntity, ChannelIdentifier

identifier = ChannelIdentifier.from_raw("@channel")
channel = ChannelEntity(
    identifier=identifier,
    title="Tech News",
    subscribers=10000,
    keywords=["tech", "news"]
)

# Бизнес-логика
channel.is_private      # False
channel.is_analyzed     # True
channel.update_metadata(subscribers=15000)
```

#### `AnalysisResult`
Результат анализа канала через LLM.

**Пример:**
```python
from app.domain import AnalysisResult

analysis = AnalysisResult(
    audience="IT-специалисты 25-40 лет",
    keywords=["python", "django"],
    tone="Профессиональный",
    source="llm",
    confidence=0.9
)

# Проверки
analysis.is_from_llm    # True
analysis.is_fallback    # False
analysis.has_keywords   # True
```

---

### 3. **Services**

#### `ProxyChannelDetector`
Определяет каналы-прокладки по их постам.

**Заменяет:** Логику из `workflow.py` (150+ строк)

**Преимущества:**
- Явные бизнес-правила
- Константы вместо магических чисел
- Легко тестировать

**Пример:**
```python
from app.domain import ProxyChannelDetector

detector = ProxyChannelDetector()
result = detector.detect(posts, exclude_username="current")

if result.is_proxy:
    print(f"Прокладка обнаружена: {result.reason}")
    for username, count in result.linked_channels:
        print(f"  @{username}: {count} упоминаний")
```

---

### 4. **Exceptions**

Доменные исключения для бизнес-логики.

```python
from app.domain import (
    DomainError,
    ChannelNotFoundError,
    InvalidChannelIdentifierError,
    ProxyChannelDetectedError,
)

try:
    identifier = ChannelIdentifier.from_raw("@ab")  # Слишком короткий
except InvalidChannelIdentifierError as e:
    print(f"Ошибка: {e}")  # "Invalid channel identifier: @ab (Username must be 3-32 characters...)"
```

---

## 🔄 Интеграция с существующим кодом

### Адаптеры

Файл `adapters.py` содержит функции-мосты для постепенной миграции:

```python
from app.domain.adapters import (
    parse_channel_identifier,
    create_callback_data_for_analysis,
    parse_callback_data_from_analysis,
    normalize_identifier_for_db,
    get_display_name,
)

# СТАРЫЙ КОД (было):
username = raw_value.strip().lstrip("@")
is_id_based = username.isdigit()

# НОВЫЙ КОД (стало):
identifier, title, is_id_based = parse_channel_identifier(raw_value)
```

---

## 🧪 Тестирование

Запусти примеры:

```bash
cd /home/alex/apps/tg-analytics-bot
source venv/bin/activate
python -m app.domain.examples
```

---

## 📈 План интеграции

### Этап 1: ✅ Создание domain layer (ЗАВЕРШЕНО)
- [x] Value Objects (ChannelIdentifier)
- [x] Entities (ChannelEntity, AnalysisResult)
- [x] Services (ProxyChannelDetector)
- [x] Exceptions
- [x] Adapters

### Этап 2: 🔄 Постепенная интеграция (СЛЕДУЮЩИЙ ШАГ)
1. Заменить ручную обработку username/ID на ChannelIdentifier
2. Использовать ProxyChannelDetector вместо встроенной логики
3. Обернуть результаты анализа в AnalysisResult

### Этап 3: Рефакторинг handlers
- Вынести логику из handlers в services
- Использовать domain entities

### Этап 4: DTO Layer (Pydantic schemas)
- Типизированные запросы/ответы
- Автовалидация

---

## 🎨 Принципы

1. **Независимость от инфраструктуры**
   - Нет импортов SQLAlchemy, aiogram, etc
   - Чистая бизнес-логика

2. **Тестируемость**
   - Легко мокировать
   - Нет побочных эффектов

3. **Явность**
   - Валидация при создании
   - Явные бизнес-правила
   - Типизация

4. **Обратная совместимость**
   - Старый код продолжает работать
   - Постепенная миграция
   - Адаптеры для совместимости

---

## 💡 Примеры использования

См. файл `examples.py` для детальных примеров всех компонентов.

---

## 🚀 Следующие шаги

После завершения интеграции domain layer:
- Добавить DTO layer (Pydantic schemas)
- Разделить Repository на отдельные классы
- Внедрить Dependency Injection
- Улучшить error handling

---

*Документация обновлена: 13 декабря 2025*

