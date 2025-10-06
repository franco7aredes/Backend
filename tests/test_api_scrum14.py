# tests/test_api_scrum14.py (async)
import pytest
from sqlalchemy import select
from app.capa_0_definicion_bd.models.partidas_models import Partida as PartidaModel, EstadoPartida


@pytest.mark.asyncio
async def test_iniciar_partida_con_exito(async_client, db_async):
    # Crear partida en espera con 2 jugadores
    partida = PartidaModel(
        id_partida=2,
        estado=EstadoPartida.en_espera,
        cantidad_jugadores=2,
        maximo=4,
        minimo=2,
        id_jugador_creador=1,
        turno_actual=1,
    )
    db_async.add(partida)
    await db_async.commit()

    resp = await async_client.patch("/partidas/2/iniciar", json={})
    assert resp.status_code == 200
    assert resp.json()["mensaje"] == "La partida comenzo"

    db_async.expire_all()
    res = await db_async.execute(select(PartidaModel).where(PartidaModel.id_partida == 2))
    partida_actualizada = res.scalars().first()
    assert partida_actualizada.estado == EstadoPartida.en_juego


@pytest.mark.asyncio
async def test_iniciar_partida_ya_iniciada_lanza_error(async_client, db_async):
    partida = PartidaModel(
        id_partida=3,
        estado=EstadoPartida.en_juego,
        cantidad_jugadores=2,
        maximo=4,
        minimo=2,
        id_jugador_creador=1,
        turno_actual=1,
    )
    db_async.add(partida)
    await db_async.commit()

    resp = await async_client.patch("/partidas/3/iniciar", json={})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "La partida ya esta en juego"


@pytest.mark.asyncio
async def test_iniciar_partida_no_encontrada_lanza_error(async_client):
    resp = await async_client.patch("/partidas/999/iniciar", json={})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Partida no encontrada"


@pytest.mark.asyncio
async def test_unirse_a_partida_con_exito(async_client, db_async):
    partida = PartidaModel(
        id_partida=4,
        estado=EstadoPartida.en_espera,
        cantidad_jugadores=0,
        maximo=4,
        minimo=2,
        id_jugador_creador=1,
        turno_actual=1,
    )
    db_async.add(partida)
    await db_async.commit()

    jugador_data = {"nombre": "TestJugador", "fecha_nacimiento": "1990-01-01T00:00:00"}
    resp = await async_client.put("/partidas/4/unirse", json=jugador_data)
    assert resp.status_code == 201
    body = resp.json()
    assert body["mensaje"] == "jugador agregado"
    assert "jugador_id" in body

    db_async.expire_all()
    res = await db_async.execute(select(PartidaModel).where(PartidaModel.id_partida == 4))
    partida_actualizada = res.scalars().first()
    assert partida_actualizada.cantidad_jugadores == 1


@pytest.mark.asyncio
async def test_unirse_a_partida_llena_lanza_error(async_client, db_async):
    partida = PartidaModel(
        id_partida=5,
        estado=EstadoPartida.en_espera,
        cantidad_jugadores=4,
        maximo=4,
        minimo=2,
        id_jugador_creador=1,
        turno_actual=1,
    )
    db_async.add(partida)
    await db_async.commit()

    jugador_data = {"nombre": "JugadorExtra", "fecha_nacimiento": "1990-01-01T00:00:00"}
    resp = await async_client.put("/partidas/5/unirse", json=jugador_data)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "La partida ya tiene el máximo de jugadores"


@pytest.mark.asyncio
async def test_unirse_a_partida_no_encontrada_lanza_error(async_client):
    jugador_data = {"nombre": "JugadorInexistente", "fecha_nacimiento": "1990-01-01T00:00:00"}
    resp = await async_client.put("/partidas/999/unirse", json=jugador_data)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Partida no encontrada"

