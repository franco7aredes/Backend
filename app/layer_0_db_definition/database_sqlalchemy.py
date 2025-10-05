from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.settings import settings

# Base compartida para los ORM
Base = declarative_base()


# Configuración de la base de datos asíncrona
async_engine = create_async_engine(
    settings.DATABASE_URL_ASYNC, pool_pre_ping=True
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_async_db() -> AsyncSession:
    """Yield de una sesión asíncrona de la base de datos.
    
    Usar en endpoints con Depends(get_async_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
