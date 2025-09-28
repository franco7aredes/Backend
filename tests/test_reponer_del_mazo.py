import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.main import app as fastapi_app
from app.db.databases import get_db, Base, engine
from app.db.models.cartas_models import Carta, PosicionCarta


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


@pytest.fixture()
def setup_reponer(client_with_db):
    db = next(override_get_db())
    payload = {
        "jugador_creador": "pepito",
        "fecha_nac": "2002-09-15",
        "minimo": 2,
        "maximo": 5
    }
    response = client_with_db.post("/partidas", json=payload)
    data = response.json()
    id_partida = data["id_partida"]
    id_jugador = data["id_jugador_creador"]

    # crear 10 cartas en el mazo
    for i in range(10):
        carta = Carta(id_partida=id_partida, id_jugador=None, posicion=PosicionCarta.mazo)
        db.add(carta)

    # Crear 3 cartas ya en la mano del jugador
    for j in range(3):
        carta = Carta(id_partida=id_partida, id_jugador=id_jugador, posicion=PosicionCarta.mano)
        db.add(carta)

    db.commit()

    return client_with_db, id_partida, id_jugador


def test_reponer_del_mazo(setup_reponer):
    client, id_partida, id_jugador = setup_reponer

    response = client.put(f"/partida/{id_partida}/reponer", json={"jugador_id": id_jugador})

    assert response.status_code == 200
    data = response.json()
    assert "mensaje" in data
    assert "cartas" in data
    assert len(data["cartas"]) == 3
    for carta in data["cartas"]:
        assert carta["posicion"] == "mano"

def test_reponer_maximo_cartas(setup_reponer):
    client, id_partida, id_jugador = setup_reponer
    db = next(override_get_db())

    # poner 6 cartas en mano (ya está en el setup 3, agregamos 3 más)
    for i in range(3):
        carta = Carta(id_partida=id_partida, id_jugador=id_jugador, posicion=PosicionCarta.mano)
        db.add(carta)
    db.commit()

    response = client.put(f"/partida/{id_partida}/reponer", json={"jugador_id": id_jugador})
    assert response.status_code == 200
    data = response.json()
    assert data["mensaje"] == "El jugador ya tiene el maximo de cartas en la mano"


def test_reponer_mazo_vacio(setup_reponer):
    client, id_partida, id_jugador = setup_reponer
    db = next(override_get_db())

    # Vaciar el mazo
    db.query(Carta).filter_by(id_partida=id_partida, id_jugador=None, posicion=PosicionCarta.mazo).delete()
    db.commit()

    response = client.put(f"/partida/{id_partida}/reponer", json={"jugador_id": id_jugador})
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "No hay cartas disponibles en el mazo"


def test_reponer_jugador_inexistente(setup_reponer):
    client, id_partida, _ = setup_reponer

    response = client.put(f"/partida/{id_partida}/reponer", json={"jugador_id": 9999})
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Jugador no encontrado"

def test_reponer_partida_inexistente(setup_reponer):
    client, _, id_jugador = setup_reponer

    response = client.put(f"/partida/9999/reponer", json={"jugador_id": id_jugador})
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Partida no encontrada"
