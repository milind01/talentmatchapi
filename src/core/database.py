"""Database connection and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import NullPool
import logging

from src.core.config import settings


logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy base class for ORM models."""
    pass


# Async engine for FastAPI
async_engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.debug,
    poolclass=NullPool,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_async_db() -> AsyncSession:
    """Dependency for getting async database session."""
    async with AsyncSessionLocal() as session:
        yield session


# Sync engine for Celery workers
sync_engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)


def get_sync_db() -> Session:
    """Get synchronous database session for workers."""
    with Session(sync_engine) as session:
        yield session


async def init_db():
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def close_db():
    """Close database connection."""
    await async_engine.dispose()
    logger.info("Database connection closed")
