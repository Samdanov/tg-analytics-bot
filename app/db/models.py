from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    title = Column(Text)
    description = Column(Text)
    subscribers = Column(Integer)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)

    posts = relationship("Post", back_populates="channel", cascade="all, delete")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"))
    text = Column(Text)
    date = Column(TIMESTAMP)
    views = Column(Integer)
    forwards = Column(Integer)

    channel = relationship("Channel", back_populates="posts")
