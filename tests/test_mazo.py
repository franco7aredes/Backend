import pytest
from sqlalchemy import select, text
from app.capa_0_definicion_bd.models.partidas_models import Partida, EstadoPartida
from app.capa_0_definicion_bd.models.jugadores_models import Jugador
from app.capa_0_definicion_bd.models.cartas_models import Carta, PosicionCarta


@pytest.mark.asyncio
async def test_descartar_carta(async_client, db_async):
    # Crear partida vía endpoint
    payload = {"jugador_creador": "TestJugador", "fecha_nac": "2004-11-19", "minimo": 2, "maximo": 4}
    resp = await async_client.post("/partidas", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    id_partida = data["id_partida"]
    id_jugador = data["id_jugador_creador"]

    # Crear carta para el jugador
    carta = Carta(id_carta=1, id_partida=id_partida, id_jugador=id_jugador, posicion=PosicionCarta.mano)
    db_async.add(carta)
    await db_async.flush()
    await db_async.refresh(carta)
    await db_async.commit()

    # Llamar endpoint descartar
    response = await async_client.patch(f"/partida/{id_partida}/descartar", json={"jugador_id": id_jugador})
    assert response.status_code == 200
    # Verificar en DB
    carta_id = carta.id_carta
    db_async.expire_all()
    res = await db_async.execute(select(Carta).where(Carta.id_carta == carta_id))
    carta_actualizada = res.scalars().first()
    assert carta_actualizada.id_jugador is None
    assert carta_actualizada.posicion.name == "descarte"


@pytest.mark.asyncio
async def test_descartar_carta_sin_cartas(async_client, db_async):
    payload = {"jugador_creador": "TestJugador", "fecha_nac": "2004-11-19", "minimo": 2, "maximo": 4}
    resp = await async_client.post("/partidas", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    id_partida = data["id_partida"]
    id_jugador = data["id_jugador_creador"]

    response = await async_client.patch(f"/partida/{id_partida}/descartar", json={"jugador_id": id_jugador})
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "No se encontró carta para descartar en esta partida"


@pytest.mark.asyncio
async def test_descartar_carta_partida_inexistente(async_client, db_async):
    payload = {"jugador_creador": "TestJugador", "fecha_nac": "2004-11-19", "minimo": 2, "maximo": 4}
    resp = await async_client.post("/partidas", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    id_jugador = data["id_jugador_creador"]

    response = await async_client.patch(f"/partida/9999/descartar", json={"jugador_id": id_jugador})
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "No se encontró carta para descartar en esta partida"


@pytest.mark.asyncio
async def test_descartar_carta_jugador_inexistente(async_client, db_async):
    payload = {"jugador_creador": "TestJugador", "fecha_nac": "2004-11-19", "minimo": 2, "maximo": 4}
    resp = await async_client.post("/partidas", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    id_partida = data["id_partida"]

    response = await async_client.patch(f"/partida/{id_partida}/descartar", json={"jugador_id": 9999})
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "No se encontró carta para descartar en esta partida"


@pytest.mark.asyncio
async def test_descartar_carta_varias_cartas(async_client, db_async):
    payload = {"jugador_creador": "TestJugador", "fecha_nac": "2004-11-19", "minimo": 2, "maximo": 4}
    resp = await async_client.post("/partidas", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    id_partida = data["id_partida"]
    id_jugador = data["id_jugador_creador"]

    # Crear dos cartas en mano
    carta1 = Carta(id_carta=1, id_partida=id_partida, id_jugador=id_jugador, posicion=PosicionCarta.mano)
    carta2 = Carta(id_carta=2, id_partida=id_partida, id_jugador=id_jugador, posicion=PosicionCarta.mano)
    db_async.add_all([carta1, carta2])
    await db_async.flush()
    await db_async.refresh(carta1)
    await db_async.refresh(carta2)
    await db_async.commit()

    response = await async_client.patch(f"/partida/{id_partida}/descartar", json={"jugador_id": id_jugador})
    assert response.status_code == 200
    id1, id2 = carta1.id_carta, carta2.id_carta
    db_async.expire_all()
    res1 = await db_async.execute(select(Carta).where(Carta.id_carta == id1))
    carta1_actualizada = res1.scalars().first()
    res2 = await db_async.execute(select(Carta).where(Carta.id_carta == id2))
    carta2_actualizada = res2.scalars().first()
    assert (carta1_actualizada.id_jugador is None or carta2_actualizada.id_jugador is None)
    assert (carta1_actualizada.posicion.name == "descarte" or carta2_actualizada.posicion.name == "descarte")
    assert (carta1_actualizada.posicion.name == "mano" or carta2_actualizada.posicion.name == "mano")
