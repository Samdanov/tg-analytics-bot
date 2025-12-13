"""
Schemas Layer (DTO)

Pydantic models для валидации и сериализации данных.
Заменяют Dict[str, Any] на типизированные модели.
"""

from .base import BaseSchema, SuccessResponse, ErrorResponse
from .channel import (
    ChannelIdentifierSchema,
    ChannelCreateSchema,
    ChannelResponseSchema,
    ChannelUpdateSchema,
    ChannelWithPostsSchema,
)
from .analysis import (
    AnalysisRequestSchema,
    AnalysisResponseSchema,
    AnalysisResultSchema,
)
from .similarity import (
    SimilarityRequestSchema,
    SimilarityResultSchema,
    SimilarChannelSchema,
)
from .telegram import (
    CallbackDataSchema,
    ChannelInfoSchema,
)

__all__ = [
    # Base
    "BaseSchema",
    "SuccessResponse",
    "ErrorResponse",
    # Channel
    "ChannelIdentifierSchema",
    "ChannelCreateSchema",
    "ChannelResponseSchema",
    "ChannelUpdateSchema",
    "ChannelWithPostsSchema",
    # Analysis
    "AnalysisRequestSchema",
    "AnalysisResponseSchema",
    "AnalysisResultSchema",
    # Similarity
    "SimilarityRequestSchema",
    "SimilarityResultSchema",
    "SimilarChannelSchema",
    # Telegram
    "CallbackDataSchema",
    "ChannelInfoSchema",
]

