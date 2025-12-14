#!/bin/bash
#
# Параллельный пересчёт similarity (4 процесса)
# Время: ~6 часов вместо 23
#

echo "╔══════════════════════════════════════════════════════╗"
echo "║  🚀 ПАРАЛЛЕЛЬНЫЙ ПЕРЕСЧЁТ SIMILARITY (4 процесса)   ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

cd /home/alex/apps/tg-analytics-bot
source venv/bin/activate

# Запускаем 4 процесса в фоне
echo "🔄 Запуск процесса 1/4 (0-50000)..."
python -m app.services.similarity_engine.cli seq 500 0 50000 > logs/similarity_1.log 2>&1 &
PID1=$!

echo "🔄 Запуск процесса 2/4 (50000-100000)..."
python -m app.services.similarity_engine.cli seq 500 50000 100000 > logs/similarity_2.log 2>&1 &
PID2=$!

echo "🔄 Запуск процесса 3/4 (100000-150000)..."
python -m app.services.similarity_engine.cli seq 500 100000 150000 > logs/similarity_3.log 2>&1 &
PID3=$!

echo "🔄 Запуск процесса 4/4 (150000-210000)..."
python -m app.services.similarity_engine.cli seq 500 150000 210000 > logs/similarity_4.log 2>&1 &
PID4=$!

echo ""
echo "✅ Все 4 процесса запущены!"
echo ""
echo "📊 PIDs: $PID1, $PID2, $PID3, $PID4"
echo ""
echo "📋 Логи:"
echo "   tail -f logs/similarity_1.log"
echo "   tail -f logs/similarity_2.log"
echo "   tail -f logs/similarity_3.log"
echo "   tail -f logs/similarity_4.log"
echo ""
echo "🔍 Проверка статуса:"
echo "   ps aux | grep similarity_engine"
echo ""
echo "⏳ Ожидаемое время: ~6 часов"
echo ""

# Ждём завершения всех процессов
echo "⏳ Ожидание завершения..."
wait $PID1 $PID2 $PID3 $PID4

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║           ✅ ВСЕ ПРОЦЕССЫ ЗАВЕРШЕНЫ!                ║"
echo "╚══════════════════════════════════════════════════════╝"
