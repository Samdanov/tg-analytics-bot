# app/bot/handlers/workflow.py

import re
import time
from pathlib import Path
from collections import Counter

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)

from app.services.usecases.channel_service import run_full_pipeline_usecase
from app.services.usecases.website_service import run_website_analysis_pipeline
from app.services.helpers import build_channel_summary, build_website_summary
from app.services.telegram_parser.channel_info import get_channel_with_posts
from app.core.logging import get_logger
from app.bot.styles import (
    create_analysis_buttons,
    format_channel_info,
    format_loading_message,
    format_error_message,
    format_proxy_channel_message,
    create_channel_selection_buttons,
    Icons,
)

router = Router()
logger = get_logger(__name__)

USERNAME_RE = re.compile(r"(?:t\.me/|@)([A-Za-z0-9_]{3,})")
# Регулярка для извлечения username из ссылок в постах
CHANNEL_LINK_RE = re.compile(r"(?:https?://)?(?:www\.)?t\.me/([A-Za-z0-9_]{3,})")
USERNAME_MENTION_RE = re.compile(r"@([A-Za-z0-9_]{3,})")
# Регулярка для определения веб-сайтов
WEBSITE_RE = re.compile(r"https?://(?:www\.)?([a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,})")

# Простой кеш для дедупликации media_group
_media_group_cache = {}
_CACHE_TTL = 60  # секунд


def _is_duplicate_media_group(media_group_id: str | None) -> bool:
    """Проверяет, был ли уже обработан этот media_group."""
    if not media_group_id:
        return False
    
    now = time.time()
    # Очистка устаревших записей
    expired = [k for k, v in _media_group_cache.items() if now - v > _CACHE_TTL]
    for k in expired:
        _media_group_cache.pop(k, None)
    
    if media_group_id in _media_group_cache:
        return True
    
    _media_group_cache[media_group_id] = now
    return False


def _extract_channel_links_from_posts(posts: list, exclude_username: str = None) -> list:
    """
    Извлекает все упоминания каналов из постов.
    Возвращает список (username, count) отсортированный по частоте.
    
    Args:
        posts: список постов канала
        exclude_username: username текущего канала (исключить из результатов)
    """
    channels = []
    
    for post in posts:
        text = post.get("text", "") or ""
        
        # Ищем ссылки вида t.me/channel
        for match in CHANNEL_LINK_RE.finditer(text):
            username = match.group(1).lstrip("@").lower()
            # Пропускаем служебные ссылки и текущий канал
            if username and not username.startswith(("joinchat", "c/", "+")):
                if not exclude_username or username != exclude_username.lower():
                    channels.append(username)
        
        # Ищем упоминания вида @channel
        for match in USERNAME_MENTION_RE.finditer(text):
            username = match.group(1).lstrip("@").lower()
            if username:
                if not exclude_username or username != exclude_username.lower():
                    channels.append(username)
    
    # Подсчитываем частоту и возвращаем топ
    if not channels:
        return []
    
    counter = Counter(channels)
    top_channels = counter.most_common(10)
    
    logger.debug(f"Extracted channels from posts: {top_channels}")
    return top_channels  # Топ-10 упоминаемых каналов


def _extract_url_from_message(message: Message) -> tuple:
    """
    Извлекает URL из сообщения и определяет его тип.
    
    Возвращает: (url, url_type)
    - url: URL или None
    - url_type: "channel" | "website" | None
    """
    text = message.text or message.caption or ""
    
    if not text:
        return None, None
    
    # Сначала проверяем на канал Telegram
    channel_match = CHANNEL_LINK_RE.search(text)
    if channel_match:
        return None, "channel"  # Обрабатывается в _extract_channel_from_message
    
    # Проверяем на веб-сайт
    website_match = WEBSITE_RE.search(text)
    if website_match:
        url = text[website_match.start():website_match.end()]
        # Извлекаем полный URL если есть
        if url.startswith("http"):
            return url, "website"
        else:
            return f"https://{url}", "website"
    
    return None, None


