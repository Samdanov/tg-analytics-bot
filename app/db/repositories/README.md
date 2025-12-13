## Repositories Layer

**Слой доступа к данным с чистой архитектурой.**

Заменяет монолитный `repo.py` на отдельные репозитории по принципу Single Responsibility.

---

## 📁 Структура

```
repositories/
├── __init__.py                           # Публичный API
├── README.md                             # Этот файл
├── base.py                               # BaseRepository (абстрактный)
├── channel_repository.py                 # ChannelRepository
├── post_repository.py                    # PostRepository
├── keywords_cache_repository.py          # KeywordsCacheRepository
├── analytics_results_repository.py       # AnalyticsResultsRepository
├── facade.py                             # RepositoryFacade (unified access)
└── examples.py                           # Примеры использования
```

---

## 🎯 Основные компоненты

### 1. **BaseRepository** (абстрактный)

Базовый класс для всех репозиториев с CRUD операциями.

**Методы:**
- `get_by_id(id)` - получить по ID
- `get_all(limit, offset)` - получить все
- `create(**kwargs)` - создать
- `update(id, **kwargs)` - обновить
- `delete(id)` - удалить
- `count()` - подсчитать количество
- `exists(id)` - проверить существование

**Generic тип:** Поддерживает любую SQLAlchemy модель

```python
class ChannelRepository(BaseRepository[Channel]):
    def __init__(self):
        super().__init__(Channel)
```

---

### 2. **ChannelRepository**

Репозиторий для работы с каналами.

**Специфичные методы:**
- `get_by_username(username)` - поиск по username
- `get_by_identifier(identifier)` - поиск через domain.ChannelIdentifier
- `upsert(data)` - создать или обновить канал
- `update_metadata(channel_id, update_data)` - обновить метаданные
- `update_keywords(channel_id, keywords)` - обновить keywords
- `get_with_keywords(limit, min_keywords)` - получить каналы с keywords
- `search_by_title(search_term)` - поиск по названию
- `get_recently_updated(limit)` - недавно обновленные
- `to_schema(channel)` - преобразование в Pydantic schema

**Пример:**
```python
from app.db.repositories import ChannelRepository
from app.schemas import ChannelCreateSchema

repo = ChannelRepository()

# UPSERT канала
data = ChannelCreateSchema(
    identifier="@technews",
    title="Tech News",
    subscribers=10000
)
channel = await repo.upsert(data)

# Поиск
channel = await repo.get_by_username("technews")

# Преобразование в schema
schema = repo.to_schema(channel)
```

---

### 3. **PostRepository**

Репозиторий для работы с постами.

**Специфичные методы:**
- `get_by_channel(channel_id, limit, offset)` - посты канала
- `replace_posts(channel_id, posts_data)` - заменить все посты
- `count_by_channel(channel_id)` - количество постов
- `get_posts_stats(channel_id)` - статистика (avg views, forwards)
- `delete_by_channel(channel_id)` - удалить все посты канала
- `get_posts_with_text(channel_id, min_length)` - посты с текстом

**Пример:**
```python
from app.db.repositories import PostRepository

repo = PostRepository()

# Замена постов
posts_data = [
    {"date": datetime.utcnow(), "views": 100, "text": "Post 1"},
    {"date": datetime.utcnow(), "views": 200, "text": "Post 2"},
]
count = await repo.replace_posts(channel_id, posts_data)

# Статистика
stats = await repo.get_posts_stats(channel_id)
print(f"Avg views: {stats['avg_views']}")
```

---

### 4. **KeywordsCacheRepository**

Репозиторий для работы с кешем keywords (результаты LLM).

**Специфичные методы:**
- `get_by_channel_id(channel_id)` - получить кеш
- `upsert_analysis(channel_id, analysis)` - сохранить результат LLM
- `get_keywords_list(channel_id)` - получить список keywords
- `to_schema(cache)` - преобразование в Pydantic schema

**Пример:**
```python
from app.db.repositories import KeywordsCacheRepository
from app.schemas import AnalysisResultSchema

repo = KeywordsCacheRepository()

# Сохранение анализа
analysis = AnalysisResultSchema(
    audience="IT specialists",
    keywords=["python", "django"],
    tone="Professional"
)
cache = await repo.upsert_analysis(channel_id, analysis)

# Получение keywords
keywords = await repo.get_keywords_list(channel_id)
```

---

### 5. **AnalyticsResultsRepository**

Репозиторий для работы с результатами similarity.

**Специфичные методы:**
- `get_by_channel_id(channel_id)` - получить результаты
- `upsert_results(channel_id, similar_channels)` - сохранить
- `get_similar_channels(channel_id, limit)` - список похожих
- `get_top_similar(channel_id, top_n)` - топ-N похожих
- `has_results(channel_id)` - есть ли результаты
- `delete_by_channel(channel_id)` - удалить результаты

**Пример:**
```python
from app.db.repositories import AnalyticsResultsRepository

repo = AnalyticsResultsRepository()

# Сохранение результатов
similar = [
    (123, 0.95),  # (channel_id, score)
    (456, 0.85),
    (789, 0.75),
]
await repo.upsert_results(target_channel_id, similar)

# Получение топ-N
top_10 = await repo.get_top_similar(target_channel_id, top_n=10)
```

---

