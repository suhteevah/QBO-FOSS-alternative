"""Database engine and session factories."""

from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from openledger.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

# Async engine (for FastAPI)
engine_kwargs = {"echo": settings.debug}
if _is_sqlite:
    # SQLite needs check_same_thread=False for async use
    engine_kwargs["connect_args"] = {"check_same_thread": False}

async_engine = create_async_engine(settings.database_url, **engine_kwargs)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine (for Alembic and CLI)
sync_engine = create_engine(settings.database_url_sync, echo=settings.debug)
SyncSessionLocal = sessionmaker(bind=sync_engine)


# Enable WAL mode and foreign keys for SQLite
if _is_sqlite:
    @sa_event.listens_for(sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