def _extract_channel_from_message(message: Message):
    """
    Пытаемся достать username/ID и title канала из:
    - пересланного поста (поддержка каналов без username)
    - текста с ссылкой t.me/... или @username
    
    Возвращает: (identifier, title, is_id_based)
    - identifier: username или channel_id (как строка)
    - title: название канала
    - is_id_based: True если это ID (канал без username)
    """
    identifier = None
    title = None
    is_id_based = False

    if message.forward_from_chat and message.forward_from_chat.type == "channel":
        ch = message.forward_from_chat
        title = ch.title
        
        # Сначала пробуем взять username
        if ch.username:
            identifier = ch.username
            is_id_based = False
        else:
            # Если username нет - используем ID канала
            identifier = str(ch.id)
            is_id_based = True
            logger.info(f"Channel without username detected: {title} (ID: {identifier})")

    if not identifier and message.text:
        m = USERNAME_RE.search(message.text)
        if m:
            identifier = m.group(1)
            title = identifier
            is_id_based = False
    
    # Также проверяем caption (для постов с картинками)
    if not identifier and message.caption:
        m = USERNAME_RE.search(message.caption)
        if m:
            identifier = m.group(1)
            title = identifier
            is_id_based = False

    if identifier and not is_id_based:
        identifier = identifier.lstrip("@")

    return identifier, title, is_id_based


@router.message(F.text | F.forward_from_chat | F.photo | F.video)
async def detect_channel_handler(message: Message):
    # Игнорируем дубликаты из media_group (альбомы)
    if _is_duplicate_media_group(message.media_group_id):
        return

    # Проверяем на веб-сайт
    url, url_type = _extract_url_from_message(message)
    if url_type == "website" and url:
        # Обрабатываем как сайт
        text = (
            f"{Icons.SATELLITE} <b>Найден веб-сайт:</b>\n"
            f"<b>{url}</b>\n\n"
            f"{Icons.ANALYTICS} Выбери количество похожих каналов для анализа:"
        )
        
        # Создаем кнопки для выбора количества каналов
        # Используем специальный префикс "analyze_website|" для сайтов (| вместо : чтобы избежать конфликтов с URL)
        import urllib.parse
        url_encoded = urllib.parse.quote(url, safe='')
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=f"{Icons.NUM_10} 10 каналов", callback_data=f"analyze_website|{url_encoded}|10"),
                    InlineKeyboardButton(text=f"{Icons.NUM_25} 25 каналов", callback_data=f"analyze_website|{url_encoded}|25"),
                ],
                [
                    InlineKeyboardButton(text=f"{Icons.NUM_50} 50 каналов", callback_data=f"analyze_website|{url_encoded}|50"),
                    InlineKeyboardButton(text=f"{Icons.NUM_100} 100 каналов", callback_data=f"analyze_website|{url_encoded}|100"),
                ],
                [
                    InlineKeyboardButton(text=f"{Icons.NUM_500} 500 каналов (макс)", callback_data=f"analyze_website|{url_encoded}|500"),
                ],
            ]
        )
        
        await message.answer(text, reply_markup=kb)
        return

    # Обрабатываем как канал Telegram
    identifier, title, is_id_based = _extract_channel_from_message(message)
    if not identifier:
        return

    identifier = identifier.strip()

    # Формируем текст с учетом типа идентификатора (стиль ОРБИТА)
    text = format_channel_info(identifier, title, is_id_based)

    # Создаем стилизованные кнопки
    kb = create_analysis_buttons(identifier, is_id_based)

    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("analyze:"))
