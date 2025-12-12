# Миграция: добавление колонки tone

## Проблема с правами

Пользователь БД не имеет прав на изменение структуры таблицы. Нужно выполнить миграцию от имени суперпользователя PostgreSQL.

## Вариант 1: Через sudo (рекомендуется)

Если у вас есть доступ к sudo и PostgreSQL установлен локально:

```bash
sudo -u postgres psql -d tg_analytics -c "ALTER TABLE keywords_cache ADD COLUMN IF NOT EXISTS tone TEXT;"
```

Или используйте файл миграции:

```bash
sudo -u postgres psql -d tg_analytics -f app/db/migrations/add_tone_column.sql
```

## Вариант 2: Через psql с указанием пользователя

Если знаете пароль суперпользователя:

```bash
psql -U postgres -d tg_analytics -c "ALTER TABLE keywords_cache ADD COLUMN IF NOT EXISTS tone TEXT;"
```

## Вариант 3: Через Python скрипт с другими правами

Если у вас есть другой пользователь БД с правами на ALTER TABLE, можно временно изменить `POSTGRES_DSN` в `.env` файле на этого пользователя, выполнить миграцию, и вернуть обратно.

## Проверка

После применения миграции проверьте:

```bash
sudo -u postgres psql -d tg_analytics -c "\d keywords_cache"
```

Должна появиться колонка `tone` типа `text`.

## Альтернатива: через SQLAlchemy при первом запуске

Если миграция не может быть выполнена сейчас, SQLAlchemy может автоматически создать колонку при следующем использовании модели, но это зависит от настроек. Лучше выполнить миграцию вручную.
