"""
Async database engine + session factory.

`get_db` is a FastAPI dependency: each request gets its own AsyncSession,
which is closed automatically when the request finishes. This is the
dependency-injection pattern you'll reuse for auth in Week 2.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.DEBUG,        # log SQL in dev, silent in prod
    pool_pre_ping=True,         # recycle dead connections gracefully
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session