async def start_analysis_callback(callback: CallbackQuery):
    await callback.answer()

    parts = callback.data.split(":")
    
    # Проверяем формат: может быть "analyze:username:N" или "analyze:id:CHANNEL_ID:N"
    is_id_based = False
    identifier = None
    top_n = None
    
    try:
        if len(parts) == 3:
            # Формат: analyze:username:N
            identifier = parts[1]
            top_n = int(parts[2])
            is_id_based = False
        elif len(parts) == 4 and parts[1] == "id":
            # Формат: analyze:id:CHANNEL_ID:N
            identifier = parts[2]
            top_n = int(parts[3])
            is_id_based = True
        else:
            await callback.message.answer(format_error_message("неверный формат команды"))
            return
    except (ValueError, IndexError) as e:
        await callback.message.answer(format_error_message(f"неверный формат команды ({type(e).__name__})"))
        return

    # Проверяем, не является ли это каналом-прокладкой
    msg = await callback.message.answer(
        format_loading_message(identifier, is_id_based)
    )

    try:
        # Передаем идентификатор - это может быть username или ID
        channel_data, posts, error = await get_channel_with_posts(raw_username=identifier, limit=50)
        
        if error:
            await msg.edit_text(format_error_message(f"Ошибка при получении канала: {error}"))
            return
        
        # Проверяем на канал-прокладку (только для каналов с username, у ID-based каналов нет смысла)
        if posts and not is_id_based:
            linked_channels = _extract_channel_links_from_posts(posts, exclude_username=identifier)
            
            # Считаем реальный текстовый контент (без ссылок)
            total_text_length = 0
            posts_with_links_count = 0
            
            for post in posts:
                text = post.get("text", "") or ""
                # Удаляем ссылки и считаем оставшийся текст
                text_without_links = CHANNEL_LINK_RE.sub("", text)
                text_without_links = USERNAME_MENTION_RE.sub("", text_without_links)
                clean_text = text_without_links.strip()
                total_text_length += len(clean_text)
                
                # Считаем посты, в которых есть ссылки
                if CHANNEL_LINK_RE.search(text) or USERNAME_MENTION_RE.search(text):
                    posts_with_links_count += 1
            
            avg_text_per_post = total_text_length / len(posts) if posts else 0
            link_posts_ratio = posts_with_links_count / len(posts) if posts else 0
            
            display_name = f"@{identifier}" if not is_id_based else f"ID:{identifier}"
            logger.info(
                f"Channel check: {display_name} - posts: {len(posts)}, "
                f"linked_channels: {len(linked_channels)}, "
                f"avg_text_per_post: {avg_text_per_post:.1f}, "
                f"link_posts_ratio: {link_posts_ratio:.2%}"
            )
            
            # Если найдено много ссылок на каналы и мало текста - это прокладка
            # Критерии: >= 3 уникальных каналов, средняя длина текста < 100 символов,
            # и более 50% постов содержат ссылки
            is_proxy_channel = (
                linked_channels 
                and len(linked_channels) >= 3 
                and avg_text_per_post < 100
                and link_posts_ratio > 0.5
            )
            
            if is_proxy_channel:
                logger.info(
                    f"Proxy channel detected: @{identifier}, "
                    f"found {len(linked_channels)} linked channels: {linked_channels[:5]}"
                )
                
                # Создаем стилизованное сообщение о прокладке
                proxy_message = format_proxy_channel_message(linked_channels, top_n)
                kb = create_channel_selection_buttons(linked_channels, top_n, identifier, is_id_based)
                
                await callback.message.answer(proxy_message, reply_markup=kb)
                return
        
        # Если не прокладка - продолжаем обычный анализ
        if is_id_based:
            await msg.edit_text(
                f"{Icons.START} <b>Запускаю анализ для канала</b> (ID: <code>{identifier}</code>)...\n"
                f"{Icons.ANALYTICS} Поиск {top_n} похожих каналов. Это может занять немного времени..."
            )
        else:
            await msg.edit_text(
                f"{Icons.START} <b>Запускаю анализ для</b> @{identifier}...\n"
                f"{Icons.ANALYTICS} Поиск {top_n} похожих каналов. Это может занять немного времени..."
            )
        
    except Exception as e:
        await msg.edit_text(f"🔥 Ошибка при проверке канала: <code>{e}</code>")
        raise

    try:
        report_path: Path = await run_full_pipeline_usecase(identifier, top_n=top_n)
    except ValueError as e:
        await msg.edit_text(f"⚠️ Не удалось выполнить анализ: {e}")
        return
    except Exception as e:
        await msg.edit_text(f"🔥 Ошибка: <code>{e}</code>")
        raise

    summary = await build_channel_summary(identifier)
    await callback.message.answer(summary)

    doc = FSInputFile(report_path)
    await msg.edit_text("✅ Анализ завершён, отправляю отчёт...")

    display_name = f"ID:{identifier}" if is_id_based else f"@{identifier}"
    await callback.message.answer_document(
        document=doc,
        caption=f"📊 Отчёт: {top_n} похожих каналов для {display_name}",
    )


