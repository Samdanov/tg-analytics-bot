"""
Domain Layer

Содержит бизнес-логику, не зависящую от внешних фреймворков:
- Entities: Доменные сущности
- Value Objects: Неизменяемые объекты со своей логикой
- Services: Доменные сервисы (бизнес-правила)
- Exceptions: Доменные исключения
"""

from .exceptions import (
    DomainError,
    ChannelNotFoundError,
    InvalidChannelIdentifierError,
    ProxyChannelDetectedError,
    AnalysisError,
    SimilarityCalculationError,
)

from .value_objects import ChannelIdentifier

from .entities import (
    ChannelEntity,
    AnalysisResult,
)

from .services import (
    ProxyChannelDetector,
    ProxyDetectionResult,
)

__all__ = [
    # Exceptions
    "DomainError",
    "ChannelNotFoundError",
    "InvalidChannelIdentifierError",
    "ProxyChannelDetectedError",
    "AnalysisError",
    "SimilarityCalculationError",
    # Value Objects
    "ChannelIdentifier",
    # Entities
    "ChannelEntity",
    "AnalysisResult",
    # Services
    "ProxyChannelDetector",
    "ProxyDetectionResult",
]

