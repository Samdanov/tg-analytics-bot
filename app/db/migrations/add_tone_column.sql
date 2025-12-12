-- Миграция: добавление колонки tone в таблицу keywords_cache
-- Выполнить: psql -d tg_analytics -f app/db/migrations/add_tone_column.sql

ALTER TABLE keywords_cache 
ADD COLUMN IF NOT EXISTS tone TEXT;

COMMENT ON COLUMN keywords_cache.tone IS 'Тональность канала (стиль подачи контента)';
