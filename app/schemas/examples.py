"""
Примеры использования Schemas

Демонстрирует как использовать Pydantic schemas в коде.
"""

from datetime import datetime
from typing import Dict, Any

from app.schemas import (
    ChannelIdentifierSchema,
    ChannelCreateSchema,
    ChannelResponseSchema,
    ChannelUpdateSchema,
    AnalysisResultSchema,
    AnalysisResponseSchema,
    SimilarityRequestSchema,
    SimilarChannelSchema,
    SimilarityResultSchema,
    CallbackDataSchema,
    ChannelInfoSchema,
    SuccessResponse,
    ErrorResponse,
)


# ============================================================================
# ПРИМЕР 1: Валидация и создание Channel schemas
# ============================================================================

def example_channel_schemas():
    """Примеры работы с Channel schemas."""
    
    print("=" * 80)
    print("ПРИМЕР 1: Channel Schemas")
    print("=" * 80)
    
    # 1.1 Валидация идентификатора
    print("\n1.1 Валидация ChannelIdentifier:")
    
    try:
        valid_id = ChannelIdentifierSchema(raw_value="@technews")
        print(f"✓ Валидный username: {valid_id.raw_value}")
        print(f"  Domain object: {valid_id.to_domain()}")
    except ValueError as e:
        print(f"✗ Ошибка: {e}")
    
    try:
        invalid_id = ChannelIdentifierSchema(raw_value="@ab")  # Слишком короткий
    except ValueError as e:
        print(f"✓ Отклонен некорректный username: {e}")
    
    # 1.2 Создание канала
    print("\n1.2 Создание ChannelCreateSchema:")
    
    channel_create = ChannelCreateSchema(
        identifier="@technews",
        title="Tech News",
        description="Latest technology news",
        subscribers=10000
    )
    print(f"✓ Создан schema: {channel_create.model_dump()}")
    
    # 1.3 Response schema
    print("\n1.3 ChannelResponseSchema:")
    
    channel_response = ChannelResponseSchema(
        id=123,
        identifier="technews",
        is_id_based=False,
        title="Tech News",
        description="Latest technology news",
        subscribers=10000,
        keywords=["tech", "news", "innovation"],
        last_update=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    
    print(f"✓ Display name: {channel_response.display_name}")
    print(f"✓ Is analyzed: {channel_response.is_analyzed}")
    print(f"✓ Keywords: {channel_response.keywords}")
    
    # 1.4 Update schema (partial)
    print("\n1.4 ChannelUpdateSchema (partial update):")
    
    update = ChannelUpdateSchema(
        subscribers=15000,
        keywords=["technology", "gadgets"]
    )
    print(f"✓ Update data: {update.model_dump(exclude_none=True)}")


# ============================================================================
# ПРИМЕР 2: Analysis schemas
# ============================================================================

def example_analysis_schemas():
    """Примеры работы с Analysis schemas."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 2: Analysis Schemas")
    print("=" * 80)
    
    # 2.1 Analysis Result
    print("\n2.1 AnalysisResultSchema:")
    
    analysis = AnalysisResultSchema(
        audience="IT-специалисты 25-40 лет, интересующиеся технологиями",
        keywords=["python", "django", "backend", "devops"],
        tone="Профессиональный, с техническими деталями",
        source="llm",
        confidence=0.9
    )
    
    print(f"✓ From LLM: {analysis.is_from_llm}")
    print(f"✓ Has keywords: {analysis.has_keywords}")
    print(f"✓ Keywords count: {len(analysis.keywords)}")
    print(f"✓ Confidence: {analysis.confidence * 100}%")
    
    # 2.2 Fallback analysis
    print("\n2.2 Fallback AnalysisResultSchema:")
    
    fallback = AnalysisResultSchema(
        audience="Не удалось получить анализ от LLM",
        keywords=["tech", "news"],
        tone="",
        source="fallback",
        confidence=0.5
    )
    
    print(f"✓ Is fallback: {fallback.is_fallback}")
    print(f"✓ Confidence: {fallback.confidence * 100}%")
    
    # 2.3 Full Analysis Response
    print("\n2.3 AnalysisResponseSchema:")
    
    response = AnalysisResponseSchema(
        channel_id=123,
        identifier="technews",
        is_id_based=False,
        title="Tech News",
        subscribers=10000,
        analysis=analysis,
        analyzed_posts=50,
        analysis_duration_ms=5000
    )
    
    print(f"✓ Channel: {response.display_name}")
    print(f"✓ Analyzed {response.analyzed_posts} posts")
    print(f"✓ Duration: {response.analysis_duration_ms}ms")
    print(f"✓ Keywords: {response.analysis.keywords}")


# ============================================================================
# ПРИМЕР 3: Similarity schemas
# ============================================================================

def example_similarity_schemas():
    """Примеры работы с Similarity schemas."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 3: Similarity Schemas")
    print("=" * 80)
    
    # 3.1 Similarity Request
    print("\n3.1 SimilarityRequestSchema:")
    
    request = SimilarityRequestSchema(
        identifier="@technews",
        top_n=10,
        min_score=0.5
    )
    print(f"✓ Request: {request.model_dump()}")
    
    # 3.2 Similar Channel
    print("\n3.2 SimilarChannelSchema:")
    
    similar = SimilarChannelSchema(
        channel_id=456,
        identifier="devnews",
        is_id_based=False,
        title="Dev News",
        description="Developer news",
        subscribers=8000,
        keywords=["python", "javascript", "devops"],
        score=0.85,
        common_keywords=["python", "devops"]
    )
    
    print(f"✓ Channel: {similar.display_name}")
    print(f"✓ Relevance: {similar.relevance_percent}%")
    print(f"✓ Link: {similar.telegram_link}")
    print(f"✓ Common keywords: {similar.common_keywords}")
    
    # 3.3 Similarity Result
    print("\n3.3 SimilarityResultSchema:")
    
    result = SimilarityResultSchema(
        target_channel_id=123,
        target_identifier="technews",
        target_keywords=["python", "django", "backend"],
        similar_channels=[similar],
        total_found=50,
        calculation_duration_ms=1200
    )
    
    print(f"✓ Has results: {result.has_results}")
    print(f"✓ Avg score: {result.avg_score:.2f}")
    print(f"✓ Top 3: {[ch.identifier for ch in result.top_3_channels]}")


