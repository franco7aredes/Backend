"""Infraestructura de SQLAlchemy asíncrona (capa 0).

- Base: clase base de modelos ORM
- async_engine y AsyncSessionLocal: motor y fábrica de sesiones asíncronas
- get_async_db: dependencia para FastAPI que maneja commit/rollback por request
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.settings import settings

# Base compartida para todos los modelos ORM
Base = declarative_base()


# Motor y sesión asíncronos
async_engine = create_async_engine(settings.DATABASE_URL_ASYNC, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_db() -> AsyncSession:
    """Dependencia de FastAPI que provee una AsyncSession por request.

    Asegura commit si todo sale OK o rollback ante excepción.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
