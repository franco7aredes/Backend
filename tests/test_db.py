import pytest
import pytest_asyncio
from sqlalchemy import select
from app.capa_0_definicion_bd.models.jugadores_modelos import Jugador
from app.capa_0_definicion_bd.models.partidas_modelos import Partida, EstadoPartida
from app.capa_0_definicion_bd.models.cartas_modelos import Carta
from datetime import date


@pytest.mark.asyncio
async def test_insertar_jugador_y_partida(db_async):
    partida = Partida(
        estado=EstadoPartida.en_espera,
        id_jugador_creador=1,
        cantidad_jugadores=4,
        turno_actual=1,
        minimo=2,
        maximo=6,
    )

    db_async.add(partida)
    await db_async.flush()
    await db_async.refresh(partida)

    jugador = Jugador(
        nombre="Leandro",
        fecha_nacimiento=date(1990, 5, 15),
        orden_turno=1,
        id_avatar=3,
        id_partida=partida.id_partida,
    )
    db_async.add(jugador)
    await db_async.flush()
    await db_async.refresh(jugador)

    partida.id_jugador_creador = jugador.id_jugador
    db_async.add(partida)
    await db_async.flush()
    await db_async.refresh(partida)

    assert jugador.id_jugador is not None
    assert partida.id_partida is not None
    assert partida.id_jugador_creador == jugador.id_jugador
    assert jugador.nombre == "Leandro"
    assert partida.estado == EstadoPartida.en_espera


@pytest.mark.asyncio
async def test_partida_sin_estado(db_async):
    partida = Partida(
        id_jugador_creador=1,
        cantidad_jugadores=4,
        turno_actual=1,
        minimo=2,
        maximo=4,
    )
    db_async.add(partida)
    with pytest.raises(Exception):
        await db_async.flush()


@pytest.mark.asyncio
async def test_estado_partida_valido(db_async):
    partida = Partida(
        estado=EstadoPartida.Finalizada,
        id_jugador_creador=1,
        cantidad_jugadores=3,
        turno_actual=1,
        minimo=2,
        maximo=4,
    )
    db_async.add(partida)
    await db_async.flush()
    assert partida.estado == EstadoPartida.Finalizada


@pytest.mark.asyncio
async def test_varios_jugadores_en_una_partida(db_async):
    partida = Partida(
        estado=EstadoPartida.en_juego,
        id_jugador_creador=1,
        cantidad_jugadores=3,
        turno_actual=1,
        minimo=2,
        maximo=4,
    )
    db_async.add(partida)
    await db_async.flush()

    jugadores = [
        Jugador(nombre="Joa", fecha_nacimiento=date(1995, 1, 1), orden_turno=1, id_avatar=1, id_partida=partida.id_partida),
        Jugador(nombre="Facu", fecha_nacimiento=date(2002, 2, 2), orden_turno=2, id_avatar=2, id_partida=partida.id_partida),
        Jugador(nombre="Gero", fecha_nacimiento=date(2004, 3, 3), orden_turno=3, id_avatar=3, id_partida=partida.id_partida),
    ]
    db_async.add_all(jugadores)
    await db_async.flush()

    res = await db_async.execute(select(Jugador).where(Jugador.id_partida == partida.id_partida))
    resultado = res.scalars().all()
    assert len(resultado) == 3


@pytest.mark.asyncio
async def test_cartas_en_jugadores(db_async):
    partida = Partida(
        estado=EstadoPartida.en_juego,
        id_jugador_creador=1,
        cantidad_jugadores=3,
        turno_actual=1,
        minimo=2,
        maximo=4,
    )
    db_async.add(partida)
    await db_async.flush()

    jugadores = [
        Jugador(nombre="Joa", fecha_nacimiento=date(1995, 1, 1), orden_turno=1, id_avatar=1, id_partida=partida.id_partida),
        Jugador(nombre="Facu", fecha_nacimiento=date(2002, 2, 2), orden_turno=2, id_avatar=2, id_partida=partida.id_partida),
        Jugador(nombre="Gero", fecha_nacimiento=date(2004, 3, 3), orden_turno=3, id_avatar=3, id_partida=partida.id_partida),
    ]
    db_async.add_all(jugadores)
    await db_async.flush()

    joa_id = jugadores[0].id_jugador
    facu_id = jugadores[1].id_jugador
    gero_id = jugadores[2].id_jugador
    cartas = [
        Carta(id_carta=1, id_partida=partida.id_partida, id_jugador=joa_id, posicion="mano"),
        Carta(id_carta=2, id_partida=partida.id_partida, id_jugador=facu_id, posicion="mano"),
        Carta(id_carta=3, id_partida=partida.id_partida, id_jugador=gero_id, posicion="mano"),
        Carta(id_carta=4, id_partida=partida.id_partida, posicion="mazo"),
        Carta(id_carta=5, id_partida=partida.id_partida, posicion="descarte"),
        Carta(id_carta=6, id_partida=partida.id_partida, posicion="mazo"),
    ]
    db_async.add_all(cartas)
    await db_async.flush()

    res = await db_async.execute(select(Carta).where(Carta.id_jugador == joa_id))
    mano_joa = res.scalars().all()
    assert len(mano_joa) == 1
    res = await db_async.execute(select(Carta).where(Carta.id_jugador == facu_id))
    mano_facu = res.scalars().all()
    assert len(mano_facu) == 1
    res = await db_async.execute(select(Carta).where(Carta.id_jugador == gero_id))
    mano_gero = res.scalars().all()
    assert len(mano_gero) == 1
    res = await db_async.execute(select(Carta).where(Carta.posicion == "mazo"))
    mazo = res.scalars().all()
    assert len(mazo) == 2
    res = await db_async.execute(select(Carta).where(Carta.posicion == "descarte"))
    descarte = res.scalars().all()
    assert len(descarte) == 1
    res = await db_async.execute(select(Carta).where(Carta.posicion == "mano"))
    mazo = res.scalars().all()
    assert len(mazo) == 3
