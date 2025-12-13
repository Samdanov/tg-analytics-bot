"""
Unit Tests for Use Cases

Тесты для use cases с мокированием зависимостей.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.services.use_cases import (
    MessageParserService,
    DetectProxyChannelUseCase,
)


# ============================================================================
# Tests for MessageParserService
# ============================================================================

class TestMessageParserService:
    """Тесты для MessageParserService."""
    
    def test_extract_channel_from_forwarded(self):
        """Извлечение канала из forwarded message."""
        parser = MessageParserService()
        
        # Мокируем Message
        message = Mock()
        message.forward_from_chat = Mock()
        message.forward_from_chat.type = "channel"
        message.forward_from_chat.username = "technews"
        message.forward_from_chat.title = "Tech News"
        message.text = None
        message.caption = None
        
        # Извлекаем
        channel_info = parser.extract_channel(message)
        
        assert channel_info is not None
        assert channel_info.identifier.username == "technews"
        assert channel_info.title == "Tech News"
    
    def test_extract_channel_from_text(self):
        """Извлечение канала из текста."""
        parser = MessageParserService()
        
        message = Mock()
        message.forward_from_chat = None
        message.text = "Check out @technews for latest news"
        message.caption = None
        
        channel_info = parser.extract_channel(message)
        
        assert channel_info is not None
        assert channel_info.identifier.username == "technews"
    
    def test_extract_channel_from_link(self):
        """Извлечение канала из ссылки."""
        parser = MessageParserService()
        
        message = Mock()
        message.forward_from_chat = None
        message.text = "Visit https://t.me/technews"
        message.caption = None
        
        channel_info = parser.extract_channel(message)
        
        assert channel_info is not None
        assert channel_info.identifier.username == "technews"
    
    def test_extract_website(self):
        """Извлечение веб-сайта."""
        parser = MessageParserService()
        
        message = Mock()
        message.text = "Check https://example.com"
        message.caption = None
        
        website_info = parser.extract_website(message)
        
        assert website_info is not None
        assert website_info.url == "https://example.com"
    
    def test_detect_content_type_channel(self):
        """Автоопределение: канал."""
        parser = MessageParserService()
        
        message = Mock()
        message.text = "@technews"
        message.caption = None
        message.forward_from_chat = None
        
        content_type, info = parser.detect_content_type(message)
        
        assert content_type == "channel"
        assert info.identifier.username == "technews"
    
    def test_detect_content_type_website(self):
        """Автоопределение: сайт."""
        parser = MessageParserService()
        
        message = Mock()
        message.text = "https://example.com"
        message.caption = None
        message.forward_from_chat = None
        
        content_type, info = parser.detect_content_type(message)
        
        assert content_type == "website"
        assert info.url == "https://example.com"
    
    def test_no_content(self):
        """Нет контента."""
        parser = MessageParserService()
        
        message = Mock()
        message.text = "Just some random text"
        message.caption = None
        message.forward_from_chat = None
        
        content_type, info = parser.detect_content_type(message)
        
        assert content_type is None
        assert info is None


# ============================================================================
# Tests for DetectProxyChannelUseCase
# ============================================================================

class TestDetectProxyChannelUseCase:
    """Тесты для DetectProxyChannelUseCase."""
    
    @pytest.mark.asyncio
    async def test_normal_channel(self):
        """Обычный канал (не прокладка)."""
        use_case = DetectProxyChannelUseCase(
            min_linked_channels=3,
            max_avg_text=100,
            min_link_ratio=0.5
        )
        
        posts = [
            {"text": "Long text about technology" * 10},
            {"text": "Another post with content" * 10},
        ]
        
        result = await use_case.execute(posts)
        
        assert not result.is_proxy
        assert result.reason == "Обычный канал"
    
    @pytest.mark.asyncio
    async def test_proxy_channel(self):
        """Канал-прокладка."""
        use_case = DetectProxyChannelUseCase(
            min_linked_channels=2,
            max_avg_text=50,
            min_link_ratio=0.5
        )
        
        posts = [
            {"text": "@channel1"},
            {"text": "t.me/channel2"},
            {"text": "@channel3"},
        ]
        
        result = await use_case.execute(posts)
        
        assert result.is_proxy
        assert len(result.linked_channels) >= 2
        assert result.avg_text_length < 50
    
    @pytest.mark.asyncio
    async def test_empty_posts(self):
        """Пустой список постов."""
        use_case = DetectProxyChannelUseCase()
        
        result = await use_case.execute([])
        
        assert not result.is_proxy
        assert result.total_posts == 0


# ============================================================================
# Запуск тестов
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

