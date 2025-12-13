"""
Domain Entities

Основные бизнес-сущности системы.
"""

from .channel import ChannelEntity
from .analysis import AnalysisResult

__all__ = [
    "ChannelEntity",
    "AnalysisResult",
]