### 6. **RepositoryFacade** (Unified Access)

Унифицированный интерфейс для доступа ко всем репозиториям.

**Паттерн Facade** упрощает работу с множественными репозиториями.

**Преимущества:**
- Единая точка входа
- Упрощенный DI (inject facade вместо 4 репозиториев)
- High-level методы

**Пример:**
```python
from app.db.repositories import RepositoryFacade, get_repository_facade

# Вариант 1: Создание
facade = RepositoryFacade()

# Вариант 2: Singleton
facade = get_repository_facade()

# Доступ к репозиториям
channel = await facade.channels.get_by_username("technews")
posts = await facade.posts.get_by_channel(channel.id)
keywords = await facade.keywords.get_keywords_list(channel.id)
similar = await facade.analytics.get_top_similar(channel.id, top_n=10)

# High-level метод (комбинация нескольких операций)
full_info = await facade.get_channel_full_info("technews")
# Returns: {channel, posts, posts_stats, keywords, similar_channels}

# Статистика БД
stats = await facade.get_statistics()
```

---

## 🔄 Миграция со старого repo.py

### До (старый код):
```python
from app.db.repo import save_channel, save_posts, get_channel_id_by_username

# Разрозненные функции
channel_id = await save_channel(channel_data)
await save_posts(channel_id, posts)
channel_id = await get_channel_id_by_username(username)
```

### После (новый код):
```python
from app.db.repositories import get_repository_facade
from app.schemas import ChannelCreateSchema

repo = get_repository_facade()

# Unified API
channel = await repo.channels.upsert(ChannelCreateSchema(**channel_data))
await repo.posts.replace_posts(channel.id, posts)
channel = await repo.channels.get_by_username(username)
```

---

## ✅ Преимущества новой архитектуры

### 1. **Single Responsibility Principle**
- Каждый репозиторий отвечает за свою сущность
- Легче поддерживать
- Легче тестировать

### 2. **Типобезопасность**
- Generic типы (BaseRepository[Channel])
- Возврат типизированных моделей
- IDE автодополнение

### 3. **Интеграция со Schemas**
- Методы `to_schema()` для преобразования ORM → Pydantic
- Валидация через Pydantic schemas
- Типизированные входные данные

### 4. **Тестируемость**
- Легко мокировать отдельные репозитории
- Можно заменить facade для тестов
- Нет глобального состояния

### 5. **Расширяемость**
- Легко добавить новый репозиторий
- Facade скрывает сложность
- Возможность замены хранилища

---

## 🧪 Тестирование

Запусти примеры:

```bash
cd /home/alex/apps/tg-analytics-bot
source venv/bin/activate
PYTHONPATH=/home/alex/apps/tg-analytics-bot python -m app.db.repositories.examples
```

**Примечание:** Для работы примеров нужна БД с данными.

---

## 📊 Сравнение с repo.py

| Аспект | repo.py (старое) | repositories/ (новое) |
|--------|------------------|----------------------|
| Файлов | 1 | 7 |
| Строк на файл | 117 | ~100-200 |
| Ответственность | Все операции | Одна сущность |
| Типизация | Частичная | Полная |
| Тестируемость | Сложно | Легко |
| Расширяемость | Сложно | Легко |
| Schemas | Нет | Да |

---

## 🔄 Обратная совместимость

✅ **Старый `repo.py` продолжает работать**
- Repositories добавлены параллельно
- Можно мигрировать постепенно
- Нет breaking changes

---

## 🚀 Использование в коде

### В handlers:
```python
from app.db.repositories import get_repository_facade

@router.message(Command("info"))
async def info_handler(message: Message):
    repo = get_repository_facade()
    
    channel = await repo.channels.get_by_username("technews")
    if not channel:
        await message.answer("Channel not found")
        return
    
    schema = repo.channels.to_schema(channel)
    await message.answer(f"Channel: {schema.display_name}")
```

### В use cases:
```python
from app.db.repositories import RepositoryFacade

class ChannelAnalyzer:
    def __init__(self, repo: RepositoryFacade):
        self.repo = repo
    
    async def analyze(self, username: str):
        channel = await self.repo.channels.get_by_username(username)
        posts = await self.repo.posts.get_by_channel(channel.id)
        # ... анализ ...
        await self.repo.keywords.upsert_analysis(channel.id, analysis)
```

---

## 💡 Best Practices

1. **Используй Facade для сложных операций**
   ```python
   facade = get_repository_facade()
   full_info = await facade.get_channel_full_info(username)
   ```

2. **Используй specific repositories для простых операций**
   ```python
   channel_repo = ChannelRepository()
   channel = await channel_repo.get_by_username(username)
   ```

3. **Преобразуй в schemas для передачи между слоями**
   ```python
   schema = channel_repo.to_schema(channel)
   return schema  # Типизированный ответ
   ```

4. **Используй domain objects для валидации**
   ```python
   identifier = ChannelIdentifier.from_raw(raw_username)
   channel = await repo.get_by_identifier(identifier)
   ```

---

## 📈 Следующие шаги

После завершения интеграции repositories:
- Заменить прямые вызовы `repo.py` на repositories
- Использовать schemas для типизации
- Добавить unit-тесты
- Внедрить Dependency Injection

---

*Документация обновлена: 13 декабря 2025*

