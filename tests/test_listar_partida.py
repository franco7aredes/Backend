import pytest


@pytest.mark.asyncio
async def test_listar_partidas(async_client, db_async):
    from app.capa_0_definicion_bd.models.partidas_models import Partida as PartidaModel, EstadoPartida
    from app.capa_0_definicion_bd.models.jugadores_models import Jugador as JugadorModel
    import datetime

    # Limpiar
    from sqlalchemy import text
    await db_async.execute(text("DELETE FROM jugadores"))
    await db_async.execute(text("DELETE FROM partidas"))
    await db_async.commit()

    # Crear dos jugadores creadores y sus partidas
    jugador1 = JugadorModel(nombre="Jugador1", fecha_nacimiento=datetime.date(1990, 1, 1), orden_turno=1, id_avatar=1, id_partida=1)
    jugador2 = JugadorModel(nombre="Jugador2", fecha_nacimiento=datetime.date(1991, 2, 2), orden_turno=1, id_avatar=1, id_partida=2)
    db_async.add_all([jugador1, jugador2])
    await db_async.flush()
    await db_async.refresh(jugador1)
    await db_async.refresh(jugador2)
    await db_async.commit()

    partida1 = PartidaModel(
        estado=EstadoPartida.en_espera,
        id_jugador_creador=jugador1.id_jugador,
        cantidad_jugadores=1,
        turno_actual=1,
        minimo=2,
        maximo=4,
    )
    partida2 = PartidaModel(
        estado=EstadoPartida.en_espera,
        id_jugador_creador=jugador2.id_jugador,
        cantidad_jugadores=1,
        turno_actual=1,
        minimo=4,
        maximo=6,
    )
    partida3 = PartidaModel(
        estado=EstadoPartida.en_juego,
        id_jugador_creador=jugador1.id_jugador,
        cantidad_jugadores=1,
        turno_actual=1,
        minimo=3,
        maximo=5,
    )
    db_async.add_all([partida1, partida2, partida3])
    await db_async.flush()
    await db_async.refresh(partida1)
    await db_async.refresh(partida2)
    await db_async.refresh(partida3)
    await db_async.commit()

    # Actualizar id_partida de jugadores
    jugador1.id_partida = partida1.id_partida
    jugador2.id_partida = partida2.id_partida
    db_async.add_all([jugador1, jugador2])
    await db_async.flush()
    await db_async.commit()

    response = await async_client.get("/partidas")
    assert response.status_code == 200
    partidas = response.json()
    assert isinstance(partidas, list)
    assert len(partidas) == 2
    assert partidas[0]["minimo"] == 2
    assert partidas[0]["maximo"] == 4


@pytest.mark.asyncio
async def test_listar_partidas_metodo_invalido(async_client):
    response = await async_client.post("/partidas", json={})
    assert response.status_code in (405, 422)


@pytest.mark.asyncio
async def test_listar_partidas_parametros_invalidos(async_client):
    response = await async_client.get("/partidas", params={"minimo": "dos", "maximo": "cuatro"})
    assert response.status_code in (200, 422)