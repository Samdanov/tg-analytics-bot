# Schemas Layer (DTO)

**Pydantic models для валидации и сериализации данных.**

Заменяют `Dict[str, Any]` на типизированные, валидируемые модели.

---

## 📁 Структура

```
schemas/
├── __init__.py          # Публичный API
├── README.md            # Этот файл
├── base.py              # Базовые классы
├── channel.py           # Channel schemas
├── analysis.py          # Analysis schemas
├── similarity.py        # Similarity schemas
├── telegram.py          # Telegram-специфичные schemas
├── validators.py        # Кастомные валидаторы
└── examples.py          # Примеры использования
```

---

## 🎯 Основные компоненты

### 1. **Base Schemas**

#### `BaseSchema`
Базовый класс для всех schemas с общими настройками.

```python
from app.schemas import BaseSchema

class MySchema(BaseSchema):
    name: str
    age: int
```

#### `SuccessResponse` / `ErrorResponse`
Стандартные ответы для унификации API.

```python
from app.schemas import SuccessResponse, ErrorResponse

# Успех
success = SuccessResponse(
    message="Operation completed",
    data={"result": "ok"}
)

# Ошибка
error = ErrorResponse(
    error="ValidationError",
    message="Invalid data provided",
    details={"field": "username"}
)
```

---

### 2. **Channel Schemas**

Модели для работы с каналами.

#### `ChannelIdentifierSchema`
Валидация идентификатора канала (интеграция с domain layer).

```python
from app.schemas import ChannelIdentifierSchema

# Валидация
identifier = ChannelIdentifierSchema(raw_value="@channel")

# Преобразование в domain object
domain_id = identifier.to_domain()
```

#### `ChannelCreateSchema`
Создание нового канала.

```python
from app.schemas import ChannelCreateSchema

channel = ChannelCreateSchema(
    identifier="@technews",
    title="Tech News",
    description="Latest tech news",
    subscribers=10000
)
```

#### `ChannelResponseSchema`
Ответ с данными канала.

```python
from app.schemas import ChannelResponseSchema

response = ChannelResponseSchema(
    id=123,
    identifier="technews",
    is_id_based=False,
    title="Tech News",
    subscribers=10000,
    keywords=["tech", "news"]
)

# Computed properties
display_name = response.display_name  # "@technews"
is_analyzed = response.is_analyzed    # True
```

#### `ChannelUpdateSchema`
Partial update канала.

```python
from app.schemas import ChannelUpdateSchema

update = ChannelUpdateSchema(
    subscribers=15000,
    keywords=["technology", "gadgets"]
)

# Только измененные поля
data = update.model_dump(exclude_none=True)
```

---

### 3. **Analysis Schemas**

Модели для LLM-анализа.

#### `AnalysisResultSchema`
Результат анализа от LLM.

```python
from app.schemas import AnalysisResultSchema

analysis = AnalysisResultSchema(
    audience="IT-специалисты 25-40 лет",
    keywords=["python", "django", "backend"],
    tone="Профессиональный",
    source="llm",
    confidence=0.9
)

# Properties
is_from_llm = analysis.is_from_llm      # True
is_fallback = analysis.is_fallback      # False
has_keywords = analysis.has_keywords    # True
```

#### `AnalysisResponseSchema`
Полный ответ с результатами анализа.

```python
from app.schemas import AnalysisResponseSchema

response = AnalysisResponseSchema(
    channel_id=123,
    identifier="technews",
    is_id_based=False,
    title="Tech News",
    subscribers=10000,
    analysis=analysis,
    analyzed_posts=50,
    analysis_duration_ms=5000
)
```

---

### 4. **Similarity Schemas**

Модели для поиска похожих каналов.

#### `SimilarityRequestSchema`
Запрос на поиск похожих.

```python
from app.schemas import SimilarityRequestSchema

request = SimilarityRequestSchema(
    identifier="@technews",
    top_n=10,
    min_score=0.5
)
```

#### `SimilarChannelSchema`
Один похожий канал.

```python
from app.schemas import SimilarChannelSchema

similar = SimilarChannelSchema(
    channel_id=456,
    identifier="devnews",
    is_id_based=False,
    title="Dev News",
    subscribers=8000,
    keywords=["python", "javascript"],
    score=0.85,
    common_keywords=["python"]
)

# Properties
display_name = similar.display_name          # "@devnews"
relevance_percent = similar.relevance_percent  # 85.0
telegram_link = similar.telegram_link          # "https://t.me/devnews"
```

#### `SimilarityResultSchema`
Результат поиска похожих.

```python
from app.schemas import SimilarityResultSchema

result = SimilarityResultSchema(
    target_channel_id=123,
    target_identifier="technews",
    target_keywords=["python", "django"],
    similar_channels=[similar],
    total_found=50
)

# Properties
has_results = result.has_results      # True
avg_score = result.avg_score          # 0.85
top_3 = result.top_3_channels         # Топ-3 канала
```