@router.callback_query(F.data.startswith("analyze_website|"))
async def analyze_website_callback(callback: CallbackQuery):
    """Обработчик анализа веб-сайта"""
    await callback.answer()
    
    # Формат: analyze_website|URL_ENCODED|top_n (используем | вместо : чтобы избежать конфликтов с URL)
    import urllib.parse
    parts = callback.data.split("|")
    if len(parts) != 3:
        await callback.message.answer(format_error_message("неверный формат команды для сайта"))
        return
    
    url = urllib.parse.unquote(parts[1])
    try:
        top_n = int(parts[2])
    except ValueError:
        await callback.message.answer(format_error_message("неверное количество каналов"))
        return
    
    msg = await callback.message.answer(
        f"{Icons.SEARCH} {Icons.LOADING} Парсинг сайта {url}...\n"
        f"{Icons.ANALYTICS} Поиск {top_n} похожих каналов. Это может занять время..."
    )
    
    try:
        result = await run_website_analysis_pipeline(url, top_n=top_n)
        report_path: Path = result[0]
        analysis_result = result[1]
    except ValueError as e:
        await msg.edit_text(format_error_message(f"Не удалось выполнить анализ: {e}"))
        return
    except Exception as e:
        await msg.edit_text(format_error_message(f"Ошибка: {e}"))
        logger.exception("Ошибка при анализе сайта")
        return
    
    # Выводим информацию по ЦА и ключам (как для каналов)
    summary = build_website_summary(url, analysis_result)
    await callback.message.answer(summary)
    
    doc = FSInputFile(report_path)
    await msg.edit_text(f"{Icons.SUCCESS} Анализ завершён, отправляю отчёт...")
    
    await callback.message.answer_document(
        document=doc,
        caption=f"{Icons.ANALYTICS} Отчёт: {top_n} похожих каналов для сайта {url}",
    )


@router.callback_query(F.data.startswith("force_analyze:"))
async def force_analysis_callback(callback: CallbackQuery):
    """Принудительный анализ канала-прокладки без проверок"""
    await callback.answer()

    parts = callback.data.split(":")
    
    # Проверяем формат: может быть "force_analyze:username:N" или "force_analyze:id:CHANNEL_ID:N"
    is_id_based = False
    identifier = None
    top_n = None
    
    if len(parts) == 3:
        # Формат: force_analyze:username:N
        identifier = parts[1]
        top_n = int(parts[2])
        is_id_based = False
    elif len(parts) == 4 and parts[1] == "id":
        # Формат: force_analyze:id:CHANNEL_ID:N
        identifier = parts[2]
        top_n = int(parts[3])
        is_id_based = True
    else:
        await callback.message.answer("❌ Ошибка: неверный формат команды")
        return

    if is_id_based:
        msg = await callback.message.answer(
            f"Запускаю принудительный анализ для канала (ID: <code>{identifier}</code>)...\n"
            f"Поиск {top_n} похожих каналов. Это может занять немного времени..."
        )
    else:
        msg = await callback.message.answer(
            f"Запускаю принудительный анализ для @{identifier}...\n"
            f"Поиск {top_n} похожих каналов. Это может занять немного времени..."
        )

    try:
        report_path: Path = await run_full_pipeline_usecase(identifier, top_n=top_n)
    except ValueError as e:
        await msg.edit_text(f"⚠️ Не удалось выполнить анализ: {e}")
        return
    except Exception as e:
        await msg.edit_text(f"🔥 Ошибка: <code>{e}</code>")
        raise

    summary = await build_channel_summary(identifier)
    await callback.message.answer(summary)

    doc = FSInputFile(report_path)
    await msg.edit_text("✅ Анализ завершён, отправляю отчёт...")

    display_name = f"ID:{identifier}" if is_id_based else f"@{identifier}"
    await callback.message.answer_document(
        document=doc,
        caption=f"📊 Отчёт: {top_n} похожих каналов для {display_name}",
    )
