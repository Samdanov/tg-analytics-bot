"""
Base Repository

Абстрактный базовый класс для всех репозиториев.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Type, Any
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_maker
from app.db.models import Base

# Generic type для модели
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(ABC, Generic[ModelType]):
    """
    Базовый репозиторий с CRUD операциями.
    
    Generic параметр ModelType определяет тип ORM модели.
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Args:
            model: SQLAlchemy модель (Channel, Post, etc)
        """
        self.model = model
    
    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        Получить запись по ID.
        
        Args:
            id: ID записи
        
        Returns:
            Model instance или None
        """
        async with async_session_maker() as session:
            return await session.get(self.model, id)
    
    async def get_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[ModelType]:
        """
        Получить все записи.
        
        Args:
            limit: Максимальное количество записей
            offset: Сдвиг
        
        Returns:
            Список моделей
        """
        async with async_session_maker() as session:
            query = select(self.model)
            
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def create(self, **kwargs) -> ModelType:
        """
        Создать новую запись.
        
        Args:
            **kwargs: Поля модели
        
        Returns:
            Созданная модель
        """
        async with async_session_maker() as session:
            instance = self.model(**kwargs)
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return instance
    
    async def update(
        self,
        id: int,
        **kwargs
    ) -> Optional[ModelType]:
        """
        Обновить запись по ID.
        
        Args:
            id: ID записи
            **kwargs: Поля для обновления
        
        Returns:
            Обновленная модель или None
        """
        async with async_session_maker() as session:
            instance = await session.get(self.model, id)
            if not instance:
                return None
            
            for key, value in kwargs.items():
                setattr(instance, key, value)
            
            await session.commit()
            await session.refresh(instance)
            return instance
    
    async def delete(self, id: int) -> bool:
        """
        Удалить запись по ID.
        
        Args:
            id: ID записи
        
        Returns:
            True если удалено, False если не найдено
        """
        async with async_session_maker() as session:
            instance = await session.get(self.model, id)
            if not instance:
                return False
            
            await session.delete(instance)
            await session.commit()
            return True
    
    async def count(self) -> int:
        """
        Подсчитать количество записей.
        
        Returns:
            Количество записей
        """
        async with async_session_maker() as session:
            from sqlalchemy import func
            result = await session.execute(
                select(func.count()).select_from(self.model)
            )
            return result.scalar_one()
    
    async def exists(self, id: int) -> bool:
        """
        Проверить существование записи.
        
        Args:
            id: ID записи
        
        Returns:
            True если существует
        """
        instance = await self.get_by_id(id)
        return instance is not None
    
    # Контекстный менеджер для работы с сессией
    def get_session(self) -> AsyncSession:
        """
        Получить сессию для сложных операций.
        
        Returns:
            AsyncSession
        
        Example:
            async with repo.get_session() as session:
                # Сложные операции с session
                pass
        """
        return async_session_maker()

