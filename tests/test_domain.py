"""
Unit Tests for Domain Layer

Тесты для domain entities, value objects и services.
"""

import pytest
from app.domain import (
    ChannelIdentifier,
    InvalidChannelIdentifierError,
    ChannelEntity,
    AnalysisResult,
    ProxyChannelDetector,
    ProxyChannelDetectedError,
)


# ============================================================================
# Tests for ChannelIdentifier (Value Object)
# ============================================================================

class TestChannelIdentifier:
    """Тесты для ChannelIdentifier."""
    
    def test_from_username(self):
        """Создание из username."""
        identifier = ChannelIdentifier.from_raw("@technews")
        
        assert identifier.username == "technews"
        assert not identifier.is_id_based
        assert identifier.to_display_format() == "@technews"
        assert identifier.to_db_format() == "technews"
    
    def test_from_username_without_at(self):
        """Создание из username без @."""
        identifier = ChannelIdentifier.from_raw("technews")
        
        assert identifier.username == "technews"
        assert identifier.to_display_format() == "@technews"
    
    def test_from_channel_id(self):
        """Создание из channel ID."""
        identifier = ChannelIdentifier.from_raw("-1002508742544")
        
        assert identifier.is_id_based
        assert identifier.channel_id == -1002508742544
        assert identifier.to_db_format() == "id:-1002508742544"
        assert "ID:" in identifier.to_display_format()
    
    def test_invalid_username_too_short(self):
        """Отклонение слишком короткого username."""
        with pytest.raises(InvalidChannelIdentifierError) as exc_info:
            ChannelIdentifier.from_raw("@ab")
        
        assert "3-32 characters" in str(exc_info.value)
    
    def test_invalid_username_special_chars(self):
        """Отклонение username со специальными символами."""
        with pytest.raises(InvalidChannelIdentifierError):
            ChannelIdentifier.from_raw("@chan-nel")  # Дефис недопустим
    
    def test_equality(self):
        """Проверка равенства."""
        id1 = ChannelIdentifier.from_raw("@technews")
        id2 = ChannelIdentifier.from_raw("technews")
        
        assert id1 == id2
    
    def test_hash(self):
        """Проверка хеширования (для использования в set/dict)."""
        id1 = ChannelIdentifier.from_raw("@technews")
        id2 = ChannelIdentifier.from_raw("technews")
        
        assert hash(id1) == hash(id2)
        
        # Можно использовать в set
        identifiers = {id1, id2}
        assert len(identifiers) == 1


# ============================================================================
# Tests for ChannelEntity
# ============================================================================

class TestChannelEntity:
    """Тесты для ChannelEntity."""
    
    def test_create_entity(self):
        """Создание entity."""
        identifier = ChannelIdentifier.from_raw("@technews")
        
        entity = ChannelEntity(
            identifier=identifier,
            title="Tech News",
            description="Latest tech news",
            subscribers=10000
        )
        
        assert entity.identifier == identifier
        assert entity.title == "Tech News"
        assert entity.subscribers == 10000
        assert not entity.is_analyzed
    
    def test_entity_with_keywords(self):
        """Entity с keywords."""
        identifier = ChannelIdentifier.from_raw("@technews")
        
        entity = ChannelEntity(
            identifier=identifier,
            title="Tech News",
            description="",
            subscribers=10000,
            keywords=["tech", "news"]
        )
        
        assert entity.is_analyzed
        assert entity.has_keywords
        assert "tech" in entity.keywords


# ============================================================================
# Tests for AnalysisResult
# ============================================================================

class TestAnalysisResult:
    """Тесты для AnalysisResult."""
    
    def test_create_result(self):
        """Создание результата анализа."""
        result = AnalysisResult(
            audience="IT specialists",
            keywords=["python", "django"],
            tone="Professional"
        )
        
        assert result.audience == "IT specialists"
        assert len(result.keywords) == 2
        assert result.tone == "Professional"
        assert result.has_keywords
    
    def test_validation_min_keywords(self):
        """Валидация минимума keywords."""
        with pytest.raises(ValueError):
            AnalysisResult(
                audience="Test",
                keywords=[],  # Пустой список
                tone=""
            )
    
    def test_validation_max_keywords(self):
        """Валидация максимума keywords."""
        with pytest.raises(ValueError):
            AnalysisResult(
                audience="Test",
                keywords=["kw"] * 51,  # Больше 50
                tone=""
            )


# ============================================================================
# Tests for ProxyChannelDetector
# ============================================================================

class TestProxyChannelDetector:
    """Тесты для ProxyChannelDetector."""
    
    def test_normal_channel(self):
        """Обычный канал (не прокладка)."""
        detector = ProxyChannelDetector()
        
        posts = [
            {"text": "Long text about technology and programming without links" * 5},
            {"text": "Another long post about development" * 3},
        ]
        
        # Не должно бросить исключение
        result = detector.detect(posts)
        assert result is not None
    
    def test_proxy_channel_detected(self):
        """Канал-прокладка обнаружен."""
        detector = ProxyChannelDetector(
            min_linked_channels=2,
            max_avg_text=50,
            min_link_ratio=0.5
        )
        
        posts = [
            {"text": "Check @channel1"},
            {"text": "Visit t.me/channel2"},
            {"text": "Link: t.me/channel3"},
        ]
        
        with pytest.raises(ProxyChannelDetectedError) as exc_info:
            detector.detect(posts)
        
        error = exc_info.value
        assert error.details["linked_channels"]
        assert len(error.details["linked_channels"]) >= 2
    
    def test_exclude_username(self):
        """Исключение текущего канала из подсчета."""
        detector = ProxyChannelDetector()
        
        posts = [
            {"text": "@technews mentions @otherchannel"},  # technews = текущий
            {"text": "@technews again @otherchannel"},
        ]
        
        # Не должно считать technews как прокладку (только 1 внешний канал)
        result = detector.detect(posts, exclude_username="technews")
        assert result is not None


# ============================================================================
# Запуск тестов
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

