import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.databases import Base, get_db
# Importar modelos para registrar tablas en el metadata antes de create_all
from app.db.models import partidas_models, jugadores_models, cartas_models  # noqa: F401
from app.main import app as fastapi_app
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

import app.db.databases
app.db.databases.engine = engine
app.db.databases.SessionLocal = TestingSessionLocal

def override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

fastapi_app.dependency_overrides[get_db] = override_get_db

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