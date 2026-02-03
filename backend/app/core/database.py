"""Database configuration and session management"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings
import ssl

# SSL context for asyncpg - prefer connection but don't verify cert for internal Fly.io network
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Create async engine with SSL support
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    future=True,
    connect_args={
        "ssl": ssl_context,
        "server_settings": {
            "application_name": "soccerschedules_backend"
        }
    }
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create base class for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database - create all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
