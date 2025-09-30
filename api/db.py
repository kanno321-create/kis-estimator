"""
KIS Estimator Database Module
Async SQLAlchemy connection using asyncpg for PostgreSQL
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import text, MetaData
from contextlib import asynccontextmanager
import logging

from api.config import config

logger = logging.getLogger(__name__)

# Convert postgres:// to postgresql+asyncpg://
db_url = config.SUPABASE_DB_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Create async engine
engine: AsyncEngine = create_async_engine(
    db_url,
    pool_size=config.DB_POOL_SIZE,
    max_overflow=config.DB_MAX_OVERFLOW,
    pool_timeout=config.DB_POOL_TIMEOUT,
    echo=config.DB_ECHO,
    pool_pre_ping=True,  # Verify connections before using
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Metadata for schema introspection
metadata = MetaData()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.

    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> dict:
    """
    Check database connection and basic health.

    Returns:
        dict with status, connected, timestamp, and optional error
    """
    try:
        async with AsyncSessionLocal() as session:
            # Simple connectivity check
            result = await session.execute(text("SELECT 1"))
            result.scalar()

            # Get current UTC timestamp
            result = await session.execute(
                text("SELECT now() AT TIME ZONE 'utc' as utc_now")
            )
            utc_now = result.scalar()

            return {
                "status": "ok",
                "connected": True,
                "timestamp": utc_now.isoformat() + "Z" if utc_now else "",
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "error",
            "connected": False,
            "error": str(e),
        }


async def init_db() -> None:
    """
    Initialize database connection pool and verify connectivity.
    Called on application startup.
    """
    try:
        health = await check_db_health()
        if health["status"] == "ok":
            logger.info(f"Database connected successfully at {health['timestamp']}")
        else:
            logger.error(f"Database connection failed: {health.get('error')}")
            raise RuntimeError("Database initialization failed")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise


async def close_db() -> None:
    """
    Close database connection pool.
    Called on application shutdown.
    """
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


@asynccontextmanager
async def db_transaction():
    """
    Context manager for database transactions with automatic rollback on error.

    Usage:
        async with db_transaction() as session:
            # do work
            await session.execute(...)
            # auto-commit on exit, auto-rollback on exception
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()