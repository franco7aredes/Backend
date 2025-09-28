import pytest
from fastapi.testclient import TestClient
from app.main import app as fastapi_app
from app.db.databases import SessionLocal
from app.db.models.cartas_models import Carta, PosicionCarta


# Reutiliza el cliente centralizado por conftest.py y la DB compartida
@pytest.fixture()
def client_with_db(client):
    return client


@pytest.fixture()
def setup_reponer(client_with_db):
    db = SessionLocal()
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

    # Asegurar que no haya cartas previas para esta partida (cuando los tests corren juntos)
    db.query(Carta).filter_by(id_partida=id_partida).delete()
    db.commit()

    # crear 10 cartas en el mazo con id_carta explícito
    for i in range(1, 11):
        carta = Carta(id_carta=i, id_partida=id_partida, id_jugador=None, posicion=PosicionCarta.mazo)
        db.add(carta)

    # Crear 3 cartas ya en la mano del jugador
    # continuar numeración para cartas en mano
    for j in range(11, 14):
        carta = Carta(id_carta=j, id_partida=id_partida, id_jugador=id_jugador, posicion=PosicionCarta.mano)
        db.add(carta)

    db.commit()
    db.close()

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
    db = SessionLocal()

    # poner 6 cartas en mano (ya está en el setup 3, agregamos 3 más)
    for i in range(14, 17):
        carta = Carta(id_carta=i, id_partida=id_partida, id_jugador=id_jugador, posicion=PosicionCarta.mano)
        db.add(carta)
    db.commit()
    db.close()

    response = client.put(f"/partida/{id_partida}/reponer", json={"jugador_id": id_jugador})
    assert response.status_code == 200
    data = response.json()
    assert data["mensaje"] == "El jugador ya tiene el maximo de cartas en la mano"


def test_reponer_mazo_vacio(setup_reponer):
    client, id_partida, id_jugador = setup_reponer
    db = SessionLocal()

    # Vaciar el mazo
    db.query(Carta).filter_by(id_partida=id_partida, id_jugador=None, posicion=PosicionCarta.mazo).delete()
    db.commit()
    db.close()

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
