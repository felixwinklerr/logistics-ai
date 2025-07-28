"""Database configuration and session management"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from geoalchemy2 import Geography

from app.core.config import settings


# Database engine with psycopg driver
engine = create_async_engine(
    settings.get_database_url,
    echo=settings.debug,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
    # psycopg-specific configuration
    connect_args={"timeout": 30},
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models"""
    
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s"
        }
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database and create tables"""
    try:
        async with engine.begin() as conn:
            # Create PostGIS extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            
            # Import all models to register them
            from app.models import orders, subcontractors, users, documents  # noqa
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        # Log the error but don't fail the application startup
        # This allows the API to start even if database is not available
        from loguru import logger
        logger.warning(f"Database initialization failed: {e}")
        logger.info("API will start without database connectivity - some endpoints may not work")


async def close_db() -> None:
    """Close database connections"""
    await engine.dispose()
