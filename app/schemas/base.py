"""
Base Schemas

Базовые классы для всех Pydantic schemas.
"""

from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """
    Базовый класс для всех schemas.
    
    Настройки:
    - from_attributes: Позволяет создавать из ORM моделей
    - populate_by_name: Позволяет использовать alias
    - str_strip_whitespace: Удаляет пробелы из строк
    """
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class TimestampMixin(BaseModel):
    """Mixin для моделей с временными метками."""
    
    created_at: Optional[datetime] = Field(
        None,
        description="Дата создания записи"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Дата последнего обновления"
    )


class SuccessResponse(BaseSchema):
    """
    Стандартный успешный ответ.
    
    Используется для унификации ответов API.
    """
    
    success: bool = Field(True, description="Статус выполнения")
    message: str = Field(..., description="Сообщение о результате")
    data: Optional[Dict[str, Any]] = Field(None, description="Данные ответа")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Channel analyzed successfully",
                "data": {"channel_id": 123, "keywords": ["tech", "news"]}
            }
        }


class ErrorResponse(BaseSchema):
    """
    Стандартный ответ с ошибкой.
    
    Используется для унификации обработки ошибок.
    """
    
    success: bool = Field(False, description="Статус выполнения")
    error: str = Field(..., description="Тип ошибки")
    message: str = Field(..., description="Описание ошибки")
    details: Optional[Dict[str, Any]] = Field(None, description="Детали ошибки")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "ChannelNotFoundError",
                "message": "Channel not found: @invalid_channel",
                "details": {"identifier": "@invalid_channel"}
            }
        }


class PaginationParams(BaseSchema):
    """Параметры пагинации."""
    
    page: int = Field(1, ge=1, description="Номер страницы")
    page_size: int = Field(10, ge=1, le=100, description="Размер страницы")
    
    @property
    def offset(self) -> int:
        """Вычисляет offset для SQL запроса."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Возвращает limit для SQL запроса."""
        return self.page_size


class PaginatedResponse(BaseSchema):
    """Ответ с пагинацией."""
    
    items: list = Field(..., description="Элементы текущей страницы")
    total: int = Field(..., description="Всего элементов")
    page: int = Field(..., description="Текущая страница")
    page_size: int = Field(..., description="Размер страницы")
    total_pages: int = Field(..., description="Всего страниц")
    
    @classmethod
    def create(
        cls,
        items: list,
        total: int,
        pagination: PaginationParams
    ) -> "PaginatedResponse":
        """
        Создаёт paginated response из данных.
        
        Args:
            items: Элементы текущей страницы
            total: Общее количество элементов
            pagination: Параметры пагинации
        
        Returns:
            PaginatedResponse
        """
        total_pages = (total + pagination.page_size - 1) // pagination.page_size
        
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages
        )

