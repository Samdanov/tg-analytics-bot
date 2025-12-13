#!/bin/bash
# Скрипт для переключения на DI архитектуру

echo "🚀 ПЕРЕКЛЮЧЕНИЕ НА CLEAN ARCHITECTURE (DI)"
echo "=========================================="
echo ""

# 1. Копировать service файл
echo "1️⃣  Обновляю systemd service..."
sudo cp orbita-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
echo "   ✅ Service file updated"
echo ""

# 2. Остановить бота
echo "2️⃣  Останавливаю бота..."
sudo systemctl stop orbita-bot
echo "   ✅ Bot stopped"
echo ""

# 3. Удалить старые workflow файлы
echo "3️⃣  Удаляю старые workflow файлы..."
rm -f app/bot/handlers/workflow.py
rm -f app/bot/handlers/workflow_old.py
rm -f app/bot/handlers/workflow_new.py
echo "   ✅ Old workflow files removed:"
echo "      - workflow.py (legacy)"
echo "      - workflow_old.py (backup)"
echo "      - workflow_new.py (intermediate)"
echo ""

# 4. Удалить старый main.py
echo "4️⃣  Удаляю старый main.py..."
rm -f app/main.py
echo "   ✅ Legacy main.py removed"
echo ""

# 5. Проверить что workflow_di.py существует
echo "5️⃣  Проверяю наличие workflow_di.py..."
if [ -f "app/bot/handlers/workflow_di.py" ]; then
    echo "   ✅ workflow_di.py exists"
else
    echo "   ❌ ERROR: workflow_di.py not found!"
    exit 1
fi
echo ""

# 6. Запустить бота с новой архитектурой
echo "6️⃣  Запускаю бота с DI архитектурой..."
sudo systemctl start orbita-bot
sleep 3
echo "   ✅ Bot started"
echo ""

# 7. Проверить статус
echo "7️⃣  Проверяю статус..."
sudo systemctl status orbita-bot --no-pager | head -20
echo ""

echo "=========================================="
echo "✅ МИГРАЦИЯ НА DI ЗАВЕРШЕНА!"
echo "=========================================="
echo ""
echo "📋 Что изменилось:"
echo "  • Используется: app.main_di (DI Container)"
echo "  • Handlers: workflow_di.py (Clean Architecture)"
echo "  • Удалены: workflow.py, workflow_old.py, workflow_new.py, main.py"
echo ""
echo "🔍 Проверка:"
echo "  • Логи: tail -f logs/bot-error.log"
echo "  • Статус: sudo systemctl status orbita-bot"
echo "  • Telegram: отправь /start боту"
echo ""
echo "🎉 Теперь используется Clean Architecture с DI!"
echo ""

