"""
Domain Services

Бизнес-логика, которая не принадлежит конкретной entity.
"""

from .proxy_detector import ProxyChannelDetector, ProxyDetectionResult

__all__ = [
    "ProxyChannelDetector",
    "ProxyDetectionResult",
]

