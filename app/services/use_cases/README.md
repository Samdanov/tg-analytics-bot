# Use Cases Layer

**Бизнес-логика приложения, организованная в виде use cases.**

Каждый use case представляет собой отдельную бизнес-операцию.

---

## 📁 Структура

```
use_cases/
├── __init__.py                   # Публичный API
├── README.md                     # Этот файл
├── parse_message.py              # MessageParserService
├── detect_proxy_channel.py       # DetectProxyChannelUseCase
├── analyze_channel.py            # AnalyzeChannelUseCase
└── analyze_website.py            # AnalyzeWebsiteUseCase
```

---

## 🎯 Компоненты

### 1. **MessageParserService**

Сервис для парсинга Telegram сообщений и извлечения информации.

**Возможности:**
- Извлечение информации о канале (username, ID, forwarded)
- Извлечение веб-сайтов из текста
- Определение типа контента (channel/website)
- Интеграция с domain.ChannelIdentifier

**Пример:**
```python
from app.services.use_cases import MessageParserService

parser = MessageParserService()

# Извлечение канала
channel_info = parser.extract_channel(message)
if channel_info:
    print(f"Channel: {channel_info.identifier.to_display_format()}")
    print(f"Title: {channel_info.title}")

# Извлечение сайта
website_info = parser.extract_website(message)
if website_info:
    print(f"URL: {website_info.url}")

# Автоопределение типа
content_type, content_info = parser.detect_content_type(message)
if content_type == "channel":
    # Обработка канала
elif content_type == "website":
    # Обработка сайта
```

---

### 2. **DetectProxyChannelUseCase**

Use case для определения каналов-прокладок (ad-forwarding channels).

**Возможности:**
- Анализ постов на наличие упоминаний других каналов
- Подсчет среднего размера текста
- Определение доли постов со ссылками
- Интеграция с domain.ProxyChannelDetector

**Пример:**
```python
from app.services.use_cases import DetectProxyChannelUseCase

detect_uc = DetectProxyChannelUseCase(
    min_linked_channels=3,
    max_avg_text_length=100,
    min_link_posts_ratio=0.5
)

result = await detect_uc.execute(
    posts=channel_posts,
    exclude_username="current_channel"
)

if result.is_proxy:
    print(f"Proxy detected!")
    print(f"Linked channels: {result.linked_channels}")
    print(f"Avg text length: {result.avg_text_length}")
    print(f"Reason: {result.reason}")
```

---

### 3. **AnalyzeChannelUseCase**

Use case для полного анализа Telegram канала.

**Процесс:**
1. Получение данных через Telethon
2. Сохранение в БД (repositories)
3. LLM-анализ (keywords, audience, tone)
4. Расчет похожих каналов (similarity)
5. Генерация XLSX отчета

**Пример:**
```python
from app.services.use_cases import AnalyzeChannelUseCase
from app.domain import ChannelIdentifier

analyze_uc = AnalyzeChannelUseCase()

identifier = ChannelIdentifier.from_raw("@technews")

report_path = await analyze_uc.execute(
    identifier=identifier,
    top_n=10
)

print(f"Report generated: {report_path}")
```

**Использует:**
- `RepositoryFacade` - для работы с БД
- `get_channel_with_posts` - для получения данных
- `analyze_channel` - для LLM анализа
- `calculate_similarity_for_channel` - для similarity
- `generate_similar_channels_xlsx` - для отчета

---

### 4. **AnalyzeWebsiteUseCase**

Use case для анализа веб-сайтов и поиска похожих каналов.

**Процесс:**
1. Парсинг контента сайта
2. LLM-анализ контента
3. Поиск похожих каналов по keywords
4. Генерация XLSX отчета

**Пример:**
```python
from app.services.use_cases import AnalyzeWebsiteUseCase

analyze_uc = AnalyzeWebsiteUseCase()

report_path, analysis_result = await analyze_uc.execute(
    url="https://example.com",
    top_n=10
)

print(f"Report: {report_path}")
print(f"Keywords: {analysis_result['keywords']}")
```

---

## 🔄 Интеграция с архитектурой

### Use Cases используют:

**Domain Layer:**
- `ChannelIdentifier` - валидация и нормализация идентификаторов
- `ProxyChannelDetector` - определение прокладок

**Schemas Layer:**
- `ChannelCreateSchema` - валидация данных для создания
- `AnalysisResultSchema` - валидация результатов LLM

**Repositories Layer:**
- `RepositoryFacade` - унифицированный доступ к БД
- `ChannelRepository`, `PostRepository`, etc.

---

## 📊 Преимущества Use Cases

### 1. **Separation of Concerns**
- Бизнес-логика отделена от handlers
- Легко переиспользовать в разных местах
- Handlers становятся тонкими адаптерами

### 2. **Тестируемость**
- Легко мокировать зависимости
- Можно тестировать без Telegram API
- Изолированное тестирование логики

### 3. **Читаемость**
- Явные названия use cases
- Понятная бизнес-логика
- Самодокументирующийся код

### 4. **Расширяемость**
- Легко добавить новый use case
- Переиспользование существующих
- Композиция use cases

---

## 🎓 Clean Architecture

Use Cases являются частью **Clean Architecture**:

```
┌─────────────────────────────────────┐
│  Handlers (adapters)                │
│  - Telegram-специфичные             │
│  - Тонкие (<30 строк)               │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  Use Cases (application logic)      │ ← Мы здесь
│  - Оркестрация бизнес-процессов     │
│  - Независимы от инфраструктуры     │
└─────────────────────────────────────┘
              ↓
┌──────────────┬──────────────┬────────┐
│  Domain      │  Schemas     │  Repos │
│  (rules)     │  (DTO)       │  (data)│
└──────────────┴──────────────┴────────┘
```

---

## 💡 Best Practices

### 1. **Один Use Case = Одна бизнес-операция**
```python
# ✅ Хорошо
class AnalyzeChannelUseCase:
    async def execute(self, identifier, top_n):
        # Полный процесс анализа канала
        ...

# ❌ Плохо
class AnalyzeEverythingUseCase:
    async def analyze_channel(self, ...):
        ...
    async def analyze_website(self, ...):
        ...
    async def analyze_user(self, ...):
        ...
```

### 2. **Инжекция зависимостей**
```python
# ✅ Хорошо - зависимости через конструктор
class AnalyzeChannelUseCase:
    def __init__(self, repo: RepositoryFacade):
        self.repo = repo

# ❌ Плохо - глобальные импорты
class AnalyzeChannelUseCase:
    def execute(self):
        from app.db.repo import save_channel  # Плохо!
        ...
```

### 3. **Возврат domain/schema объектов**
```python
# ✅ Хорошо
async def execute(self) -> Path:
    return report_path

# ❌ Плохо
async def execute(self) -> dict:
    return {"path": str(report_path), "success": True}
```

---

## 📈 Статистика

| Use Case | Строк кода | Зависимостей | Сложность |
|----------|-----------|--------------|-----------|
| MessageParserService | ~100 | 0 | Низкая |
| DetectProxyChannelUseCase | ~80 | Domain | Средняя |
| AnalyzeChannelUseCase | ~120 | Repositories, Domain, Schemas | Высокая |
| AnalyzeWebsiteUseCase | ~50 | Существующие сервисы | Низкая |

---

## 🚀 Следующие шаги

После внедрения Use Cases:
1. ✅ Handlers стали тонкими (<30 строк)
2. ✅ Бизнес-логика централизована
3. ✅ Легко тестировать
4. 🔄 Добавить unit-тесты для use cases
5. 🔄 Добавить integration tests

---

*Документация создана: 13 декабря 2025*

