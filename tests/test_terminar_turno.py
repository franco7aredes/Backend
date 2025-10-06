import pytest
from sqlalchemy import select, text
from app.capa_0_definicion_bd.models.partidas_models import Partida as PartidaModel, EstadoPartida
from app.capa_0_definicion_bd.models.jugadores_models import Jugador as JugadorModel
import datetime


@pytest.mark.asyncio
async def test_terminar_turno_valido(async_client, db_async):
    # Limpiar
    await db_async.execute(text("DELETE FROM jugadores"))
    await db_async.execute(text("DELETE FROM partidas"))
    await db_async.commit()

    # Crear partida
    partida1 = PartidaModel(
        estado=EstadoPartida.en_juego,
        id_jugador_creador=0,
        cantidad_jugadores=3,
        turno_actual=1,
        minimo=2,
        maximo=4,
    )
    db_async.add(partida1)
    await db_async.flush()
    await db_async.refresh(partida1)

    # Crear 3 jugadores
    jugador1 = JugadorModel(nombre="Jugador1", fecha_nacimiento=datetime.date(1990, 1, 1), orden_turno=1, id_avatar=1, id_partida=partida1.id_partida)
    jugador2 = JugadorModel(nombre="Jugador2", fecha_nacimiento=datetime.date(1991, 2, 2), orden_turno=3, id_avatar=5, id_partida=partida1.id_partida)
    jugador3 = JugadorModel(nombre="Jugador3", fecha_nacimiento=datetime.date(1992, 2, 2), orden_turno=2, id_avatar=3, id_partida=partida1.id_partida)
    db_async.add_all([jugador1, jugador2, jugador3])
    await db_async.flush()
    await db_async.refresh(jugador1)
    await db_async.refresh(jugador2)
    await db_async.refresh(jugador3)

    # Actualizar creador con un jugador real
    partida1.id_jugador_creador = jugador1.id_jugador
    db_async.add(partida1)
    await db_async.flush()
    await db_async.commit()

    # PATCH terminar turno
    response = await async_client.patch(f"/partidas/{partida1.id_partida}/terminar_turno?id_enviada={jugador1.id_jugador}")
    assert response.status_code == 200

    # Refrescar instancia local para ver cambios de otra sesión
    await db_async.refresh(partida1)
    assert partida1.turno_actual == 2


@pytest.mark.asyncio
async def test_terminar_turno_invalido(async_client, db_async):
    # Limpiar
    await db_async.execute(text("DELETE FROM jugadores"))
    await db_async.execute(text("DELETE FROM partidas"))
    await db_async.commit()

    # Crear partida y jugadores
    partida = PartidaModel(
        estado=EstadoPartida.en_juego,
        id_jugador_creador=0,
        cantidad_jugadores=2,
        turno_actual=1,
        minimo=2,
        maximo=4,
    )
    db_async.add(partida)
    await db_async.flush()
    await db_async.refresh(partida)

    j1 = JugadorModel(nombre="J1", fecha_nacimiento=datetime.date(1990, 1, 1), orden_turno=1, id_avatar=1, id_partida=partida.id_partida)
    j2 = JugadorModel(nombre="J2", fecha_nacimiento=datetime.date(1991, 1, 1), orden_turno=2, id_avatar=2, id_partida=partida.id_partida)
    db_async.add_all([j1, j2])
    await db_async.flush()
    await db_async.refresh(j1)
    await db_async.refresh(j2)

    partida.id_jugador_creador = j1.id_jugador
    db_async.add(partida)
    await db_async.flush()
    await db_async.commit()

    # Intenta terminar turno con el jugador que NO tiene el turno actual
    resp = await async_client.patch(f"/partidas/{partida.id_partida}/terminar_turno?id_enviada={j2.id_jugador}")
    assert resp.status_code == 400
