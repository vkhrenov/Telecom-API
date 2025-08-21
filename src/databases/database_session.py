from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.configs.settings import get_settings
from typing import AsyncGenerator

def numbering_async_engine(uri: URL) -> AsyncEngine:
    return create_async_engine(
        uri,
        pool_pre_ping=True,
        pool_size= 5,
        max_overflow= 10,
        pool_timeout=30.0,
        pool_recycle=600
    )

_NUMBERING_ASYNC_ENGINE = numbering_async_engine(get_settings().sqlalchemy_database_uri)
_NUMBERING_ASYNC_SESSIONMAKER = async_sessionmaker(_NUMBERING_ASYNC_ENGINE, expire_on_commit=False)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with _NUMBERING_ASYNC_SESSIONMAKER() as session:
        yield session



