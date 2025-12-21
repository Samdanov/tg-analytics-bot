from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"))
    text = Column(Text)
    date = Column(TIMESTAMP)
    views = Column(Integer)
    forwards = Column(Integer)

    channel = relationship("Channel", back_populates="posts")

# -------------------------
# CHANNEL
# -------------------------
class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(Text, unique=True, nullable=False)
    title = Column(Text)
    description = Column(Text)
    subscribers = Column(Integer)
    category = Column(Text, index=True)  # Категория из Excel (48 тем) - PRIMARY TOPIC

    keywords = Column(ARRAY(Text))
    last_update = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)

    posts = relationship("Post", back_populates="channel", cascade="all, delete")
    keywords_cache = relationship("KeywordsCache", back_populates="channel", uselist=False, cascade="all, delete")
    analytics_results = relationship("AnalyticsResults", back_populates="channel", cascade="all, delete")


# -------------------------
# KEYWORDS CACHE
# -------------------------
class KeywordsCache(Base):
    __tablename__ = "keywords_cache"

    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True)
    audience = Column(Text)
    tone = Column(Text)  # Тональность канала
    keywords_json = Column(Text)   # jsonb → текст, хранится нормально
    created_at = Column(TIMESTAMP)

    channel = relationship("Channel", back_populates="keywords_cache")


# -------------------------
# ANALYTICS RESULTS
# -------------------------
class AnalyticsResults(Base):
    __tablename__ = "analytics_results"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"))
    similar_channels_json = Column(Text)
    created_at = Column(TIMESTAMP)

    channel = relationship("Channel", back_populates="analytics_results")


# -------------------------
# USER (для подписок и лимитов)
# -------------------------
class User(Base):
    __tablename__ = "users"

    # Существующие колонки в БД
    id = Column(Integer, primary_key=True, index=True)  # Внутренний ID
    telegram_id = Column(Integer, nullable=True, index=True)  # Telegram user ID
    created_at = Column(TIMESTAMP, default=datetime.utcnow)  # Дата регистрации
    
    # Новые колонки (будут добавлены позже, пока опциональные)
    # Используем nullable=True и дефолты в коде, чтобы не падать если колонок нет
    username = Column(Text, nullable=True)  # Telegram username (без @)
    first_name = Column(Text, nullable=True)  # Имя пользователя
    
    # Подписка
    subscription_type = Column(Text, nullable=True)  # "free", "premium", "admin"
    subscription_expires_at = Column(TIMESTAMP, nullable=True)  # Дата окончания подписки
    
    # Лимиты запросов
    queries_used = Column(Integer, nullable=True)  # Использовано запросов
    queries_limit = Column(Integer, nullable=True)  # Лимит запросов (10 для free, -1 для безлимита)
    queries_reset_at = Column(TIMESTAMP, nullable=True)  # Дата сброса лимита (если нужна периодика)
    
    # Статус
    is_active = Column(Boolean, nullable=True)  # Активен ли пользователь
    is_banned = Column(Boolean, nullable=True)  # Забанен ли
    
    # Метаданные
    last_activity_at = Column(TIMESTAMP, nullable=True)  # Последняя активность
    
    # Примечания (для админов)
    notes = Column(Text, nullable=True)  # Заметки об пользователе
    
    # Методы для получения значений с дефолтами
    def get_subscription_type(self) -> str:
        """Возвращает тип подписки с дефолтом 'free'."""
        return self.subscription_type or "free"
    
    def get_queries_used(self) -> int:
        """Возвращает использованные запросы с дефолтом 0."""
        return self.queries_used if self.queries_used is not None else 0
    
    def get_queries_limit(self) -> int:
        """Возвращает лимит запросов с дефолтом 10."""
        return self.queries_limit if self.queries_limit is not None else 10
    
    def get_is_active(self) -> bool:
        """Возвращает статус активности с дефолтом True."""
        return self.is_active if self.is_active is not None else True
    
    def get_is_banned(self) -> bool:
        """Возвращает статус бана с дефолтом False."""
        return self.is_banned if self.is_banned is not None else False