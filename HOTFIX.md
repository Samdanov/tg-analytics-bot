# 🔧 Hotfix - ChannelIdentifier properties

**Дата:** 13 декабря 2025  
**Статус:** ✅ ИСПРАВЛЕНО

---

## 🐛 Проблема

```
AttributeError: 'ChannelIdentifier' object has no attribute 'username'
AttributeError: 'ChannelIdentifier' object has no attribute 'to_telethon_format'
```

В `ChannelIdentifier` отсутствовали необходимые свойства и методы.

---

## ✅ Исправление

Добавлены в `app/domain/value_objects.py`:

### 1. Метод `to_telethon_format()`

```python
def to_telethon_format(self) -> str:
    """
    Возвращает формат для Telethon API.
    
    - Username: "channel" (без @)
    - ID: "-1002508742544" (без префикса "id:")
    """
    if self.is_id_based:
        return self.normalized_value.replace("id:", "")
    else:
        return self.normalized_value
```

### 2. Property `username`

```python
@property
def username(self) -> Optional[str]:
    """
    Username канала или None для ID-based.
    
    - Username канал: "channel"
    - ID канал: None
    """
    if self.is_id_based:
        return None
    return self.normalized_value
```

### 3. Property `channel_id`

```python
@property
def channel_id(self) -> Optional[int]:
    """
    Числовой ID канала или None для username-based.
    
    - Username канал: None
    - ID канал: -1002508742544
    """
    if not self.is_id_based:
        return None
    id_str = self.normalized_value.replace("id:", "")
    return int(id_str)
```

---

## 🚀 Применение исправления

### Перезапуск бота:

```bash
cd /home/alex/apps/tg-analytics-bot
sudo systemctl restart orbita-bot
```

### Проверка:

```bash
# Статус
sudo systemctl status orbita-bot

# Логи
tail -f logs/bot-error.log
```

---

## ✅ Что теперь работает

### ChannelIdentifier API:

```python
# Username-based канал
identifier = ChannelIdentifier.from_raw("@sharemed")

identifier.username           # "sharemed"
identifier.channel_id         # None
identifier.is_id_based        # False
identifier.to_db_format()     # "sharemed"
identifier.to_display_format() # "@sharemed"
identifier.to_telethon_format() # "sharemed"
identifier.to_file_name()     # "sharemed"

# ID-based канал
identifier = ChannelIdentifier.from_raw("-1002508742544")

identifier.username           # None
identifier.channel_id         # -1002508742544
identifier.is_id_based        # True
identifier.to_db_format()     # "id:-1002508742544"
identifier.to_display_format() # "ID: -1002508742544"
identifier.to_telethon_format() # "-1002508742544"
identifier.to_file_name()     # "id_-1002508742544"
```

---

## 🔍 Тестирование

После перезапуска:

1. **Отправь боту пост канала** (например, `@sharemed`)
2. **Выбери количество** (например, 10 каналов)
3. **Дождись анализа**
4. **Получи отчёт** в Excel

Должно работать без ошибок!

---

**Исправление готово! Перезапусти бота командой выше.** 🚀

*Hotfix: 13 декабря 2025*

