
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.schemas.partidas import PartidaCreada, Partida, Jugador
from app.db.databases import Base

# Configuración de base de datos de test en memoria (Base de datos Temporal)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Parchea el engine y SessionLocal globales para que la app y los modelos usen la base de test
import app.db.databases
app.db.databases.engine = engine
app.db.databases.SessionLocal = TestingSessionLocal

# Crea las tablas una sola vez antes de cualquier test
Base.metadata.create_all(bind=engine)
from app.main import app as fastapi_app
fastapi_app.dependency_overrides = {}
fastapi_app.dependency_overrides['app.db.databases.get_db'] = lambda: (s for s in [TestingSessionLocal()])

client = TestClient(fastapi_app)

def test_listar_partidas():
    """ testea el GET de /partidas """
    response = client.get("/partidas")
    assert response.status_code == 200

def test_crear_partida_exitoso():
    """ testea el POST de /partidas """
    payload = {
        "jugador_creador": "John salchichon",
        "fecha_nac":"1980-04-20",
        "minimo": 2,
        "maximo": 4
    }
    response = client.post("/partidas", json=payload)
    # Pydantic/FASTApi devuelven 422 en caso de datos invalidos
    # y 201 en caso de bien hecho
    assert response.status_code == 201
    assert response.json() == {
        "mensaje": f"partida creada con exito"
    }

def test_crear_partida_error_validacion():
    payload = {
        "jugador_creador": "John salchichon",
        "fecha_nac":"1980-04-20",
        "minimo": "dos",
        "maximo": "cuatro"
    }
    response = client.post("/partidas", json=payload)
    assert response.status_code == 422
    # este assert busca el error en particular: el de dar un str para
    # un int
    assert response.json()['detail'][0]['type'] == 'int_parsing'
