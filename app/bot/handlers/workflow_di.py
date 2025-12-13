"""
Workflow Handlers (with Dependency Injection)

Handlers с внедрением зависимостей через DI контейнер.
Полностью избавлены от глобальных переменных.
"""

import time
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile

from app.core.container import get_container
from app.schemas import CallbackDataSchema
from app.services.telegram_parser.channel_info import get_channel_with_posts
from app.services.helpers import build_channel_summary, build_website_summary
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

# DI Container
container = get_container()
logger = container.logger(__name__)

# Media group deduplication
_media_group_cache = {}
_CACHE_TTL = 60


def _is_duplicate_media_group(media_group_id: str | None) -> bool:
    """Проверка дубликатов media группы."""
    if not media_group_id:
        return False
    
    now = time.time()
    expired = [k for k, v in _media_group_cache.items() if now - v > _CACHE_TTL]
    for k in expired:
        _media_group_cache.pop(k, None)
    
    if media_group_id in _media_group_cache:
        return True
    
    _media_group_cache[media_group_id] = now
    return False


@router.message(F.text | F.forward_from_chat | F.photo | F.video)
async def detect_content_handler(message: Message):
    """
    Определение типа контента (канал/сайт) и отображение кнопок выбора.
    
    Использует DI для получения зависимостей.
    """
    # Игнорируем дубликаты media_group
    if _is_duplicate_media_group(message.media_group_id):
        return
    
    # Получаем сервисы через DI
    message_parser = container.message_parser
    
    # Парсинг сообщения
    content_type, content_info = message_parser.detect_content_type(message)
    
    if not content_type:
        return
    
    # Обработка веб-сайта
    if content_type == "website":
        url = content_info.url
        
        text = (
            f"{Icons.SATELLITE} <b>Найден веб-сайт:</b>\n"
            f"<b>{url}</b>\n\n"
            f"{Icons.ANALYTICS} Выбери количество похожих каналов для анализа:"
        )
        
        # Используем CallbackDataSchema для создания callback_data
        buttons_data = [
            ("📊 10 каналов", CallbackDataSchema(action="analyze_website", identifier=url, top_n=10, is_id_based=False)),
            ("📊 25 каналов", CallbackDataSchema(action="analyze_website", identifier=url, top_n=25, is_id_based=False)),
            ("📊 50 каналов", CallbackDataSchema(action="analyze_website", identifier=url, top_n=50, is_id_based=False)),
            ("📊 100 каналов", CallbackDataSchema(action="analyze_website", identifier=url, top_n=100, is_id_based=False)),
            ("🚀 500 каналов (макс)", CallbackDataSchema(action="analyze_website", identifier=url, top_n=500, is_id_based=False)),
        ]
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=schema.to_callback_string())]
            for text, schema in buttons_data[:2]
        ] + [
            [InlineKeyboardButton(text=text, callback_data=schema.to_callback_string())]
            for text, schema in buttons_data[2:4]
        ] + [
            [InlineKeyboardButton(text=buttons_data[4][0], callback_data=buttons_data[4][1].to_callback_string())]
        ])
        
        await message.answer(text, reply_markup=kb)
        return
    
    # Обработка канала
    if content_type == "channel":
        identifier = content_info.identifier
        title = content_info.title
        
        text = format_channel_info(
            identifier.to_display_format(),
            title,
            identifier.is_id_based
        )
        
        kb = create_analysis_buttons(
            identifier.to_db_format(),
            identifier.is_id_based
        )
        
        await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("analyze:"))
async def analyze_channel_callback(callback: CallbackQuery):
    """
    Обработка анализа канала.
    
    Использует DI для получения use cases.
    """
    await callback.answer()
    
    # Получаем use cases через DI
    detect_proxy_uc = container.detect_proxy_uc
    analyze_channel_uc = container.analyze_channel_uc
    
    # Парсинг callback_data через schema
    try:
        callback_schema = CallbackDataSchema.from_callback_string(callback.data)
    except ValueError as e:
        await callback.message.answer(format_error_message(f"Неверный формат: {e}"))
        return
    
    identifier_raw = callback_schema.identifier
    top_n = callback_schema.top_n
    is_id_based = callback_schema.is_id_based
    
    # Отображение loading
    msg = await callback.message.answer(
        format_loading_message(identifier_raw, is_id_based)
    )
    
    try:
        # Получаем данные для проверки на прокладку
        channel_data, posts, error = await get_channel_with_posts(
            raw_username=identifier_raw,
            limit=50
        )
        
        if error:
            await msg.edit_text(format_error_message(f"Ошибка: {error}"))
            return
        
        # Проверка на прокладку (только для username-based)
        if posts and not is_id_based:
            proxy_result = await detect_proxy_uc.execute(
                posts=posts,
                exclude_username=identifier_raw
            )
            
            if proxy_result.is_proxy:
                logger.info(
                    f"Proxy detected: @{identifier_raw}, "
                    f"channels={len(proxy_result.linked_channels)}"
                )
                
                proxy_message = format_proxy_channel_message(
                    proxy_result.linked_channels,
                    top_n
                )
                kb = create_channel_selection_buttons(
                    proxy_result.linked_channels,
                    top_n,
                    identifier_raw,
                    is_id_based
                )
                
                await callback.message.answer(proxy_message, reply_markup=kb)
                return
        
        # Обычный анализ
        display = f"ID:{identifier_raw}" if is_id_based else f"@{identifier_raw}"
        await msg.edit_text(
            f"{Icons.START} <b>Запускаю анализ для</b> {display}...\n"
            f"{Icons.ANALYTICS} Поиск {top_n} похожих каналов..."
        )
    
    except Exception as e:
        await msg.edit_text(format_error_message(f"Ошибка проверки: {e}"))
        logger.exception("Error in channel check")
        return
    
    # Запуск полного анализа
    try:
        from app.domain import ChannelIdentifier
        identifier = ChannelIdentifier.from_raw(identifier_raw)
        
        report_path: Path = await analyze_channel_uc.execute(identifier, top_n=top_n)
    
    except ValueError as e:
        await msg.edit_text(format_error_message(f"Не удалось: {e}"))
        return
    except Exception as e:
        await msg.edit_text(format_error_message(f"Ошибка: {e}"))
        logger.exception("Error in analysis")
        return
    
    # Отправка результатов
    summary = await build_channel_summary(identifier_raw)
    await callback.message.answer(summary)
    
    doc = FSInputFile(report_path)
    await msg.edit_text(f"{Icons.SUCCESS} Анализ завершён!")
    
    display_name = f"ID:{identifier_raw}" if is_id_based else f"@{identifier_raw}"
    await callback.message.answer_document(
        document=doc,
        caption=f"{Icons.ANALYTICS} Отчёт: {top_n} похожих для {display_name}",
    )


