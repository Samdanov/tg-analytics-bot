-- Миграция: добавление колонки category в таблицу channels
-- Выполнить от имени postgres:
--   sudo -u postgres psql -d tg_analytics -f migrate_category.sql

-- 1. Добавляем колонку category
ALTER TABLE channels ADD COLUMN IF NOT EXISTS category TEXT;

-- 2. Создаём индекс для быстрой фильтрации
CREATE INDEX IF NOT EXISTS ix_channels_category ON channels(category);

-- 3. Проверяем результат
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'channels' AND column_name = 'category';

-- Готово!
