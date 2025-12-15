"""
Use Cases Layer

Бизнес-логика приложения, организованная в виде use cases.
"""

from .analyze_channel import AnalyzeChannelUseCase
from .analyze_website import AnalyzeWebsiteUseCase
from .detect_proxy_channel import DetectProxyChannelUseCase, ProxyDetectionResult
from .parse_message import MessageParserService, ChannelInfo, WebsiteInfo

# Services
from .channel_service import add_channel_usecase, analyze_usecase, run_full_pipeline_usecase
from .similarity_service import recalc_for_channel, recalc_all
from .website_service import run_website_analysis_pipeline

__all__ = [
    # Use Cases
    "AnalyzeChannelUseCase",
    "AnalyzeWebsiteUseCase",
    "DetectProxyChannelUseCase",
    "ProxyDetectionResult",
    "MessageParserService",
    "ChannelInfo",
    "WebsiteInfo",
    # Services
    "add_channel_usecase",
    "analyze_usecase",
    "run_full_pipeline_usecase",
    "recalc_for_channel",
    "recalc_all",
    "run_website_analysis_pipeline",
]
