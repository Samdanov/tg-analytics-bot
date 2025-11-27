from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import config

DATABASE_URL = config.database_url

engine = create_async_engine(
    DATABASE_URL,
    echo=config.debug,
)

async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

Base = declarative_base()