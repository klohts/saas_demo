from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from .config import settings
import logging

logger = logging.getLogger("db")

# Create async engine
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

# Async session factory
async_session_maker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

async def init_db() -> None:
    """Initialize the database schema asynchronously."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.exception("DB init failed: %s", e)

# Dependency helper
async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