# ============================================================================
# ПРИМЕР 4: Telegram schemas
# ============================================================================

def example_telegram_schemas():
    """Примеры работы с Telegram schemas."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 4: Telegram Schemas")
    print("=" * 80)
    
    # 4.1 Callback Data parsing
    print("\n4.1 CallbackDataSchema:")
    
    # Username callback
    callback1 = CallbackDataSchema.from_callback_string("analyze:technews:10")
    print(f"✓ Parsed username callback: {callback1.model_dump()}")
    print(f"  Back to string: {callback1.to_callback_string()}")
    
    # ID callback
    callback2 = CallbackDataSchema.from_callback_string("analyze:id:-1002508742544:25")
    print(f"✓ Parsed ID callback: {callback2.model_dump()}")
    print(f"  Back to string: {callback2.to_callback_string()}")
    
    # Website callback
    callback3 = CallbackDataSchema.from_callback_string("analyze_website|https%3A%2F%2Fexample.com|50")
    print(f"✓ Parsed website callback: {callback3.model_dump()}")
    print(f"  Back to string: {callback3.to_callback_string()}")
    
    # 4.2 Channel Info from Telegram
    print("\n4.2 ChannelInfoSchema:")
    
    channel_info = ChannelInfoSchema(
        id=-1002508742544,
        username="technews",
        title="Tech News",
        about="Latest tech news",
        participants_count=10000
    )
    
    print(f"✓ Is private: {channel_info.is_private}")
    print(f"✓ Identifier for DB: {channel_info.identifier_for_db}")


# ============================================================================
# ПРИМЕР 5: Standard Responses
# ============================================================================

def example_standard_responses():
    """Примеры стандартных ответов."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 5: Standard Responses")
    print("=" * 80)
    
    # 5.1 Success Response
    print("\n5.1 SuccessResponse:")
    
    success = SuccessResponse(
        message="Channel analyzed successfully",
        data={"channel_id": 123, "keywords": ["tech", "news"]}
    )
    print(f"✓ Success: {success.model_dump()}")
    
    # 5.2 Error Response
    print("\n5.2 ErrorResponse:")
    
    error = ErrorResponse(
        error="ChannelNotFoundError",
        message="Channel not found: @invalid_channel",
        details={"identifier": "@invalid_channel"}
    )
    print(f"✓ Error: {error.model_dump()}")


# ============================================================================
# ПРИМЕР 6: Валидация данных из dict
# ============================================================================

def example_validation_from_dict():
    """Пример валидации данных из словаря."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕР 6: Валидация из Dict")
    print("=" * 80)
    
    # Данные из внешнего источника (например, Telegram API)
    raw_data: Dict[str, Any] = {
        "id": -1002508742544,
        "username": "technews",
        "title": "Tech News",
        "about": "Latest technology news and updates",
        "participants_count": 10000
    }
    
    print("\n6.1 Валидация через schema:")
    try:
        validated = ChannelInfoSchema(**raw_data)
        print(f"✓ Данные валидированы успешно")
        print(f"  Normalized username: {validated.username}")
        print(f"  Identifier for DB: {validated.identifier_for_db}")
    except ValueError as e:
        print(f"✗ Ошибка валидации: {e}")
    
    # Некорректные данные
    print("\n6.2 Обработка некорректных данных:")
    bad_data: Dict[str, Any] = {
        "id": "not_a_number",  # Должно быть int
        "username": "@ab",  # Слишком короткий
        "title": "",  # Пустой
        "participants_count": -100  # Отрицательный
    }
    
    try:
        ChannelInfoSchema(**bad_data)
    except ValueError as e:
        print(f"✓ Отклонено с ошибкой: {e}")


# ============================================================================
# ЗАПУСК ПРИМЕРОВ
# ============================================================================

if __name__ == "__main__":
    example_channel_schemas()
    example_analysis_schemas()
    example_similarity_schemas()
    example_telegram_schemas()
    example_standard_responses()
    example_validation_from_dict()
    
    print("\n" + "=" * 80)
    print("✓ Все примеры выполнены успешно!")
    print("=" * 80)

