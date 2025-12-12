from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
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