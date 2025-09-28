# tests/test_api_scrum14.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sys
import os


# -----------------------------------------------------------
# 1️⃣ Configurar la ruta raíz del proyecto
# -----------------------------------------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# -----------------------------------------------------------
# 2️⃣ Importar tu app y modelos
# -----------------------------------------------------------
from app.main import app as fastapi_app
from app.db.databases import Base, get_db
from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida
from app.db.models.jugadores_models import Jugador as JugadorModel

# -----------------------------------------------------------
# 3️⃣ Configurar la base de datos de test en memoria
# -----------------------------------------------------------
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # 🔹 Necesario para SQLite en memoria
    poolclass=StaticPool,                        # 🔹 Compartir la misma DB entre sesiones
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# -----------------------------------------------------------
# 4️⃣ Sobrescribir dependencia get_db para usar DB de test
# -----------------------------------------------------------
@pytest.fixture(scope="session")
def override_db_dependency():
    """Sobrescribe get_db para usar la DB de test."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield
    fastapi_app.dependency_overrides.pop(get_db)

# -----------------------------------------------------------
# 5️⃣ Fixture del cliente de test con DB inicializada
# -----------------------------------------------------------
@pytest.fixture()
def client_with_db_setup(override_db_dependency):
    """Crea un cliente de test con tablas de DB limpias y la dependencia sobrescrita."""
    # 🔹 Setup: Crear tablas
    Base.metadata.create_all(bind=engine)
    
    with TestClient(fastapi_app) as client:
        yield client
        
    # 🔹 Teardown: Eliminar tablas
    Base.metadata.drop_all(bind=engine)

# ===========================================================
# 7️⃣ Tests PATCH /partidas/{partida_id}/iniciar
# ===========================================================
def test_iniciar_partida_con_exito(client_with_db_setup):
    with TestingSessionLocal() as session:
        partida = PartidaModel(
            id_partida=2,
            estado=EstadoPartida.en_espera,
            cantidad_jugadores=2,
            maximo=4,
            minimo=2,
            id_jugador_creador=1,
            turno_actual=1
        )
        session.add(partida)
        session.commit()
        session.refresh(partida)

    response = client_with_db_setup.patch("/partidas/2/iniciar", json={})
    assert response.status_code == 200
    assert response.json()["mensaje"] == "La partida comenzo"

    with TestingSessionLocal() as session:
        partida_actualizada = session.query(PartidaModel).filter(PartidaModel.id_partida==2).first()
        assert partida_actualizada.estado == EstadoPartida.en_juego

    # Aca voy a testear que se hallan enviado las cartas a cada jugador

def test_iniciar_partida_ya_iniciada_lanza_error(client_with_db_setup):
    with TestingSessionLocal() as session:
        partida = PartidaModel(
            id_partida=3,
            estado=EstadoPartida.en_juego,
            cantidad_jugadores=2,
            maximo=4,
            minimo=2,
            id_jugador_creador=1,
            turno_actual=1
        )
        session.add(partida)
        session.commit()
        session.refresh(partida)

    response = client_with_db_setup.patch("/partidas/3/iniciar", json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "La partida ya esta en juego"

def test_iniciar_partida_no_encontrada_lanza_error(client_with_db_setup):
    response = client_with_db_setup.patch("/partidas/999/iniciar", json={})
    assert response.status_code == 404
    assert response.json()["detail"] == "Partida no encontrada"

# ===========================================================
# 8️⃣ Tests PUT /partidas/{partida_id}/unirse
# ===========================================================
def test_unirse_a_partida_con_exito(client_with_db_setup):
    with TestingSessionLocal() as session:
        partida = PartidaModel(
            id_partida=4,
            estado=EstadoPartida.en_espera,
            cantidad_jugadores=0,
            maximo=4,
            minimo=2,
            id_jugador_creador=1,
            turno_actual=1
        )
        session.add(partida)
        session.commit()
        session.refresh(partida)

    jugador_data = {"nombre": "TestJugador", "fecha_nacimiento": "1990-01-01T00:00:00"}
    response = client_with_db_setup.put("/partidas/4/unirse", json=jugador_data)
    assert response.status_code == 201
    assert response.json()["mensaje"] == "jugador agregado"
    assert "jugador_id" in response.json()

    with TestingSessionLocal() as session:
        partida_actualizada = session.query(PartidaModel).filter(PartidaModel.id_partida==4).first()
        assert partida_actualizada.cantidad_jugadores == 1

def test_unirse_a_partida_llena_lanza_error(client_with_db_setup):
    with TestingSessionLocal() as session:
        partida = PartidaModel(
            id_partida=5,
            estado=EstadoPartida.en_espera,
            cantidad_jugadores=4,
            maximo=4,
            minimo=2,
            id_jugador_creador=1,
            turno_actual=1
        )
        session.add(partida)
        session.commit()
        session.refresh(partida)

    jugador_data = {"nombre": "JugadorExtra", "fecha_nacimiento": "1990-01-01T00:00:00"}
    response = client_with_db_setup.put("/partidas/5/unirse", json=jugador_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "La partida ya tiene el máximo de jugadores"

def test_unirse_a_partida_no_encontrada_lanza_error(client_with_db_setup):
    jugador_data = {"nombre": "JugadorInexistente", "fecha_nacimiento": "1990-01-01T00:00:00"}
    response = client_with_db_setup.put("/partidas/999/unirse", json=jugador_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Partida no encontrada"

