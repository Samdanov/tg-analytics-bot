#!/bin/bash
# Перезапуск бота с исправлениями

echo "╔══════════════════════════════════════════════════════╗"
echo "║                                                      ║"
echo "║     🔧 ПЕРЕЗАПУСК БОТА С ИСПРАВЛЕНИЯМИ              ║"
echo "║                                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

cd /home/alex/apps/tg-analytics-bot

echo "✅ Исправления применены:"
echo "   1. TF-IDF только для non-frequent tokens"
echo "   2. Порог снижен с 25% → 15%"
echo "   3. Детальное логирование"
echo ""

echo "🔄 Перезапуск бота..."
sudo systemctl restart orbita-bot
sleep 3

echo ""
echo "📊 Статус бота:"
sudo systemctl status orbita-bot --no-pager | head -15

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                                                      ║"
echo "║     ✅ БОТ ПЕРЕЗАПУЩЕН                              ║"
echo "║                                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "🧪 Проверка:"
echo "   1. Отправь боту канал (например @klerkonline)"
echo "   2. Получи Excel отчёт"
echo "   3. Проверь что файл НЕ пустой ✅"
echo ""
echo "📋 Логи:"
echo "   • Ошибки: tail -f logs/bot-error.log"
echo "   • Similarity: tail -f logs/bot.log | grep 'ENGINE_SINGLE'"
echo ""
echo "📚 Документация: SIMILARITY_EMPTY_FIX.md"
echo ""
EOF
chmod +x RESTART_BOT_NOW.sh

