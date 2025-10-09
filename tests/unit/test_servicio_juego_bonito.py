import pytest
from unittest.mock import AsyncMock
from typing import List, Optional

from app.capa_2_logica.servicio_juego import ServicioJuego
from app.capa_2_logica.errores import PartidaNoEncontrada
from app.capa_0_definicion_bd.models.partidas_modelos import Partida as PartidaModelo, EstadoPartida
from app.capa_0_definicion_bd.models.jugadores_modelos import Jugador as JugadorModelo
from app.capa_0_definicion_bd.models.cartas_modelos import Carta as CartaModelo, PosicionCarta
from tests.mocks.repos_mocks import (
    crear_repo_partida_mock,
    crear_repo_jugador_mock,
    crear_repo_carta_mock,
    crear_partida_en_juego,
    crear_partida_en_espera,
    crear_jugador,
    crear_carta,
)


@pytest.mark.asyncio
async def test_terminar_turno_avanza_bien():
    # Repos de fábrica reutilizables
    repo_partida = crear_repo_partida_mock()
    repo_jugador = crear_repo_jugador_mock()

    repo_partida.obtener.return_value = crear_partida_en_juego(id_partida=1, turno_actual=1, cantidad_jugadores=3)
    repo_jugador.obtener.return_value = crear_jugador(id_jugador=10, orden_turno=1, id_partida=1)

    s = ServicioJuego(repo_partida, jugadores=repo_jugador)
    nuevo = await s.terminar_turno(1, 10)
    assert nuevo.turno_nuevo == 2
    repo_partida.guardar.assert_awaited()


@pytest.mark.asyncio
async def test_iniciar_y_preparar_partida_not_found():
    repo_partida = crear_repo_partida_mock()
    repo_partida.obtener.return_value = None
    s = ServicioJuego(repo_partida)

    with pytest.raises(PartidaNoEncontrada):
        await s.iniciar_y_preparar_partida(999, 3)


@pytest.mark.asyncio
async def test_iniciar_partida_errores():
    repo_p0 = crear_repo_partida_mock()
    s = ServicioJuego(repo_p0)
    # no Encontrada
    repo_p0.obtener.return_value = None
    with pytest.raises(PartidaNoEncontrada):
        await s.iniciar_partida(1)

    # ya en juego
    repo_p0.obtener.return_value = crear_partida_en_juego(cantidad_jugadores=2, minimo=2)
    from app.capa_2_logica.errores import PartidaYaEnJuego
    with pytest.raises(PartidaYaEnJuego):
        await s.iniciar_partida(1)

    # minimo no alcanzado
    repo_p0.obtener.return_value = crear_partida_en_espera(cantidad_jugadores=1, minimo=2)
    from app.capa_2_logica.errores import MinimoJugadoresNoAlcanzado
    with pytest.raises(MinimoJugadoresNoAlcanzado):
        await s.iniciar_partida(1)


@pytest.mark.asyncio
async def test_unirse_a_partida_errores():
    repo_p1 = crear_repo_partida_mock()
    repo_j1 = crear_repo_jugador_mock()
    s = ServicioJuego(repo_p1, jugadores=repo_j1)

    # no Encontrada
    repo_p1.obtener.return_value = None
    with pytest.raises(PartidaNoEncontrada):
        await s.unirse_a_partida(1, "A", __import__('datetime').datetime(2000,1,1))

    # llena
    repo_p1.obtener.return_value = type("P", (), {"id_partida": 1, "estado": EstadoPartida.en_espera, "cantidad_jugadores": 4, "maximo": 4})()
    from app.capa_2_logica.errores import MaximoJugadoresAlcanzado
    with pytest.raises(MaximoJugadoresAlcanzado):
        await s.unirse_a_partida(1, "A", __import__('datetime').datetime(2000,1,1))


@pytest.mark.asyncio
async def test_reponer_del_mazo_casos():
    repo_p2 = crear_repo_partida_mock()
    repo_j2 = crear_repo_jugador_mock()
    repo_c2 = crear_repo_carta_mock()
    s = ServicioJuego(repo_p2, jugadores=repo_j2, cartas=repo_c2)

    # jugador no encontrado
    repo_j2.obtener.return_value = None
    with pytest.raises(ValueError):
        await s.reponer_del_mazo(1, 99)

    # partida no encontrada
    repo_j2.obtener.return_value = crear_jugador(id_partida=1)
    repo_p2.obtener.return_value = None
    from app.capa_2_logica.errores import PartidaNoEncontrada as PNE
    with pytest.raises(PNE):
        await s.reponer_del_mazo(1, 1)

    # jugador no pertenece a la partida indicada (jugador.id_partida != partida_id)
    repo_p2.obtener.return_value = type("P", (), {"id_partida": 2})()
    repo_j2.obtener.return_value = crear_jugador(id_partida=2)
    with pytest.raises(ValueError):
        await s.reponer_del_mazo(1, 1)

    # max alcanzado
    repo_p2.obtener.return_value = type("P2", (), {"id_partida": 1})()
    repo_j2.obtener.return_value = crear_jugador(id_partida=1)
    repo_c2.contar_en_mano.return_value = 6
    r = await s.reponer_del_mazo(1, 1)
    assert r.cartas == []
    assert r.fin_de_mazo is False
    assert r.max_alcanzado is True
    assert r.sin_cartas is False

    # sin cartas (mazo vacío) por lo que marca Finalizada
    repo_j2.obtener.return_value = crear_jugador(id_partida=1)
    repo_c2.contar_en_mano.return_value = 3
    repo_c2.obtener_mazo_disponible.return_value = []
    partida = type("PP", (), {"id_partida": 1, "estado": EstadoPartida.en_juego})()
    repo_p2.obtener.return_value = partida
    r2 = await s.reponer_del_mazo(1, 1)
    assert r2.sin_cartas is True
    repo_p2.guardar.assert_awaited()

    # feliz con una carta
    c = crear_carta(id_carta=1, id_partida=1, id_jugador=None, posicion=PosicionCarta.mazo)
    repo_j2.obtener.return_value = crear_jugador(id_partida=1)
    repo_c2.obtener_mazo_disponible.return_value = [c]
    r3 = await s.reponer_del_mazo(1, 1)
    assert len(r3.cartas) == 1


@pytest.mark.asyncio
async def test_terminar_turno_errores():
    repo_p3 = crear_repo_partida_mock()
    repo_j3 = crear_repo_jugador_mock()
    s = ServicioJuego(repo_p3, jugadores=repo_j3)

    # partida no encontrada
    repo_p3.obtener.return_value = None
    with pytest.raises(PartidaNoEncontrada):
        await s.terminar_turno(1, 1)

    # partida no en juego
    repo_p3.obtener.return_value = crear_partida_en_espera()
    with pytest.raises(ValueError):
        await s.terminar_turno(1, 1)

    # jugador no encontrado
    repo_p3.obtener.return_value = crear_partida_en_juego(cantidad_jugadores=2, turno_actual=1)
    repo_j3.obtener.return_value = None
    with pytest.raises(ValueError):
        await s.terminar_turno(1, 2)

    # turno inválido
    repo_j3.obtener.return_value = crear_jugador(orden_turno=2)
    with pytest.raises(PermissionError):
        await s.terminar_turno(1, 2)