@router.callback_query(F.data.startswith("analyze_website|"))
async def analyze_website_callback(callback: CallbackQuery):
    """
    Обработка анализа веб-сайта.
    
    Использует DI для получения use cases.
    """
    await callback.answer()
    
    # Получаем use case через DI
    analyze_website_uc = container.analyze_website_uc
    
    # Парсинг через schema
    try:
        callback_schema = CallbackDataSchema.from_callback_string(callback.data)
    except ValueError as e:
        await callback.message.answer(format_error_message(f"Неверный формат: {e}"))
        return
    
    url = callback_schema.identifier
    top_n = callback_schema.top_n
    
    msg = await callback.message.answer(
        f"{Icons.SEARCH} {Icons.LOADING} Парсинг {url}...\n"
        f"{Icons.ANALYTICS} Поиск {top_n} похожих каналов..."
    )
    
    # Запуск анализа
    try:
        report_path, analysis_result = await analyze_website_uc.execute(url, top_n=top_n)
    except ValueError as e:
        await msg.edit_text(format_error_message(f"Не удалось: {e}"))
        return
    except Exception as e:
        await msg.edit_text(format_error_message(f"Ошибка: {e}"))
        logger.exception("Error in website analysis")
        return
    
    # Отправка результатов
    summary = build_website_summary(url, analysis_result)
    await callback.message.answer(summary)
    
    doc = FSInputFile(report_path)
    await msg.edit_text(f"{Icons.SUCCESS} Анализ завершён!")
    
    await callback.message.answer_document(
        document=doc,
        caption=f"{Icons.ANALYTICS} Отчёт: {top_n} похожих для {url}",
    )


@router.callback_query(F.data.startswith("force_analyze:"))
async def force_analyze_callback(callback: CallbackQuery):
    """
    Принудительный анализ (игнорируя прокладку).
    
    Использует DI для получения use cases.
    """
    await callback.answer()
    
    # Получаем use case через DI
    analyze_channel_uc = container.analyze_channel_uc
    
    # Парсинг callback_data
    try:
        callback_schema = CallbackDataSchema.from_callback_string(callback.data)
    except ValueError as e:
        await callback.message.answer(format_error_message(f"Неверный формат: {e}"))
        return
    
    identifier_raw = callback_schema.identifier
    top_n = callback_schema.top_n
    is_id_based = callback_schema.is_id_based
    
    display = f"ID:{identifier_raw}" if is_id_based else f"@{identifier_raw}"
    msg = await callback.message.answer(
        f"{Icons.WARNING} Принудительный анализ {display}...\n"
        f"{Icons.ANALYTICS} Поиск {top_n} похожих каналов..."
    )
    
    # Запуск анализа
    try:
        from app.domain import ChannelIdentifier
        identifier = ChannelIdentifier.from_raw(identifier_raw)
        
        report_path: Path = await analyze_channel_uc.execute(identifier, top_n=top_n)
    
    except ValueError as e:
        await msg.edit_text(format_error_message(f"Не удалось: {e}"))
        return
    except Exception as e:
        await msg.edit_text(format_error_message(f"Ошибка: {e}"))
        logger.exception("Error in force analysis")
        return
    
    # Отправка результатов
    summary = await build_channel_summary(identifier_raw)
    await callback.message.answer(summary)
    
    doc = FSInputFile(report_path)
    await msg.edit_text(f"{Icons.SUCCESS} Анализ завершён!")
    
    await callback.message.answer_document(
        document=doc,
        caption=f"{Icons.ANALYTICS} Отчёт: {top_n} похожих для {display}",
    )

