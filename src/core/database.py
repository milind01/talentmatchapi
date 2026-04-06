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
database_url = settings.database_url
if "postgresql://" in database_url:
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
elif "postgresql+asyncpg://" not in database_url:
    database_url = database_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

async_engine = create_async_engine(
    database_url,
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
sync_database_url = settings.database_url
if "postgresql://" in sync_database_url:
    sync_database_url = sync_database_url.replace("postgresql://", "postgresql+psycopg2://")
elif "postgresql+asyncpg://" in sync_database_url:
    sync_database_url = sync_database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

sync_engine = create_engine(
    sync_database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)


def get_sync_db() -> Session:
    """Get synchronous database session for workers."""
    with Session(sync_engine) as session:
        yield session


def get_db_url() -> str:
    """Get the async database URL with asyncpg driver."""
    return database_url


async def init_db():
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def close_db():
    """Close database connection."""
    await async_engine.dispose()
    logger.info("Database connection closed")


__all__ = [
    "Base",
    "async_engine",
    "sync_engine",
    "AsyncSessionLocal",
    "get_async_db",
    "get_sync_db",
    "init_db",
    "close_db",
    "get_db_url",
]
