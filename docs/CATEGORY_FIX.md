# Исправление логики формирования базы каналов

## Проблема

Поиск похожих каналов работал некорректно:
- Бухгалтерия → консалтинг, бизнес, налоги, блогеры
- "Автоматизация" путалась с "автоматика"
- "Малый бизнес" → блогеры с фамилией "Малый"
- В топе — не профильная тема, а частотные сопутствующие слова

## Причины (были)

### 1. CATEGORY_KEYWORDS — искусственное накачивание
```python
# БЫЛО: словарь добавлял 7 искусственных keywords для каждой категории
CATEGORY_KEYWORDS = {
    "Бизнес и стартапы": ["бизнес", "стартап", "инвестиции", "финансы", ...],
    "Экономика": ["экономика", "финансы", "инвестиции", ...],  # пересечение!
    ...
}
```

Каналы из разных категорий получали одинаковые keywords → ложная высокая similarity.

### 2. Category как keyword в TF-IDF
```python
# БЫЛО:
add_keyword(category_clean)  # "Бизнес и стартапы" → токены ["бизнес", "стартапы"]
```

Все 10000+ каналов из категории получали одинаковые базовые токены.

### 3. Category НЕ ХРАНИЛАСЬ в БД
В модели `Channel` не было поля `category` — оно терялось при импорте.

### 4. Малый вес реального контента
- Из title: максимум 5 слов
- Из description: только если keywords < 8
- 60-70% keywords = искусственные, 30-40% = реальный контент

## Решение

### Новая концепция данных

| Уровень | Поле | Роль | В TF-IDF? |
|---------|------|------|-----------|
| PRIMARY | `category` | Фильтр / якорь при поиске | **НЕТ** |
| SECONDARY | `keywords` | Контент из title+description | **ДА** |

### Изменения в коде

#### 1. `app/db/models.py`
```python
class Channel(Base):
    # ...
    category = Column(Text, index=True)  # ДОБАВЛЕНО: PRIMARY TOPIC
```

#### 2. `app/db/repo.py`
```python
# save_channel() теперь сохраняет category
channel.category = channel_data.get("category") or ""
```

#### 3. `app/services/excel_importer.py`
- **УДАЛЁН** словарь `CATEGORY_KEYWORDS`
- `extract_keywords_v2()` извлекает keywords **ТОЛЬКО** из title + description
- Category передаётся в `save_channel()` как отдельное поле

#### 4. `app/services/similarity_engine/shared.py`
- `load_keywords_corpus()` возвращает `category` из БД
- `is_noise_channel()` использует реальную category, не первый keyword

#### 5. Новые скрипты
- `app/services/migrate_add_category.py` — миграция БД
- `reimport_database.py` — обновлён для новой логики

## Инструкция по применению

### Шаг 1: Миграция БД
```bash
cd /home/alex/apps/tg-analytics-bot
python -m app.services.migrate_add_category
```

### Шаг 2: Пересборка базы
```bash
python reimport_database.py
# или с ограничениями:
python reimport_database.py 100000 1000  # 100К каналов с >1000 подписчиков
```

### Шаг 3: Пересчёт similarity
```bash
python -m app.services.similarity_engine.cli seq 500
```

## Результат

- ✅ Category хранится отдельно, не размывается в keywords
- ✅ Keywords = чистый контент из title + description
- ✅ Бухгалтерия находит бухгалтерию
- ✅ "Автоматизация" ≠ "автоматика"
- ✅ Similarity работает предсказуемо

## Дальнейшие улучшения (опционально)

После пересборки базы можно добавить **category-boosting** в similarity engine:
```python
# same_category → score *= 1.5
# related_category → score *= 1.2
# unrelated_category → score *= 0.5
```

Или использовать category как **hard filter** при поиске.
