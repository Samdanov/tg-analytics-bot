#!/bin/bash
# Быстрый деплой изменений (без sudo)

echo "🚀 БЫСТРЫЙ ДЕПЛОЙ"
echo "=================="
echo ""

# Проверка что мы в правильной директории
if [ ! -f "app/main_di.py" ]; then
    echo "❌ Ошибка: запусти скрипт из корня проекта"
    exit 1
fi

# Найти PID процесса бота
BOT_PID=$(ps aux | grep "[p]ython -m app.main_di" | awk '{print $2}')

if [ -z "$BOT_PID" ]; then
    echo "⚠️  Бот не запущен"
    echo "   Запусти: sudo systemctl start orbita-bot"
    exit 1
fi

echo "📋 Найден процесс бота: PID $BOT_PID"
echo ""

# Убить процесс (требует sudo или owner)
echo "🔄 Перезапускаю бота..."
kill -9 $BOT_PID 2>/dev/null

if [ $? -eq 0 ]; then
    echo "   ✅ Старый процесс остановлен"
else
    echo "   ⚠️  Не удалось убить процесс (нужен sudo)"
    echo "   Используй: sudo systemctl restart orbita-bot"
    exit 1
fi

# Подождать немного
sleep 2

# Запустить бота в фоне
echo "▶️  Запускаю бота..."
cd /home/alex/apps/tg-analytics-bot
source venv/bin/activate
nohup python -m app.main_di > /dev/null 2>> logs/bot-error.log &

NEW_PID=$!
echo "   ✅ Бот запущен: PID $NEW_PID"
echo ""

# Подождать и проверить
sleep 3

if ps -p $NEW_PID > /dev/null; then
    echo "✅ Бот работает!"
    echo ""
    echo "📊 Статус:"
    ps aux | grep "[p]ython -m app.main_di"
    echo ""
    echo "📝 Логи:"
    echo "   tail -f logs/bot-error.log"
else
    echo "❌ Бот не запустился!"
    echo "   Проверь логи: tail -100 logs/bot-error.log"
    exit 1
fi

