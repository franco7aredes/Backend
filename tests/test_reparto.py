import pytest
from unittest.mock import patch
from app.capa_0_definicion_bd.models.cartas_models import PosicionCarta, Carta
from app.capa_0_definicion_bd.models.jugadores_models import Jugador
from app.capa_0_definicion_bd.models.partidas_models import Partida, EstadoPartida
from app.capa_2_logica.fabrica import obtener_servicio_juego


@pytest.mark.asyncio
@patch('app.capa_2_logica.servicio_juego.random.shuffle')  # Evito barajar para controlar mejor
async def test_repartir_cartas_equitativamente(mock_shuffle, db_async):
    NUM_CARTAS = 6
    NUM_JUGADORES = 5
    # Preparar datos en DB async compartida
    partida = Partida(
        minimo=2,
        maximo=6,
        estado=EstadoPartida.en_espera,
        cantidad_jugadores=0,
        id_jugador_creador=0,
        turno_actual=1,
    )
    db_async.add(partida)
    await db_async.flush()
    await db_async.refresh(partida)

    # Limpiar cartas previas por si otros tests dejaron datos
    from sqlalchemy import text
    await db_async.execute(text("DELETE FROM cartas WHERE id_partida = :pid"), {"pid": partida.id_partida})
    await db_async.commit()

    # Crear jugadores
    jugadores = []
    for i in range(1, NUM_JUGADORES + 1):
        j = Jugador(
            nombre=f"J{i}",
            fecha_nacimiento=__import__('datetime').date(2000, 1, i),
            orden_turno=0,
            id_avatar=1,
            id_partida=partida.id_partida,
        )
        db_async.add(j)
        jugadores.append(j)
    await db_async.flush()
    await db_async.refresh(partida)
    partida.cantidad_jugadores = NUM_JUGADORES
    db_async.add(partida)
    await db_async.flush()

    service = obtener_servicio_juego(db_async)
    resultado = await service.repartir_cartas(partida.id_partida, NUM_CARTAS)
    repartidas = resultado["repartidas"]
    mazo = resultado["mazo"]

    assert len(repartidas) == NUM_JUGADORES
    assert (NUM_JUGADORES * NUM_CARTAS) + len(mazo) == 61

    # verificación de posesión
    primer_jugador_id = jugadores[0].id_jugador
    cartas_j1 = repartidas[primer_jugador_id]
    assert cartas_j1[0].id_jugador == primer_jugador_id
    assert cartas_j1[0].posicion == PosicionCarta.mano

    # verificación de cartas restantes en mazo
    assert mazo[0].id_jugador is None
    assert mazo[0].posicion == PosicionCarta.mazo
    # no cleanup


@pytest.mark.asyncio
async def test_repartir_cartas_sin_jugadores(db_async):
    # Preparar partida sin jugadores
    partida = Partida(
        minimo=2,
        maximo=6,
        estado=EstadoPartida.en_espera,
        cantidad_jugadores=0,
        id_jugador_creador=0,
        turno_actual=1,
    )
    db_async.add(partida)
    await db_async.flush()
    await db_async.refresh(partida)

    # Limpiar cartas
    from sqlalchemy import text
    await db_async.execute(text("DELETE FROM cartas WHERE id_partida = :pid"), {"pid": partida.id_partida})
    await db_async.commit()

    service = obtener_servicio_juego(db_async)
    resultado = await service.repartir_cartas(partida.id_partida, 6)
    assert resultado == {"repartidas": {}, "mazo": []}
