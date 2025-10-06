import pytest
from fastapi.testclient import TestClient
from app.capa_3_api.main import app as fastapi_app
from app.capa_0_definicion_bd.base_datos.base_datos_sincronica import SessionLocal
from app.capa_0_definicion_bd.models.cartas_models import Carta, PosicionCarta
from app.capa_0_definicion_bd.models.partidas_models import Partida as PartidaModel, EstadoPartida


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

    # Verificar que se actualizó el estado de la partida a Finalizada
    db2 = SessionLocal()
    partida_db = db2.query(PartidaModel).filter(PartidaModel.id_partida == id_partida).first()
    assert partida_db is not None
    estado = getattr(partida_db, 'estado')
    # Comparar de forma segura considerando que puede ser enum o string
    valor_estado = estado.value if hasattr(estado, 'value') else estado
    assert valor_estado in (EstadoPartida.Finalizada, EstadoPartida.Finalizada.value)
    db2.close()

    # Abrir conexión WS y luego disparar el endpoint que debe broadcastear el fin de mazo
    with client.websocket_connect(f"/ws/{id_jugador}") as ws:
        response = client.put(f"/partida/{id_partida}/reponer", json={"jugador_id": id_jugador})
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "No hay cartas disponibles en el mazo"

        # Verificar que llega el mensaje por WS en texto plano
        msg = ws.receive_text()
        assert msg == "fin_de_mazo"


def test_fin_de_mazo_al_agotar(setup_reponer):
    client, id_partida, id_jugador = setup_reponer
    db = SessionLocal()

    # Dejar exactamente N cartas en mazo para que se agoten con una sola reposición
    # Primero vaciar y luego crear 2 cartas nuevas en mazo
    db.query(Carta).filter_by(id_partida=id_partida).delete()
    from app.capa_0_definicion_bd.models.cartas_models import PosicionCarta as PC
    # 2 cartas en mazo, 3 en mano -> reponer necesitará 3, tomará 2 y dejará mazo en 0
    db.add(Carta(id_carta=1001, id_partida=id_partida, id_jugador=None, posicion=PC.mazo))
    db.add(Carta(id_carta=1002, id_partida=id_partida, id_jugador=None, posicion=PC.mazo))
    # mano actual del jugador: crear 3 cartas
    db.add(Carta(id_carta=2001, id_partida=id_partida, id_jugador=id_jugador, posicion=PC.mano))
    db.add(Carta(id_carta=2002, id_partida=id_partida, id_jugador=id_jugador, posicion=PC.mano))
    db.add(Carta(id_carta=2003, id_partida=id_partida, id_jugador=id_jugador, posicion=PC.mano))
    db.commit()
    db.close()

    with client.websocket_connect(f"/ws/{id_jugador}") as ws:
        response = client.put(f"/partida/{id_partida}/reponer", json={"jugador_id": id_jugador})
        assert response.status_code == 200
        data = response.json()
        assert "cartas" in data
        # Como el mazo quedó vacío, debe llegar notificación inmediata
        msg = ws.receive_text()
        assert msg == "fin_de_mazo"

    # Verificar que se actualizó el estado de la partida a Finalizada
    db3 = SessionLocal()
    partida_db = db3.query(PartidaModel).filter(PartidaModel.id_partida == id_partida).first()
    assert partida_db is not None
    estado = getattr(partida_db, 'estado')
    valor_estado = estado.value if hasattr(estado, 'value') else estado
    assert valor_estado in (EstadoPartida.Finalizada, EstadoPartida.Finalizada.value)
    db3.close()


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