---

### 5. **Telegram Schemas**

Модели для Telegram-специфичных данных.

#### `CallbackDataSchema`
Парсинг callback_data от inline кнопок.

```python
from app.schemas import CallbackDataSchema

# Username callback
callback1 = CallbackDataSchema.from_callback_string("analyze:technews:10")
callback1.to_callback_string()  # "analyze:technews:10"

# ID callback
callback2 = CallbackDataSchema.from_callback_string("analyze:id:-1002508742544:25")
callback2.to_callback_string()  # "analyze:id:-1002508742544:25"

# Website callback
callback3 = CallbackDataSchema.from_callback_string("analyze_website|https://example.com|50")
callback3.to_callback_string()  # "analyze_website|https%3A%2F%2Fexample.com|50"
```

#### `ChannelInfoSchema`
Информация о канале из Telegram API.

```python
from app.schemas import ChannelInfoSchema

channel_info = ChannelInfoSchema(
    id=-1002508742544,
    username="technews",
    title="Tech News",
    about="Latest tech news",
    participants_count=10000
)

# Properties
is_private = channel_info.is_private              # False
identifier_for_db = channel_info.identifier_for_db  # "technews"
```

---

### 6. **Custom Validators**

Переиспользуемые валидаторы.

```python
from app.schemas.validators import (
    validate_telegram_username,
    validate_keywords_list,
    validate_score,
)

# Валидация username
username = validate_telegram_username("@technews")  # "technews"

# Очистка keywords
keywords = validate_keywords_list(["  python  ", "", "django", "python"])  
# ["python", "django"]

# Валидация score
score = validate_score(0.8567)  # 0.8567 (rounded to 4 decimal places)
```

---

## 🧪 Примеры использования

### Валидация данных из dict

```python
from app.schemas import ChannelInfoSchema

# Данные из внешнего источника
raw_data = {
    "id": -1002508742544,
    "username": "technews",
    "title": "Tech News",
    "participants_count": 10000
}

# Валидация и преобразование
try:
    validated = ChannelInfoSchema(**raw_data)
    print(f"✓ Valid data: {validated.identifier_for_db}")
except ValueError as e:
    print(f"✗ Validation error: {e}")
```

### Сериализация в dict/JSON

```python
from app.schemas import ChannelResponseSchema

channel = ChannelResponseSchema(...)

# В dict
data = channel.model_dump()

# В JSON
json_str = channel.model_dump_json()

# Только измененные поля
partial = channel.model_dump(exclude_none=True)
```

### Создание из ORM модели

```python
from app.schemas import ChannelResponseSchema
from app.db.models import Channel

# Получаем из БД
channel_orm = session.query(Channel).first()

# Преобразуем в schema
channel_schema = ChannelResponseSchema.model_validate(channel_orm)
```

---

## 🔄 Интеграция с существующим кодом

### До (старый код):
```python
# Возвращаем dict
def get_channel_data(username: str) -> Dict[str, Any]:
    return {
        "id": 123,
        "username": username,
        "title": "Some Title",
        # ... нет валидации, легко ошибиться
    }
```

### После (новый код):
```python
from app.schemas import ChannelResponseSchema

def get_channel_data(username: str) -> ChannelResponseSchema:
    # Автоматическая валидация при создании
    return ChannelResponseSchema(
        id=123,
        identifier=username,
        is_id_based=False,
        title="Some Title",
        subscribers=10000
    )
```

---

## ✅ Преимущества

1. **Типобезопасность**
   - IDE автодополнение
   - Статический анализ типов
   - Меньше ошибок во время выполнения

2. **Автоматическая валидация**
   - Проверка типов при создании
   - Кастомные валидаторы
   - Понятные ошибки

3. **Сериализация/Десериализация**
   - Автоматическое преобразование в dict/JSON
   - Работа с ORM моделями
   - Alias для полей

4. **Документация**
   - Field descriptions
   - Examples в schema
   - Автогенерация OpenAPI schemas

5. **Читаемость**
   - Явные модели данных
   - Computed properties
   - Самодокументирующийся код

---

## 🧪 Тестирование

Запусти примеры:

```bash
cd /home/alex/apps/tg-analytics-bot
source venv/bin/activate
python -m app.schemas.examples
```

---

## 📈 Статистика

| Метрика | Значение |
|---------|----------|
| Файлов | 8 |
| Schemas | 20+ |
| Validators | 7 |
| Примеров | 6 |
| Строк кода | ~1400 |

---

## 🚀 Следующие шаги

1. **Интеграция в handlers**
   - Использовать schemas вместо dict
   - Валидация входных данных

2. **Интеграция в repository**
   - Преобразование ORM → schemas
   - Типизированные ответы

3. **Интеграция в use cases**
   - Типизированные параметры
   - Валидация бизнес-правил

---

*Документация обновлена: 13 декабря 2025*

