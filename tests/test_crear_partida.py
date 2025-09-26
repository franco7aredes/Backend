import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.main import app as fastapi_app
from app.schemas.partidas import PartidaCreada, Partida, Jugador
from app.db.databases import Base, get_db
from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida
from app.db.models.jugadores_models import Jugador as JugadorModel


# Configuración de base de datos de test en memoria (Base de datos Temporal)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine)

def override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

# sobrescribo get_db globalmente
fastapi_app.dependency_overrides[get_db] = override_get_db

# crea un cliente de test con tablas de DB limpias y la dependencia sobrescrita
@pytest.fixture()
def client_with_db():
    # crear tablas
    Base.metadata.create_all(bind=engine)
    
    with TestClient(fastapi_app) as client:
        yield client
    
    # eliminar tablas
    Base.metadata.drop_all(bind=engine)

def test_crear_partida(client_with_db):
    payload = {
        "jugador_creador": "Juan",
        "fecha_nac": "2002-04-20",
        "minimo": 2,
        "maximo": 4
    }

    response = client_with_db.post("/partidas", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "mensaje" in data
    assert data["mensaje"] == "partida creada con exito"
    assert "id_partida" in data
    assert "id_jugador_creador" in data
    assert isinstance(data["id_partida"], int)
    assert isinstance(data["id_jugador_creador"], int)

def test_crear_partida_sin_jugador(client_with_db):
    payload = {
        "fecha_nac": "2002-04-20",
        "minimo": 2,
        "maximo": 4
    }

    response = client_with_db.post("/partidas", json=payload)
    assert response.status_code == 422


def test_crear_partida_fecha_invalida(client_with_db):
    payload = {
        "Nombre": "Juan",
        "fecha_nac": "10-03-2025",
        "minimo": 2,
        "maximo": 4
    }

    response = client_with_db.post("/partidas", json=payload)
    assert response.status_code == 422

def test_crear_partida_error_invalidacion(client_with_db):
    payload = {
        "Nombre": 32,
        "fecha_nac": "10-03-2025",
        "minimo": "dos",
        "maximo": "cuatro"
    }

    response = client_with_db.post("/partidas", json=payload)
    assert response.status_code == 422

    
