# tests/test_listar_partida.py

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.main import app as fastapi_app
from app.schemas.partidas import PartidaCreada, Partida, Jugador
from app.db.databases import Base
from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida
from app.db.models.jugadores_models import Jugador as JugadorModel

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




# Sobrescribe la dependencia get_db para usar la sesión de test en vez de la real
def override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


from app.db.models.jugadores_models import Jugador as JugadorModel
from app.db.models.partidas_models import Partida as PartidaModel

# Crea las tablas una sola vez antes de cualquier test
Base.metadata.create_all(bind=engine)
fastapi_app.dependency_overrides = {}
fastapi_app.dependency_overrides['app.db.databases.get_db'] = override_get_db

client = TestClient(fastapi_app)


def setup_function(function):
    # Limpia y recrea las tablas antes de cada test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def test_listar_partidas():
    # Testea el GET de /partidas poblando la base directamente con SQLAlchemy.
    from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida
    from app.db.models.jugadores_models import Jugador as JugadorModel

    import datetime
    session = TestingSessionLocal()

    # Crea dos jugadores creadores sin partida asignada
    jugador1 = JugadorModel(nombre="Jugador1", fecha_nacimiento=datetime.date(1990, 1, 1), orden_turno=1, id_avatar=1, id_partida=1)
    jugador2 = JugadorModel(nombre="Jugador2", fecha_nacimiento=datetime.date(1991, 2, 2), orden_turno=1, id_avatar=1, id_partida=2)
    session.add_all([jugador1, jugador2])
    session.commit()
    session.refresh(jugador1)
    session.refresh(jugador2)

    # Crea dos partidas en espera y una en juego usando los jugadores como creadores
    partida1 = PartidaModel(
        estado=EstadoPartida.en_espera,
        id_jugador_creador=jugador1.id_jugador,
        cantidad_jugadores=1,
        turno_actual=1,
        minimo=2,
        maximo=4
    )
    partida2 = PartidaModel(
        estado=EstadoPartida.en_espera,
        id_jugador_creador=jugador2.id_jugador,
        cantidad_jugadores=1,
        turno_actual=1,
        minimo=4,
        maximo=6
    )
    partida3 = PartidaModel(
        estado=EstadoPartida.en_juego,
        id_jugador_creador=jugador1.id_jugador,
        cantidad_jugadores=1,
        turno_actual=1,
        minimo=3,
        maximo=5
    )
    session.add_all([partida1, partida2, partida3])
    session.commit()
    session.refresh(partida1)
    session.refresh(partida2)
    session.refresh(partida3)

    # Actualiza el id_partida de los jugadores
    jugador1.id_partida = partida1.id_partida
    jugador2.id_partida = partida2.id_partida
    session.commit()
    session.close()

    response = client.get("/partidas")
    assert response.status_code == 200
    partidas = response.json()
    assert isinstance(partidas, list)

    # Como el endpoint solo lista partidas en espera, deberíamos obtener 2 y no 3.
    assert len(partidas) == 2
    assert partidas[0]["minimo"] == 2
    assert partidas[0]["maximo"] == 4


def test_listar_partidas_metodo_invalido():
    # Intentar listar partidas usando POST en vez de GET debe fallar.
    response = client.post("/partidas", json={})
    assert response.status_code in (405, 422)

def test_listar_partidas_parametros_invalidos():
    # Intentar pasar parámetros inválidos al GET debe ignorarlos o devolver error.
    response = client.get("/partidas", params={"minimo": "dos", "maximo": "cuatro"})
    # El endpoint no espera params, así que debe ignorarlos o devolver error
    assert response.status_code in (200, 422)


