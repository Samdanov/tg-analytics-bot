"""
Unit Tests for Schemas Layer

Тесты для Pydantic schemas (валидация, сериализация).
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas import (
    ChannelIdentifierSchema,
    ChannelCreateSchema,
    ChannelResponseSchema,
    ChannelUpdateSchema,
    AnalysisResultSchema,
    AnalysisResponseSchema,
    SimilarChannelSchema,
    SimilarityResultSchema,
    CallbackDataSchema,
    ChannelInfoSchema,
    SuccessResponse,
    ErrorResponse,
)


# ============================================================================
# Tests for ChannelIdentifierSchema
# ============================================================================

class TestChannelIdentifierSchema:
    """Тесты для ChannelIdentifierSchema."""
    
    def test_valid_username(self):
        """Валидный username."""
        schema = ChannelIdentifierSchema(raw_value="@technews")
        assert schema.raw_value == "@technews"
        
        # Преобразование в domain
        domain_id = schema.to_domain()
        assert domain_id.username == "technews"
    
    def test_valid_id(self):
        """Валидный channel ID."""
        schema = ChannelIdentifierSchema(raw_value="-1002508742544")
        domain_id = schema.to_domain()
        assert domain_id.is_id_based
    
    def test_invalid_username(self):
        """Невалидный username."""
        with pytest.raises(ValidationError) as exc_info:
            ChannelIdentifierSchema(raw_value="@ab")
        
        assert "3-32 characters" in str(exc_info.value)


# ============================================================================
# Tests for ChannelCreateSchema
# ============================================================================

class TestChannelCreateSchema:
    """Тесты для ChannelCreateSchema."""
    
    def test_create_valid(self):
        """Создание с валидными данными."""
        schema = ChannelCreateSchema(
            identifier="@technews",
            title="Tech News",
            description="Latest tech news",
            subscribers=10000
        )
        
        assert schema.identifier == "@technews"
        assert schema.subscribers == 10000
    
    def test_negative_subscribers(self):
        """Отклонение отрицательных subscribers."""
        with pytest.raises(ValidationError):
            ChannelCreateSchema(
                identifier="@technews",
                subscribers=-100
            )
    
    def test_whitespace_stripping(self):
        """Удаление пробелов."""
        schema = ChannelCreateSchema(
            identifier="@technews",
            title="  Tech News  ",
            description="  Description  "
        )
        
        assert schema.title == "Tech News"
        assert schema.description == "Description"


# ============================================================================
# Tests for AnalysisResultSchema
# ============================================================================

class TestAnalysisResultSchema:
    """Тесты для AnalysisResultSchema."""
    
    def test_valid_analysis(self):
        """Валидный результат анализа."""
        schema = AnalysisResultSchema(
            audience="IT specialists",
            keywords=["python", "django", "backend"],
            tone="Professional",
            source="llm",
            confidence=0.9
        )
        
        assert schema.is_from_llm
        assert not schema.is_fallback
        assert schema.has_keywords
    
    def test_fallback_analysis(self):
        """Fallback результат."""
        schema = AnalysisResultSchema(
            audience="Unable to analyze",
            keywords=["fallback"],
            tone="",
            source="fallback",
            confidence=0.5
        )
        
        assert not schema.is_from_llm
        assert schema.is_fallback
    
    def test_keywords_cleaning(self):
        """Очистка keywords (пустые значения)."""
        schema = AnalysisResultSchema(
            audience="Test",
            keywords=["python", "", "  ", "django"],
            tone="",
            source="llm"
        )
        
        # Пустые должны быть удалены
        assert "" not in schema.keywords
        assert "python" in schema.keywords
        assert "django" in schema.keywords


# ============================================================================
# Tests for CallbackDataSchema
# ============================================================================

class TestCallbackDataSchema:
    """Тесты для CallbackDataSchema."""
    
    def test_parse_username_callback(self):
        """Парсинг username callback."""
        schema = CallbackDataSchema.from_callback_string("analyze:technews:10")
        
        assert schema.action == "analyze"
        assert schema.identifier == "technews"
        assert schema.top_n == 10
        assert not schema.is_id_based
    
    def test_parse_id_callback(self):
        """Парсинг ID callback."""
        schema = CallbackDataSchema.from_callback_string("analyze:id:-1002508742544:25")
        
        assert schema.action == "analyze"
        assert schema.identifier == "-1002508742544"
        assert schema.top_n == 25
        assert schema.is_id_based
    
    def test_parse_website_callback(self):
        """Парсинг website callback."""
        schema = CallbackDataSchema.from_callback_string(
            "analyze_website|https%3A%2F%2Fexample.com|50"
        )
        
        assert schema.action == "analyze_website"
        assert schema.identifier == "https://example.com"
        assert schema.top_n == 50
    
    def test_serialize_back(self):
        """Сериализация обратно в строку."""
        original = "analyze:technews:10"
        schema = CallbackDataSchema.from_callback_string(original)
        serialized = schema.to_callback_string()
        
        assert serialized == original
    
    def test_invalid_format(self):
        """Неверный формат callback."""
        with pytest.raises(ValueError):
            CallbackDataSchema.from_callback_string("invalid_format")


# ============================================================================
# Tests for SimilarChannelSchema
# ============================================================================

class TestSimilarChannelSchema:
    """Тесты для SimilarChannelSchema."""
    
    def test_create_valid(self):
        """Создание похожего канала."""
        schema = SimilarChannelSchema(
            channel_id=456,
            identifier="devnews",
            is_id_based=False,
            title="Dev News",
            description="Developer news",
            subscribers=8000,
            keywords=["python", "javascript"],
            score=0.85,
            common_keywords=["python"]
        )
        
        assert schema.relevance_percent == 85.0
        assert schema.telegram_link == "https://t.me/devnews"
        assert schema.display_name == "@devnews"
    
    def test_private_channel_no_link(self):
        """Приватный канал без ссылки."""
        schema = SimilarChannelSchema(
            channel_id=789,
            identifier="id:-1002508742544",
            is_id_based=True,
            title="Private Channel",
            subscribers=1000,
            keywords=["test"],
            score=0.75,
            common_keywords=[]
        )
        
        assert schema.telegram_link is None
        assert "ID:" in schema.display_name


# ============================================================================
# Tests for Standard Responses
# ============================================================================

class TestStandardResponses:
    """Тесты для SuccessResponse и ErrorResponse."""
    
    def test_success_response(self):
        """Успешный ответ."""
        response = SuccessResponse(
            message="Operation completed",
            data={"result": "ok"}
        )
        
        assert response.success is True
        assert response.message == "Operation completed"
        assert response.data["result"] == "ok"
    
    def test_error_response(self):
        """Ответ с ошибкой."""
        response = ErrorResponse(
            error="ValidationError",
            message="Invalid data",
            details={"field": "username"}
        )
        
        assert response.success is False
        assert response.error == "ValidationError"
        assert response.details["field"] == "username"


# ============================================================================
# Запуск тестов
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

