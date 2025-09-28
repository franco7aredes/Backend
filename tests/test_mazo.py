

import pytest
from fastapi.testclient import TestClient
from app.main import app as fastapi_app
from app.db.databases import get_db, Base, engine
from app.db.models.partidas_models import Partida, EstadoPartida
from app.db.models.jugadores_models import Jugador
from app.db.models.cartas_models import Carta, PosicionCarta
import datetime

@pytest.fixture
def client():
    return TestClient(fastapi_app)

@pytest.fixture
def setup_db(client):
    from app.db.models.cartas_models import Carta, PosicionCarta
    from app.db.databases import get_db
    db = next(get_db())
    # Crear partida y jugador usando el endpoint
    payload = {
        "jugador_creador": "TestJugador",
        "fecha_nac": "2004-11-19",
        "minimo": 2,
        "maximo": 4
    }
    response = client.post("/partidas", json=payload)
    assert response.status_code == 201
    data = response.json()
    id_partida = data["id_partida"]
    id_jugador = data["id_jugador_creador"]

    # Obtener instancia de partida y jugador desde la base de datos
    from app.db.models.partidas_models import Partida
    from app.db.models.jugadores_models import Jugador
    partida = db.query(Partida).filter_by(id_partida=id_partida).first()
    jugador = db.query(Jugador).filter_by(id_jugador=id_jugador).first()

    # Crear carta para el jugador (PK compuesta requiere id_carta explícito)
    carta = Carta(id_carta=1, id_partida=id_partida, id_jugador=id_jugador, posicion=PosicionCarta.mano)
    db.add(carta)
    db.commit()
    db.refresh(carta)

    return db, partida, jugador, carta


def test_descartar_carta(client, setup_db):
    db, partida, jugador, carta = setup_db
    # Llamar al endpoint para descartar carta
    response = client.patch(f"/partida/{partida.id_partida}/descartar", json={"jugador_id": jugador.id_jugador})
    assert response.status_code == 200
    data = response.json()
    assert "mensaje" in data
    # Verificar en la base de datos que la carta fue descartada
    carta_actualizada = db.query(Carta).filter_by(id_carta=carta.id_carta).first()
    db.refresh(carta_actualizada)
    assert carta_actualizada.id_jugador is None
    assert carta_actualizada.posicion.name == "descarte"


def test_descartar_carta_sin_cartas(client, setup_db):
    db, partida, jugador, carta = setup_db
    # Eliminar la carta del jugador
    db.delete(carta)
    db.commit()
    # Llamar al endpoint para descartar carta
    response = client.patch(f"/partida/{partida.id_partida}/descartar", json={"jugador_id": jugador.id_jugador})
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "No se encontró carta para descartar en esta partida"


def test_descartar_carta_partida_inexistente(client, setup_db):
    db, partida, jugador, carta = setup_db
    response = client.patch(f"/partida/9999/descartar", json={"jugador_id": jugador.id_jugador})
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "No se encontró carta para descartar en esta partida"


def test_descartar_carta_jugador_inexistente(client, setup_db):
    db, partida, jugador, carta = setup_db
    response = client.patch(f"/partida/{partida.id_partida}/descartar", json={"jugador_id": 9999})
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "No se encontró carta para descartar en esta partida"


def test_descartar_carta_varias_cartas(client, setup_db):
    db, partida, jugador, carta1 = setup_db
    # Crear segunda carta para el mismo jugador
    carta2 = Carta(id_carta=carta1.id_carta + 1, id_partida=partida.id_partida, id_jugador=jugador.id_jugador, posicion=PosicionCarta.mano)
    db.add(carta2)
    db.commit()
    db.refresh(carta2)
    # Descarta una carta
    response = client.patch(f"/partida/{partida.id_partida}/descartar", json={"jugador_id": jugador.id_jugador})
    assert response.status_code == 200
    data = response.json()
    # Verifica que solo una carta fue descartada
    carta1_actualizada = db.query(Carta).filter_by(id_carta=carta1.id_carta).first()
    carta2_actualizada = db.query(Carta).filter_by(id_carta=carta2.id_carta).first()
    assert (carta1_actualizada.id_jugador is None or carta2_actualizada.id_jugador is None)
    assert (carta1_actualizada.posicion.name == "descarte" or carta2_actualizada.posicion.name == "descarte")
    # La otra carta sigue en mano
    assert (carta1_actualizada.posicion.name == "mano" or carta2_actualizada.posicion.name == "mano")
