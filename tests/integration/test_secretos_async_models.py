import pytest
from sqlalchemy import select
from datetime import date

from app.capa_0_definicion_bd.models.partidas_modelos import Partida, EstadoPartida
from app.capa_0_definicion_bd.models.jugadores_modelos import Jugador
from app.capa_0_definicion_bd.models.secretos_modelos import SecretoDB, EstadoSecreto, TipoSecreto


@pytest.mark.asyncio
async def test_secretos_basico_crud(db_async):
    # Crear partida y dos jugadores
    p = Partida(
        estado=EstadoPartida.en_juego,
        id_jugador_creador=1,
        cantidad_jugadores=2,
        turno_actual=1,
        minimo=2,
        maximo=4,
    )
    db_async.add(p)
    await db_async.flush()
    await db_async.refresh(p)

    j1 = Jugador(nombre="A", fecha_nacimiento=date(1990, 1, 1), orden_turno=1, id_avatar=1, id_partida=p.id_partida)
    j2 = Jugador(nombre="B", fecha_nacimiento=date(1991, 2, 2), orden_turno=2, id_avatar=2, id_partida=p.id_partida)
    db_async.add_all([j1, j2])
    await db_async.flush()
    await db_async.refresh(j1)
    await db_async.refresh(j2)

    # Crear secretos
    s1 = SecretoDB(id_secreto=1, id_partida=p.id_partida, id_jugador=j1.id_jugador, tipo=TipoSecreto.asesino, estado=EstadoSecreto.oculto)
    s2 = SecretoDB(id_secreto=2, id_partida=p.id_partida, id_jugador=j2.id_jugador, tipo=TipoSecreto.otro, estado=EstadoSecreto.revelado)
    db_async.add_all([s1, s2])
    await db_async.flush()

    # Consultas y asserts
    res = await db_async.execute(select(SecretoDB).where(SecretoDB.id_partida == p.id_partida))
    secretos = res.scalars().all()
    assert len(secretos) == 2

    res = await db_async.execute(select(SecretoDB).where(SecretoDB.estado == EstadoSecreto.revelado))
    revelados = res.scalars().all()
    assert len(revelados) == 1

    # Update de estado
    s1.estado = EstadoSecreto.revelado
    db_async.add(s1)
    await db_async.flush()

    res = await db_async.execute(select(SecretoDB).where(SecretoDB.estado == EstadoSecreto.revelado))
    revelados2 = res.scalars().all()
    assert len(revelados2) == 2
