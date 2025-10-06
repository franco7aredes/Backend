import pytest
from sqlalchemy import delete, select
from app.capa_0_definicion_bd.models.cartas_models import Carta, PosicionCarta
from app.capa_0_definicion_bd.models.partidas_models import Partida as PartidaModel, EstadoPartida


@pytest.mark.asyncio
async def test_reponer_del_mazo(async_client, db_async):
    # Crear partida
    payload = {"jugador_creador": "pepito", "fecha_nac": "2002-09-15", "minimo": 2, "maximo": 5}
    resp = await async_client.post("/partidas", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    id_partida = data["id_partida"]
    id_jugador = data["id_jugador_creador"]

    # Limpiar cualquier carta previa
    await db_async.execute(delete(Carta).where(Carta.id_partida == id_partida))
    # Crear 10 cartas en mazo
    db_async.add_all([Carta(id_carta=i, id_partida=id_partida, id_jugador=None, posicion=PosicionCarta.mazo) for i in range(1, 11)])
    # Y 3 en mano
    db_async.add_all([Carta(id_carta=j, id_partida=id_partida, id_jugador=id_jugador, posicion=PosicionCarta.mano) for j in range(11, 14)])
    await db_async.commit()

    # Reponer
    response = await async_client.put(f"/partida/{id_partida}/reponer", json={"jugador_id": id_jugador})
    assert response.status_code == 200
    body = response.json()
    assert "mensaje" in body and "cartas" in body
    assert len(body["cartas"]) == 3
    assert all(c["posicion"] == "mano" for c in body["cartas"])


@pytest.mark.asyncio
async def test_reponer_maximo_cartas(async_client, db_async):
    resp = await async_client.post("/partidas", json={"jugador_creador": "pepito", "fecha_nac": "2002-09-15", "minimo": 2, "maximo": 5})
    assert resp.status_code == 201
    data = resp.json()
    id_partida = data["id_partida"]
    id_jugador = data["id_jugador_creador"]

    await db_async.execute(delete(Carta).where(Carta.id_partida == id_partida))
    # Poner exactamente 6 en mano (máximo)
    db_async.add_all([Carta(id_carta=i, id_partida=id_partida, id_jugador=id_jugador, posicion=PosicionCarta.mano) for i in range(1, 7)])
    await db_async.commit()

    response = await async_client.put(f"/partida/{id_partida}/reponer", json={"jugador_id": id_jugador})
    assert response.status_code == 200
    assert response.json()["mensaje"] == "El jugador ya tiene el maximo de cartas en la mano"


@pytest.mark.asyncio
async def test_reponer_mazo_vacio(async_client, db_async, client):
    resp = await async_client.post("/partidas", json={"jugador_creador": "pepito", "fecha_nac": "2002-09-15", "minimo": 2, "maximo": 5})
    assert resp.status_code == 201
    data = resp.json()
    id_partida = data["id_partida"]
    id_jugador = data["id_jugador_creador"]

    # Vaciar el mazo de esa partida (por si hay cartas)
    await db_async.execute(delete(Carta).where((Carta.id_partida == id_partida) & (Carta.id_jugador.is_(None)) & (Carta.posicion == PosicionCarta.mazo)))
    await db_async.commit()

    response = await async_client.put(f"/partida/{id_partida}/reponer", json={"jugador_id": id_jugador})
    assert response.status_code == 404
    assert response.json()["detail"] == "No hay cartas disponibles en el mazo"

    # Verificar estado Finalizada
    res = await db_async.execute(select(PartidaModel).where(PartidaModel.id_partida == id_partida))
    partida_db = res.scalars().first()
    assert partida_db is not None
    estado = getattr(partida_db, "estado")
    valor_estado = estado.value if hasattr(estado, "value") else estado
    assert valor_estado in (EstadoPartida.Finalizada, getattr(EstadoPartida.Finalizada, "value", EstadoPartida.Finalizada))

    # Abrir WS y disparar endpoint nuevamente para recibir notificación
    with client.websocket_connect(f"/ws/{id_jugador}") as ws:
        response2 = client.put(f"/partida/{id_partida}/reponer", json={"jugador_id": id_jugador})
        assert response2.status_code == 404
        assert response2.json()["detail"] == "No hay cartas disponibles en el mazo"
        msg = ws.receive_text()
        assert msg == "fin_de_mazo"


@pytest.mark.asyncio
async def test_fin_de_mazo_al_agotar(async_client, db_async, client):
    resp = await async_client.post("/partidas", json={"jugador_creador": "pepito", "fecha_nac": "2002-09-15", "minimo": 2, "maximo": 5})
    assert resp.status_code == 201
    data = resp.json()
    id_partida = data["id_partida"]
    id_jugador = data["id_jugador_creador"]

    # Dejar solo 2 en mazo y 3 en mano
    await db_async.execute(delete(Carta).where(Carta.id_partida == id_partida))
    db_async.add(Carta(id_carta=1001, id_partida=id_partida, id_jugador=None, posicion=PosicionCarta.mazo))
    db_async.add(Carta(id_carta=1002, id_partida=id_partida, id_jugador=None, posicion=PosicionCarta.mazo))
    db_async.add(Carta(id_carta=2001, id_partida=id_partida, id_jugador=id_jugador, posicion=PosicionCarta.mano))
    db_async.add(Carta(id_carta=2002, id_partida=id_partida, id_jugador=id_jugador, posicion=PosicionCarta.mano))
    db_async.add(Carta(id_carta=2003, id_partida=id_partida, id_jugador=id_jugador, posicion=PosicionCarta.mano))
    await db_async.commit()

    with client.websocket_connect(f"/ws/{id_jugador}") as ws:
        response = client.put(f"/partida/{id_partida}/reponer", json={"jugador_id": id_jugador})
        assert response.status_code == 200
        _ = response.json()
        msg = ws.receive_text()
        assert msg == "fin_de_mazo"

    # Estado Finalizada
    res = await db_async.execute(select(PartidaModel).where(PartidaModel.id_partida == id_partida))
    partida_db = res.scalars().first()
    assert partida_db is not None
    estado = getattr(partida_db, "estado")
    valor_estado = estado.value if hasattr(estado, "value") else estado
    assert valor_estado in (EstadoPartida.Finalizada, getattr(EstadoPartida.Finalizada, "value", EstadoPartida.Finalizada))


@pytest.mark.asyncio
async def test_reponer_jugador_inexistente(async_client, db_async):
    resp = await async_client.post("/partidas", json={"jugador_creador": "pepito", "fecha_nac": "2002-09-15", "minimo": 2, "maximo": 5})
    assert resp.status_code == 201
    data = resp.json()
    id_partida = data["id_partida"]

    response = await async_client.put(f"/partida/{id_partida}/reponer", json={"jugador_id": 9999})
    assert response.status_code == 404
    assert response.json()["detail"] == "Jugador no encontrado"


@pytest.mark.asyncio
async def test_reponer_partida_inexistente(async_client, db_async):
    resp = await async_client.post("/partidas", json={"jugador_creador": "pepito", "fecha_nac": "2002-09-15", "minimo": 2, "maximo": 5})
    assert resp.status_code == 201
    data = resp.json()
    id_jugador = data["id_jugador_creador"]

    response = await async_client.put(f"/partida/9999/reponer", json={"jugador_id": id_jugador})
    assert response.status_code == 404
    assert response.json()["detail"] == "Partida no encontrada"
