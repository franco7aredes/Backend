from app.capa_0_definicion_bd.models.partidas_models import Partida as PartidaModel, EstadoPartida
from app.capa_0_definicion_bd.models.jugadores_models import Jugador as JugadorModel
from datetime import date

import pytest


@pytest.mark.asyncio
async def test_obtener_partida_existente(async_client, db_async):
    partida = PartidaModel(
        estado=EstadoPartida.en_espera,
        id_jugador_creador=0,
        cantidad_jugadores=1,
        turno_actual=1,
        minimo=2,
        maximo=4,
    )
    db_async.add(partida)
    await db_async.flush()
    await db_async.refresh(partida)

    jugador_creador = JugadorModel(
        nombre="Gero",
        id_avatar=0,
        orden_turno=1,
        fecha_nacimiento=date(2000, 1, 1),
        id_partida=partida.id_partida,
    )
    db_async.add(jugador_creador)
    await db_async.flush()
    await db_async.refresh(jugador_creador)

    partida.id_jugador_creador = jugador_creador.id_jugador
    db_async.add(partida)
    await db_async.flush()
    await db_async.refresh(partida)
    # Asegurar visibilidad desde otras sesiones (commit antes de llamar al endpoint)
    await db_async.commit()

    response = await async_client.get(f"/partidas/{partida.id_partida}")
    assert response.status_code == 200
    data = response.json()

    assert data["id_partida"] == partida.id_partida
    assert data["minimo"] == 2
    assert data["maximo"] == 4
    assert data["estado"] == "En espera"
    assert data["cantidad_jugadores"] == 1
    assert data["turno_actual"] == 1
    assert data["id_jugador_creador"] == jugador_creador.id_jugador