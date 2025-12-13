#!/bin/bash
echo "🔄 Перезапуск бота..."
sudo systemctl restart orbita-bot
sleep 2
echo "✅ Бот перезапущен"
echo ""
sudo systemctl status orbita-bot --no-pager | head -15
