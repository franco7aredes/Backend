import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session
from app.capa_0_definicion_bd.models.cartas_models import PosicionCarta, Carta
from app.capa_0_definicion_bd.models.jugadores_models import Jugador
from app.capa_0_definicion_bd.models.partidas_models import Partida, EstadoPartida
import asyncio
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_0_definicion_bd.base_datos.base_datos_sincronica import SessionLocal
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


@patch('app.capa_2_logica.servicio_juego.random.shuffle')  # Evito barajar para controlar mejor
def test_repartir_cartas_equitativamente(mock_shuffle):
    NUM_CARTAS = 6
    NUM_JUGADORES = 5

    # Preparar datos reales en DB sync compartida
    db = SessionLocal()
    try:
        partida = Partida(
            minimo=2,
            maximo=6,
            estado=EstadoPartida.en_espera,
            cantidad_jugadores=0,
            id_jugador_creador=0,
            turno_actual=1,
        )
        db.add(partida)
        db.commit()
        db.refresh(partida)

        # Asegurar que no existan cartas previas para esta partida (limpieza por si otros tests las dejaron)
        db.query(Carta).filter(Carta.id_partida == partida.id_partida).delete(synchronize_session=False)
        db.commit()

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
            db.add(j)
            jugadores.append(j)
        db.commit()
        db.refresh(partida)
        partida.cantidad_jugadores = NUM_JUGADORES
        db.add(partida)
        db.commit()

        # Ejecutar servicio async
        async def _run():
            # Usar la misma BD de test (./test.db) para la sesión asíncrona
            async_engine = create_async_engine("sqlite+aiosqlite:///./test.db")
            AsyncTestingSessionLocal = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
            async with AsyncTestingSessionLocal() as db_async:
                service = obtener_servicio_juego(db_async)
                return await service.repartir_cartas(partida.id_partida, NUM_CARTAS)
        # Ejecutar corrutina de forma moderna y sin warnings
        resultado = asyncio.run(_run())

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
    finally:
        db.close()


def test_repartir_cartas_sin_jugadores():
    # Preparar partida sin jugadores
    db = SessionLocal()
    try:
        partida = Partida(
            minimo=2,
            maximo=6,
            estado=EstadoPartida.en_espera,
            cantidad_jugadores=0,
            id_jugador_creador=0,
            turno_actual=1,
        )
        db.add(partida)
        db.commit()
        db.refresh(partida)

        # Asegurar que no existan cartas previas para esta partida (limpieza)
        db.query(Carta).filter(Carta.id_partida == partida.id_partida).delete(synchronize_session=False)
        db.commit()

        async def _run():
            # Usar la misma BD de test (./test.db) para la sesión asíncrona
            async_engine = create_async_engine("sqlite+aiosqlite:///./test.db")
            AsyncTestingSessionLocal = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
            async with AsyncTestingSessionLocal() as db_async:
                service = obtener_servicio_juego(db_async)
                return await service.repartir_cartas(partida.id_partida, 6)
        resultado = asyncio.run(_run())

        assert resultado == {"repartidas": {}, "mazo": []}
    finally:
        db.close()
