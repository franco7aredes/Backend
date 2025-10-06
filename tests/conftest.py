import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.capa_0_definicion_bd.base_datos.base_datos_sincronica import Base, get_db
from app.capa_0_definicion_bd.base_datos_sqlalchemy import get_async_db as get_async_db_es
# Importar modelos reales para registrar tablas en el metadata antes de create_all
from app.capa_0_definicion_bd.models import partidas_models, jugadores_models, cartas_models  # noqa: F401
from app.capa_3_api.main import app as fastapi_app
from fastapi.testclient import TestClient

# Elimina test.db antes de la sesión
if os.path.exists("./test.db"):
    os.remove("./test.db")
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

import app.capa_0_definicion_bd.base_datos.base_datos_sincronica as dbsync
dbsync.engine = engine
dbsync.SessionLocal = TestingSessionLocal

def override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

fastapi_app.dependency_overrides[get_db] = override_get_db

# --- Sobreescritura de la base de datos asíncrona ---
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

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

fastapi_app.dependency_overrides[get_async_db_es] = override_get_async_db

@pytest.fixture(scope="session", autouse=True)
def setup_db_once():
    # Crea las tablas una sola vez antes de todos los tests
    Base.metadata.create_all(bind=engine)
    yield
    # Borra las tablas y elimina el archivo al final
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest.fixture
def client(setup_db_once):
    with TestClient(fastapi_app) as c:
        yield c