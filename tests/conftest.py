import pytest
import pytest_asyncio
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.capa_0_definicion_bd.base_datos_sqlalchemy import Base, get_async_db as get_async_db_es
# Importar modelos reales para registrar tablas en el metadata antes de create_all
from app.capa_0_definicion_bd.models import partidas_models, jugadores_models, cartas_models  # noqa: F401
from app.main import app as fastapi_app
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Elimina test.db antes de la sesión
if os.path.exists("./test.db"):
    os.remove("./test.db")

ASYNC_SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
async_engine = create_async_engine(ASYNC_SQLALCHEMY_DATABASE_URL)
AsyncTestingSessionLocal = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_async_db():
    async with AsyncTestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# Nuevo: fixture opcional para tests que quieran usar la sesión asíncrona directamente
@pytest_asyncio.fixture
async def db_async():
    async with AsyncTestingSessionLocal() as session:
        try:
            yield session
            # Intentar commitear; si quedó en estado de rollback por un error controlado en el test, hacer rollback silencioso
            try:
                await session.commit()
            except Exception:
                await session.rollback()
        finally:
            pass

fastapi_app.dependency_overrides[get_async_db_es] = override_get_async_db

@pytest.fixture(scope="session", autouse=True)
def setup_db_once():
    # Crea las tablas una sola vez antes de todos los tests, usando el motor asíncrono
    import asyncio

    async def _create():
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create())
    yield
    async def _drop():
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    asyncio.run(_drop())
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest.fixture
def client(setup_db_once):
    with TestClient(fastapi_app) as c:
        yield c

# Cliente HTTP asíncrono para tests async
@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

# Sin puente sincrónico: todas las pruebas usan AsyncSession y async_client