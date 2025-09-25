
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

def test_listar_partidas():
    """Testea el GET de /partidas poblando la base directamente con SQLAlchemy."""
    from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida
    from app.db.models.jugadores_models import Jugador as JugadorModel


    import datetime
    session = TestingSessionLocal()
    # Crea dos jugadores creadores
    jugador1 = JugadorModel(nombre="Jugador1", fecha_nacimiento=datetime.date(1990, 1, 1), orden_turno=1, id_avatar=1)
    jugador2 = JugadorModel(nombre="Jugador2", fecha_nacimiento=datetime.date(1991, 2, 2), orden_turno=1, id_avatar=1)
    session.add_all([jugador1, jugador2])
    session.commit()
    session.refresh(jugador1)
    session.refresh(jugador2)

    # Crea dos partidas en espera y una en juego
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
    session.close()

    response = client.get("/partidas")
    assert response.status_code == 200
    partidas = response.json()
    assert isinstance(partidas, list)
    # Como el endpoint solo lista partidas en espera, deberíamos obtener 2 y no 3.
    assert len(partidas) == 2
    assert partidas[0]["minimo"] == 2
    assert partidas[0]["maximo"] == 4
    assert partidas[1]["minimo"] == 4
    assert partidas[1]["maximo"] == 6

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
