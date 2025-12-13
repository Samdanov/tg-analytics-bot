"""
Use Cases Layer

Бизнес-логика приложения, организованная в виде use cases.
Каждый use case представляет собой отдельную бизнес-операцию.
"""

from .analyze_channel import AnalyzeChannelUseCase
from .analyze_website import AnalyzeWebsiteUseCase
from .detect_proxy_channel import DetectProxyChannelUseCase, ProxyDetectionResult
from .parse_message import MessageParserService, ChannelInfo, WebsiteInfo

__all__ = [
    "AnalyzeChannelUseCase",
    "AnalyzeWebsiteUseCase",
    "DetectProxyChannelUseCase",
    "ProxyDetectionResult",
    "MessageParserService",
    "ChannelInfo",
    "WebsiteInfo",
]

