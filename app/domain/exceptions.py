"""
Domain Exceptions

Доменные исключения для бизнес-логики.
Независимы от инфраструктуры (БД, API, etc).
"""


class DomainError(Exception):
    """Базовый класс для всех доменных исключений."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ChannelNotFoundError(DomainError):
    """Канал не найден в системе."""
    
    def __init__(self, identifier: str):
        super().__init__(
            f"Channel not found: {identifier}",
            {"identifier": identifier}
        )


class InvalidChannelIdentifierError(DomainError):
    """Некорректный идентификатор канала."""
    
    def __init__(self, raw_value: str, reason: str = None):
        details = {"raw_value": raw_value}
        if reason:
            details["reason"] = reason
        
        message = f"Invalid channel identifier: {raw_value}"
        if reason:
            message += f" ({reason})"
        
        super().__init__(message, details)


class ProxyChannelDetectedError(DomainError):
    """Обнаружен канал-прокладка."""
    
    def __init__(self, identifier: str, linked_channels: list):
        super().__init__(
            f"Proxy channel detected: {identifier}",
            {
                "identifier": identifier,
                "linked_channels": linked_channels[:10],  # Топ-10
                "total_links": len(linked_channels)
            }
        )
        self.linked_channels = linked_channels


class AnalysisError(DomainError):
    """Ошибка при анализе канала."""
    pass


class SimilarityCalculationError(DomainError):
    """Ошибка при расчёте похожести."""
    pass

