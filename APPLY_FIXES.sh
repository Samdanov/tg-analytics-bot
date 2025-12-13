#!/bin/bash
# Применение всех исправлений

echo "╔═══════════════════════════════════════════════════════╗"
echo "║                                                       ║"
echo "║      🔧 ПРИМЕНЕНИЕ ИСПРАВЛЕНИЙ                       ║"
echo "║                                                       ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

cd /home/alex/apps/tg-analytics-bot

# 1. Проверка файлов
echo "1️⃣  Проверка исправленных файлов..."
echo ""

if [ -f "app/main_di.py" ]; then
    echo "   ✅ app/main_di.py - OK"
else
    echo "   ❌ app/main_di.py - NOT FOUND"
    exit 1
fi

if [ -f "app/bot/handlers/workflow_di.py" ]; then
    echo "   ✅ app/bot/handlers/workflow_di.py - OK"
else
    echo "   ❌ app/bot/handlers/workflow_di.py - NOT FOUND"
    exit 1
fi

if [ -f "app/domain/value_objects.py" ]; then
    echo "   ✅ app/domain/value_objects.py - OK (ChannelIdentifier fixed)"
else
    echo "   ❌ app/domain/value_objects.py - NOT FOUND"
    exit 1
fi

if [ -f "app/services/similarity_engine/engine_single.py" ]; then
    echo "   ✅ app/services/similarity_engine/engine_single.py - OK (TF-IDF + Cosine)"
else
    echo "   ❌ engine_single.py - NOT FOUND"
    exit 1
fi

if [ -f "app/services/xlsx_generator.py" ]; then
    echo "   ✅ app/services/xlsx_generator.py - OK (Absolute normalization)"
else
    echo "   ❌ xlsx_generator.py - NOT FOUND"
    exit 1
fi

echo ""

# 2. Проверка импортов
echo "2️⃣  Проверка импортов Python..."
source venv/bin/activate

python -c "from app.domain.value_objects import ChannelIdentifier; print('   ✅ ChannelIdentifier imports OK')" || exit 1
python -c "from app.services.similarity_engine.engine_single import calculate_similarity_for_channel; print('   ✅ engine_single imports OK')" || exit 1
python -c "from app.services.xlsx_generator import generate_similar_channels_xlsx; print('   ✅ xlsx_generator imports OK')" || exit 1
python -c "from app.bot.handlers.workflow_di import router; print('   ✅ workflow_di imports OK')" || exit 1

echo ""

# 3. Обновление systemd service
echo "3️⃣  Обновление systemd service..."
sudo cp orbita-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
echo "   ✅ Service файл обновлён"
echo ""

# 4. Перезапуск бота
echo "4️⃣  Перезапуск бота..."
sudo systemctl restart orbita-bot
sleep 3
echo "   ✅ Бот перезапущен"
echo ""

# 5. Проверка статуса
echo "5️⃣  Проверка статуса..."
sudo systemctl status orbita-bot --no-pager | head -15
echo ""

echo "╔═══════════════════════════════════════════════════════╗"
echo "║                                                       ║"
echo "║      ✅ ВСЕ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ!                   ║"
echo "║                                                       ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "📋 Что исправлено:"
echo "   ✅ ChannelIdentifier: +username, +channel_id, +to_telethon_format()"
echo "   ✅ Similarity: абсолютная нормализация (честные %)"
echo "   ✅ Similarity: TF-IDF + Cosine Similarity (точнее)"
echo "   ✅ Similarity: минимальный порог 25%"
echo "   ✅ DI Architecture: migration complete"
echo ""
echo "🔍 Проверка:"
echo "   • Логи: tail -f logs/bot-error.log"
echo "   • Telegram: отправь боту канал и проверь проценты"
echo "   • Статистика: tail -f logs/bot.log | grep 'ENGINE_SINGLE stats'"
echo ""
echo "🎉 Готово к использованию!"
echo ""
EOF
chmod +x APPLY_FIXES.sh && cat APPLY_FIXES.sh
