"""
Message Parser Service

Сервис для парсинга сообщений Telegram и извлечения информации.
"""

import re
from typing import Optional, Tuple
from dataclasses import dataclass

from aiogram.types import Message

from app.domain import ChannelIdentifier, InvalidChannelIdentifierError
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ChannelInfo:
    """Информация о канале, извлеченная из сообщения."""
    identifier: ChannelIdentifier
    title: str
    

@dataclass
class WebsiteInfo:
    """Информация о веб-сайте, извлеченная из сообщения."""
    url: str


class MessageParserService:
    """
    Сервис для парсинга сообщений Telegram.
    
    Извлекает:
    - Каналы (по username, ID, forwarded message)
    - Веб-сайты (по URL)
    """
    
    # Регулярки для поиска
    USERNAME_RE = re.compile(r"(?:t\.me/|@)([A-Za-z0-9_]{3,})")
    WEBSITE_RE = re.compile(r"https?://(?:www\.)?([a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,})")
    
    def __init__(self):
        pass
    
    def extract_channel(self, message: Message) -> Optional[ChannelInfo]:
        """
        Извлечь информацию о канале из сообщения.
        
        Args:
            message: Telegram сообщение
        
        Returns:
            ChannelInfo или None если канал не найден
        """
        identifier_raw = None
        title = None
        
        # Проверяем forwarded message
        if message.forward_from_chat and message.forward_from_chat.type == "channel":
            ch = message.forward_from_chat
            title = ch.title
            
            if ch.username:
                identifier_raw = ch.username
            else:
                # Канал без username - используем ID
                identifier_raw = str(ch.id)
                logger.info(f"Channel without username: {title} (ID: {identifier_raw})")
        
        # Проверяем text
        if not identifier_raw and message.text:
            m = self.USERNAME_RE.search(message.text)
            if m:
                identifier_raw = m.group(1).lstrip("@")
                title = identifier_raw
        
        # Проверяем caption (для постов с медиа)
        if not identifier_raw and message.caption:
            m = self.USERNAME_RE.search(message.caption)
            if m:
                identifier_raw = m.group(1).lstrip("@")
                title = identifier_raw
        
        if not identifier_raw:
            return None
        
        # Создаем ChannelIdentifier через domain layer
        try:
            identifier = ChannelIdentifier.from_raw(identifier_raw)
            return ChannelInfo(identifier=identifier, title=title or identifier_raw)
        except InvalidChannelIdentifierError as e:
            logger.warning(f"Invalid channel identifier: {identifier_raw} | {e}")
            return None
    
    def extract_website(self, message: Message) -> Optional[WebsiteInfo]:
        """
        Извлечь веб-сайт из сообщения.
        
        Args:
            message: Telegram сообщение
        
        Returns:
            WebsiteInfo или None если сайт не найден
        """
        text = message.text or message.caption or ""
        
        if not text:
            return None
        
        # Проверяем на канал (приоритет над сайтом)
        if self.USERNAME_RE.search(text):
            return None
        
        # Ищем URL
        match = self.WEBSITE_RE.search(text)
        if not match:
            return None
        
        url = text[match.start():match.end()]
        if not url.startswith("http"):
            url = f"https://{url}"
        
        return WebsiteInfo(url=url)
    
    def detect_content_type(self, message: Message) -> Tuple[Optional[str], Optional[ChannelInfo | WebsiteInfo]]:
        """
        Определить тип контента в сообщении.
        
        Args:
            message: Telegram сообщение
        
        Returns:
            (content_type, info) где:
            - content_type: "channel" | "website" | None
            - info: ChannelInfo | WebsiteInfo | None
        """
        # Сначала проверяем канал (приоритет)
        channel_info = self.extract_channel(message)
        if channel_info:
            return "channel", channel_info
        
        # Потом проверяем сайт
        website_info = self.extract_website(message)
        if website_info:
            return "website", website_info
        
        return None, None

