import pytest
from unittest.mock import AsyncMock
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from app.capa_2_logica.servicio_juego import _regla_nsf_es_cancelable_simple
from app.capa_2_logica.resultados import *
from app.capa_2_logica.servicio_juego import ServicioJuego
from app.capa_2_logica.errores import *
from app.capa_0_definicion_bd.models.partidas_modelos import Partida as PartidaModelo, EstadoPartida
from app.capa_0_definicion_bd.models.jugadores_modelos import Jugador as JugadorModelo
from app.capa_0_definicion_bd.models.cartas_modelos import Carta as CartaModelo, PosicionCarta, TipoCarta
from app.capa_0_definicion_bd.models.secretos_modelos import SecretoDB, TipoSecreto, EstadoSecreto
from app.capa_0_definicion_bd.models.sets_modelos import Set as SetModelo
from tests.mocks.repos_mocks import (
    crear_repo_partida_mock,
    crear_repo_jugador_mock,
    crear_repo_set_mock,
    crear_repo_carta_mock,
    crear_repo_secreto_mock,
    crear_partida_en_juego,
    crear_partida_en_espera,
    crear_jugador,
    crear_carta,
    crear_secreto,
    crear_set
)


@pytest.mark.asyncio
async def test_terminar_turno_avanza_bien():
    # Repos de fÃ¡brica reutilizables
    repo_partida = crear_repo_partida_mock()
    repo_jugador = crear_repo_jugador_mock()

    repo_partida.obtener.return_value = crear_partida_en_juego(id_partida=1, turno_actual=1,estado=EstadoPartida.en_juego, cantidad_jugadores=3)
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
    repo_p0.obtener.return_value = crear_partida_en_juego(cantidad_jugadores=2, estado=EstadoPartida.en_juego, minimo=2)
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

    # sin cartas (mazo vacÃ­o) por lo que marca Finalizada
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
    repo_p3.obtener.return_value = crear_partida_en_juego(cantidad_jugadores=2, estado = EstadoPartida.en_juego, turno_actual=1)
    repo_j3.obtener.return_value = None
    with pytest.raises(ValueError):
        await s.terminar_turno(1, 2)

    # turno invÃ¡lido
    repo_j3.obtener.return_value = crear_jugador(orden_turno=2)
    with pytest.raises(PermissionError):
        await s.terminar_turno(1, 2)


@pytest.mark.asyncio
async def test_obtener_cartas_propias():
    from app.capa_0_definicion_bd.models.cartas_modelos import TipoCarta

    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock()
    # jugador y partida vÃ¡lidos
    repo_j.obtener.return_value = crear_jugador(id_jugador=10, id_partida=77)
    repo_p.obtener.return_value = crear_partida_en_juego(id_partida=77, estado=EstadoPartida.en_juego)

    # cartas en mano mock
    c1 = crear_carta(id_carta=1, id_partida=77, id_jugador=10, posicion=PosicionCarta.mano)
    c1.nombre, c1.tipo = "Not so fast", TipoCarta.instant
    c2 = crear_carta(id_carta=2, id_partida=77, id_jugador=10, posicion=PosicionCarta.mano)
    c2.nombre, c2.tipo = "Hercule Poirot", TipoCarta.detective

    repo_c = crear_repo_carta_mock(obtener_cartas_en_mano_return=[c1, c2])

    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)
    res = await s.obtener_cartas_propias(77, 10)

    assert len(res.cartas) == 2
    assert [c.id_carta for c in res.cartas] == [1, 2]
    assert all(c.posicion == PosicionCarta.mano for c in res.cartas)
    assert all((getattr(c, "nombre", None) is not None and getattr(c, "tipo", None) is not None) for c in res.cartas)

@pytest.mark.asyncio
async def test_obtener_cartas_propias_errores():
    # jugador no encontrado
    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    repo_c = crear_repo_carta_mock()
    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)
    with pytest.raises(ValueError):
        await s.obtener_cartas_propias(77, 10)


    # jugador no pertenece a la partida
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=10, id_partida=99))
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=77, estado=EstadoPartida.en_juego))
    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)
    with pytest.raises(ValueError):
        await s.obtener_cartas_propias(77, 10)

@pytest.mark.asyncio
async def test_descartar_cartas_bonito():

    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock()

    repo_j.obtener.return_value = crear_jugador(id_jugador=10, id_partida=77)
    repo_p.obtener.return_value = crear_partida_en_juego(id_partida=77, estado=EstadoPartida.en_juego)

    c1 = crear_carta(id_carta=1, id_partida=77, id_jugador=10, posicion=PosicionCarta.mano)
    c1.nombre, c1.tipo = "Not so fast", TipoCarta.instant

    repo_c = crear_repo_carta_mock(obtener_carta_return=c1,
                            obtener_cantidad_descartadas_return=35)

    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)

    res = await s.descartar_carta(77, 10, 1)

    assert hasattr(res, "carta")
    assert res.carta == c1
    assert c1.orden_en_descarte == 36

@pytest.mark.asyncio
async def test_descartar_cartas_error():
    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock()

    repo_j.obtener.return_value = crear_jugador(id_jugador=10, id_partida=77)
    repo_p.obtener.return_value = crear_partida_en_juego(id_partida=77, estado=EstadoPartida.en_juego)

    # Veo que pasa cuando la query devuelve nada
    repo_c = crear_repo_carta_mock(obtener_carta_return=None,
                            obtener_cantidad_descartadas_return=35)

    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)

    res = await s.descartar_carta(77, 10, 1)
    assert hasattr(res, "carta")
    assert res.carta == None
    # Veo cuando no hay base de datos
    
    repo_p.obtener.return_value = crear_partida_en_juego(id_partida=77, estado=EstadoPartida.en_juego)

    repo_c = crear_repo_carta_mock()
    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)

    res = await s.descartar_carta(77, 10, 1)
    assert hasattr(res, "carta")
    assert res.carta == None


@pytest.mark.asyncio    
async def test_ordenar_turnos_bonitos():
    repo_partida = crear_repo_partida_mock()
    repo_jugador = crear_repo_jugador_mock()

    repo_partida.obtener.return_value = crear_partida_en_juego(id_partida=1, turno_actual=1,estado=EstadoPartida.en_juego, cantidad_jugadores=3)
    repo_jugador.listar_por_partida.return_value = [
        crear_jugador(id_jugador=10, orden_turno=1, id_partida=1, fecha_nacimiento=date(1995, 8, 10)),
        crear_jugador(id_jugador=13, orden_turno=2, id_partida=1, fecha_nacimiento=date(1995, 10, 12)),
        crear_jugador(id_jugador=15, orden_turno=3, id_partida=1, fecha_nacimiento=date(1993, 8, 2)),
    ]

    s = ServicioJuego(repo_partida, jugadores=repo_jugador)

    res = await s.asignar_turnos(1)

    assert len(res) == 3
    assert [j.id_jugador for j in res] == [13, 10, 15]

    repo_jugador.listar_por_partida.return_value = [
        crear_jugador(id_jugador=10, orden_turno=1, id_partida=1, fecha_nacimiento=date(1995, 9, 10)),
        crear_jugador(id_jugador=13, orden_turno=2, id_partida=1, fecha_nacimiento=date(1996, 9, 21)),
        crear_jugador(id_jugador=15, orden_turno=3, id_partida=1, fecha_nacimiento=date(1993, 9, 8)),
    ]
    s = ServicioJuego(repo_partida, jugadores=repo_jugador)

    res = await s.asignar_turnos(1)

    assert len(res) == 3
    assert [j.id_jugador for j in res] == [10, 13, 15]

@pytest.mark.asyncio
async def test_obtener_cantidad_cartas_en_mazo():
    repo_p = crear_repo_partida_mock()
    repo_c = crear_repo_carta_mock(contar_en_mazo_return=7)

    s = ServicioJuego(repo_p, cartas=repo_c)
    res = await s.obtener_cantidad_cartas_en_mazo(30)

    # Validaciones 
    assert hasattr(res, "cantidad")
    assert res.cantidad == 7
    repo_c.contar_en_mazo.assert_awaited_once_with(30)

@pytest.mark.asyncio
async def test_obtener_cantidad_cartas_en_error():
    repo_p = crear_repo_partida_mock()
    s = ServicioJuego(repo_p)  # sin cartas

    res = await s.obtener_cantidad_cartas_en_mazo(77)

    assert hasattr(res, "cantidad")
    assert res.cantidad == 0

@pytest.mark.asyncio
async def test_obtener_cantidad_manos():
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=77, estado=EstadoPartida.en_juego))
    j1 = crear_jugador(id_jugador=10, id_partida=77)
    j2 = crear_jugador(id_jugador=11, id_partida=77)
    repo_jugador = crear_repo_jugador_mock(listar_por_partida_return=[j1, j2])

    repo_carta = crear_repo_carta_mock()
    # primero jugador 10 (3 cartas), luego jugador 11 (5 cartas)
    repo_carta.contar_en_mano.side_effect = [3, 5]

    s = ServicioJuego(repo_partida, jugadores=repo_jugador, cartas=repo_carta)
    res = await s.obtener_cantidad_manos(77)
    assert res.cartas_por_jugador == {10: 3, 11: 5}

@pytest.mark.asyncio
async def test_obtener_secretos_propios():
    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock()

    repo_j.obtener.return_value = crear_jugador(id_jugador=10, id_partida=77)
    repo_p.obtener.return_value = crear_partida_en_juego(id_partida=77, estado=EstadoPartida.en_juego)

    # Secretos mock
    s1 = crear_secreto(id_secreto=1, id_partida=77, id_jugador=10, tipo = TipoSecreto.otro)
    s2 = crear_secreto(id_secreto=3, id_partida=77, id_jugador=10, tipo = TipoSecreto.otro)
    s3 = crear_secreto(id_secreto=2, id_partida=77, id_jugador=10, tipo = TipoSecreto.otro)

    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[s1, s2, s3])

    s = ServicioJuego(repo_p, jugadores=repo_j, secretos=repo_s)

    res = await s.obtener_secretos_propios(77, 10)

    assert len(res.secretos) == 3
    assert [s.id_secreto for s in res.secretos] == [1, 3, 2]
    assert all(s.tipo == TipoSecreto.otro for s in res.secretos)
    assert all (s.id_jugador == 10 for s in res.secretos)

@pytest.mark.asyncio
async def test_obtener_secretos_propios_cero():

    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock()

    repo_j.obtener.return_value = crear_jugador(id_jugador=10, id_partida=77)
    repo_s = crear_repo_secreto_mock()
    s = ServicioJuego(repo_p, jugadores=repo_j, secretos=repo_s)

    res = await s.obtener_secretos_propios(77, 10)
    assert len(res.secretos) == 0

@pytest.mark.asyncio
async def test_ver_del_descarte_bonito():
    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock()

    repo_j.obtener.return_value = crear_jugador(id_jugador=10, id_partida=77)
    repo_p.obtener.return_value = crear_partida_en_juego(id_partida=77, estado=EstadoPartida.en_juego)

    c1 = crear_carta(id_carta=1, id_partida=77, id_jugador=10, posicion=PosicionCarta.descarte, orden_en_descarte=4)
    c1.nombre, c1.tipo = "Not so fast", TipoCarta.instant
    c2 = crear_carta(id_carta=5, id_partida=77, id_jugador=10, posicion=PosicionCarta.descarte, orden_en_descarte=3)
    c2.nombre, c2.tipo = "Hercule Poirot", TipoCarta.detective
    c3 = crear_carta(id_carta=2, id_partida=77, id_jugador=10, posicion=PosicionCarta.descarte, orden_en_descarte=2)
    c3.nombre, c3.tipo = "Not so fast", TipoCarta.instant
    c4 = crear_carta(id_carta=9, id_partida=77, id_jugador=10, posicion=PosicionCarta.descarte, orden_en_descarte=1)
    c4.nombre, c4.tipo = "Miss Marple", TipoCarta.detective

    repo_c = crear_repo_carta_mock(
                    obtener_primeras_de_descarte_return=[c1, c2, c3, c4]
                    )
   
    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)

    res = await s.ver_del_descarte(77, 10)

    assert hasattr(res, "descarte")
    assert res.descarte == [c1, c2, c3, c4]
    assert [c.orden_en_descarte for c in res.descarte] == [4, 3, 2, 1]

@pytest.mark.asyncio
async def test_ver_de_descarte_error():

    # Veo que pasa cuando la query devuelve nada
    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock()

    repo_j.obtener.return_value = crear_jugador(id_jugador=10, id_partida=77)
    repo_p.obtener.return_value = crear_partida_en_juego(id_partida=77, estado=EstadoPartida.en_juego)

    repo_c = crear_repo_carta_mock(
                            obtener_primeras_de_descarte_return=[],
                            )

    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)

    res = await s.ver_del_descarte(77, 10)
    assert hasattr(res, "descarte")
    assert res.descarte == []

    # Veo cuando no hay base de datos
    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock()

    repo_j.obtener.return_value = crear_jugador(id_jugador=10, id_partida=77)
    repo_p.obtener.return_value = crear_partida_en_juego(id_partida=77, estado=EstadoPartida.en_juego)

    repo_c = crear_repo_carta_mock()
    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)

    res = await s.ver_del_descarte(77, 10)
    assert hasattr(res, "descarte")
    assert res.descarte == []
    
@pytest.mark.asyncio
async def test_obtener_draft_bonito():
    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock()
    # Cartas en draft mock
    c1 = crear_carta(id_carta=1, id_partida=77, posicion=PosicionCarta.draft)
    c1.nombre, c1.tipo = "Not so fast", TipoCarta.instant
    c2 = crear_carta(id_carta=4, id_partida=77, posicion=PosicionCarta.draft)
    c2.nombre, c2.tipo = "Not so fast", TipoCarta.instant
    c3 = crear_carta(id_carta=7, id_partida=77, posicion=PosicionCarta.draft)
    c3.nombre, c3.tipo = "Not so fast", TipoCarta.instant

    repo_j.obtener.return_value = crear_jugador(id_jugador=10, id_partida=77)
    repo_p.obtener.return_value = crear_partida_en_juego(id_partida=77, estado=EstadoPartida.en_juego)

    repo_c = crear_repo_carta_mock(obtener_draft_return=[c1, c2, c3])
    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)

    res = await s.ver_draft(77, 10)

    assert len(res.draft) == 3
    assert all (c.posicion == PosicionCarta.draft for c in res.draft)
    assert [c.id_carta for c in res.draft] == [1, 4, 7]

@pytest.mark.asyncio
async def test_obtener_draft_errores():

    # jugador no encontrado
    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    repo_c = crear_repo_carta_mock()
    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)
    with pytest.raises(ValueError):
        await s.ver_draft(77, 10)

    # jugador no pertenece a la partida
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=10, id_partida=99))
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=77, estado=EstadoPartida.en_juego))
    s= ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)
    with pytest.raises(ValueError):
        await s.ver_draft(77, 10)
        

@pytest.mark.asyncio        
async def test_obtener_asesino():
    # Setup repositorios mockeados
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=3))
    repo_j = crear_repo_jugador_mock()

    # Crear secreto de tipo asesino
    secreto_asesino = crear_secreto(id_secreto=1, id_partida=3, id_jugador=5, tipo=TipoSecreto.asesino)

    # Repositorio de secretos con el mÃ©todo mockeado correctamente
    repo_s = crear_repo_secreto_mock(obtener_secreto_asesino_return=secreto_asesino)

    servicio = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s)

    resultado = await servicio.obtener_asesino(partida_id=3)
    assert hasattr(resultado, "asesino")
    assert resultado.asesino == 5

@pytest.mark.asyncio
async def test_obtener_asesino_sin_partida():
    repo_p = crear_repo_partida_mock()
    repo_p.obtener.return_value = None 

    repo_j = crear_repo_jugador_mock()
    repo_s = crear_repo_secreto_mock()

    servicio = ServicioJuego(partidas=repo_p,jugadores=repo_j, secretos=repo_s)

    with pytest.raises(PartidaNoEncontrada):
        await servicio.obtener_asesino(partida_id=5)

@pytest.mark.asyncio
async def test_obtener_cantidad_secretos():
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=99, estado=EstadoPartida.en_juego))
    j1 = crear_jugador(id_jugador=3, id_partida=99)
    j2 = crear_jugador(id_jugador=7, id_partida=99)
    repo_jugador = crear_repo_jugador_mock(listar_por_partida_return=[j1, j2])

    repo_secreto = crear_repo_secreto_mock()
    # primero jugador 3 (2 secretos), luego jugador 7 (4 secretos)
    repo_secreto.contar_secretos_jugador.side_effect = [2, 4]

    s = ServicioJuego(repo_partida, jugadores=repo_jugador, secretos=repo_secreto)
    res = await s.obtener_cantidad_secretos(99)
    assert res.secretos_por_jugador == {3: 2, 7: 4}

@pytest.mark.asyncio
async def test_obtener_cantidad_secretos_partida_no_encontrada():
    repo_partida = crear_repo_partida_mock(obtener_return=None)
    repo_jugador = crear_repo_jugador_mock()
    repo_secreto = crear_repo_secreto_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, secretos=repo_secreto)
    with pytest.raises(PartidaNoEncontrada):
        await s.obtener_cantidad_secretos(99)

@pytest.mark.asyncio
async def test_obtener_cantidad_secretos_sin_jugadores():
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=99, estado=EstadoPartida.en_juego))
    repo_jugador = crear_repo_jugador_mock(listar_por_partida_return=[])
    repo_secreto = crear_repo_secreto_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, secretos=repo_secreto)
    res = await s.obtener_cantidad_secretos(99)
    assert res.secretos_por_jugador == {}

@pytest.mark.asyncio
async def test_preparar_set_valido_dos_cartas():
    repo_jugador = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=4, id_partida=2))
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=2))
    
    # Cartas: mismo detective, requiere 2
    c1 = crear_carta(id_carta=1, id_partida=2, id_jugador=4)
    c1.nombre = "Parker Pyne"
    c1.tipo = TipoCarta.detective

    c2 = crear_carta(id_carta=2, id_partida=2, id_jugador=4)
    c2.nombre = "Parker Pyne"
    c2.tipo = TipoCarta.detective
    repo_cartas = crear_repo_carta_mock(obtener_cartas_en_mano_return=[c1, c2])

    set_modelo = crear_set(id_set=1, id_partida=2, id_jugador=4, nombre="Parker Pyne")
    repo_sets = crear_repo_set_mock(crear_set_return=set_modelo)

    servicio = ServicioJuego(
        partidas=repo_partida,
        jugadores=repo_jugador,
        cartas=repo_cartas,
        sets=repo_sets
    )

    resultado = await servicio.preparar_set(partida_id=2, jugador_id=4, cartas_id=[1, 2])

    assert resultado.set.id_set == 1
    assert resultado.set.nombre == "Parker Pyne"
    assert resultado.set.id_partida == 2
    assert resultado.set.id_jugador == 4

@pytest.mark.asyncio
async def test_preparar_set_valido_tres_cartas_con_comodin():
    repo_jugador = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=5, id_partida=3))
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=3))

    # Cartas: 2 normales + 1 comodÃ­n
    c1 = crear_carta(id_carta=10, id_partida=3, id_jugador=5)
    c1.nombre = "Miss Marple"
    c1.tipo = TipoCarta.detective

    c2 = crear_carta(id_carta=11, id_partida=3, id_jugador=5)
    c2.nombre = "Miss Marple"
    c2.tipo = TipoCarta.detective

    c3 = crear_carta(id_carta=12, id_partida=3, id_jugador=5)
    c3.nombre = "Harley Quin Wildcard"
    c3.tipo = TipoCarta.detective

    repo_cartas = crear_repo_carta_mock(obtener_cartas_en_mano_return=[c1, c2, c3])

    set_modelo = crear_set(id_set=2, id_partida=3, id_jugador=5, nombre="Miss Marple")
    repo_sets = crear_repo_set_mock(crear_set_return=set_modelo)

    servicio = ServicioJuego(
        partidas=repo_partida,
        jugadores=repo_jugador,
        cartas=repo_cartas,
        sets=repo_sets
    )

    resultado = await servicio.preparar_set(partida_id=3, jugador_id=5, cartas_id=[10, 11, 12])

    assert resultado.set.id_set == 2
    assert resultado.set.nombre == "Miss Marple"
    assert resultado.set.id_partida == 3
    assert resultado.set.id_jugador == 5

@pytest.mark.asyncio
async def test_preparar_set_valido_beresford():
    repo_jugador = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=7, id_partida=4))
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=4))

    # Cartas de Beresford
    c1 = crear_carta(id_carta=20, id_partida=4, id_jugador=7)
    c1.nombre = "Tommy Beresford"
    c1.tipo = TipoCarta.detective

    c2 = crear_carta(id_carta=21, id_partida=4, id_jugador=7)
    c2.nombre = "Tuppence Beresford"
    c2.tipo = TipoCarta.detective

    repo_cartas = crear_repo_carta_mock(obtener_cartas_en_mano_return=[c1, c2])

    set_modelo = crear_set(id_set=4, id_partida=4, id_jugador=7, nombre="Beresford")
    repo_sets = crear_repo_set_mock(crear_set_return=set_modelo)

    servicio = ServicioJuego(
        partidas=repo_partida,
        jugadores=repo_jugador,
        cartas=repo_cartas,
        sets=repo_sets
    )

    resultado = await servicio.preparar_set(partida_id=4, jugador_id=7, cartas_id=[20, 21])

    assert resultado.set.id_set == 4
    assert resultado.set.nombre == "Beresford"
    assert resultado.set.id_partida == 4
    assert resultado.set.id_jugador == 7

@pytest.mark.asyncio
async def test_preparar_set_invalido_beresford_tres_cartas():
    repo_jugador = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=2, id_partida=1))
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))

    c1 = crear_carta(id_carta=1, id_partida=1, id_jugador=2)
    c1.nombre = "Tommy Beresford"
    c1.tipo = TipoCarta.detective

    c2 = crear_carta(id_carta=2, id_partida=1, id_jugador=2)
    c2.nombre = "Tuppence Beresford"
    c2.tipo = TipoCarta.detective

    c3 = crear_carta(id_carta=3, id_partida=1, id_jugador=2)
    c3.nombre = "Tommy Beresford"
    c3.tipo = TipoCarta.detective

    repo_cartas = crear_repo_carta_mock(obtener_cartas_en_mano_return=[c1, c2, c3])
    repo_sets = crear_repo_set_mock()

    servicio = ServicioJuego(
        partidas=repo_partida,
        jugadores=repo_jugador,
        cartas=repo_cartas,
        sets=repo_sets
    )

    with pytest.raises(ValueError):
        await servicio.preparar_set(partida_id=1, jugador_id=2, cartas_id=[1, 2, 3])

@pytest.mark.asyncio
async def test_preparar_set_invalido_con_adriane_oliver():
    repo_jugador = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=1, id_partida=1))
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))

    c1 = crear_carta(id_carta=1, id_partida=1, id_jugador=1)
    c1.nombre = "Miss Marple"
    c1.tipo = TipoCarta.detective

    c2 = crear_carta(id_carta=2, id_partida=1, id_jugador=1)
    c2.nombre = "Adriane Oliver"
    c2.tipo = TipoCarta.detective 

    repo_cartas = crear_repo_carta_mock(obtener_cartas_en_mano_return=[c1, c2])
    repo_sets = crear_repo_set_mock()

    servicio = ServicioJuego(
        partidas=repo_partida,
        jugadores=repo_jugador,
        cartas=repo_cartas,
        sets=repo_sets
    )

    with pytest.raises(ValueError):
        await servicio.preparar_set(partida_id=1, jugador_id=1, cartas_id=[1, 2])

@pytest.mark.asyncio
async def test_preparar_set_mas_de_tres_cartas():
    repo_jugador = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=2, id_partida=1))
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))

    cartas = []
    for i in range(1, 5):
        carta = crear_carta(id_carta=i, id_partida=1, id_jugador=2)
        carta.nombre = "Miss Marple"
        carta.tipo = TipoCarta.detective
        cartas.append(carta)

    repo_cartas = crear_repo_carta_mock(obtener_cartas_en_mano_return=cartas)
    repo_sets = crear_repo_set_mock()

    servicio = ServicioJuego(
        partidas=repo_partida,
        jugadores=repo_jugador,
        cartas=repo_cartas,
        sets=repo_sets
    )

    with pytest.raises(ValueError):
        await servicio.preparar_set(partida_id=1, jugador_id=2, cartas_id=[1, 2, 3, 4])

@pytest.mark.asyncio
async def test_preparar_set_solo_con_comodines():
    repo_jugador = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=1, id_partida=1))
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))

    c1 = crear_carta(id_carta=1, id_partida=1, id_jugador=1)
    c1.nombre = "Harley Quin Wildcard"
    c1.tipo = TipoCarta.detective

    c2 = crear_carta(id_carta=2, id_partida=1, id_jugador=1)
    c2.nombre = "Harley Quin Wildcard"
    c2.tipo = TipoCarta.detective

    repo_cartas = crear_repo_carta_mock(obtener_cartas_en_mano_return=[c1, c2])
    repo_sets = crear_repo_set_mock()

    servicio = ServicioJuego(
        partidas=repo_partida,
        jugadores=repo_jugador,
        cartas=repo_cartas,
        sets=repo_sets
    )

    with pytest.raises(ValueError):
        await servicio.preparar_set(partida_id=1, jugador_id=1, cartas_id=[1, 2])
    
@pytest.mark.asyncio
async def test_reponer_del_draft_errores():
    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock()
    repo_c = crear_repo_carta_mock()
    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)

    # jugador no encontrado
    repo_j.obtener.return_value = None
    with pytest.raises(ValueError):
        await s.reponer_del_draft(1, 99, carta_id=5)

    # partida no encontrada
    repo_j.obtener.return_value = crear_jugador(id_partida=1)
    repo_p.obtener.return_value = None
    with pytest.raises(PartidaNoEncontrada):
        await s.reponer_del_draft(1, 1, carta_id=5)

    # jugador no pertenece a la partida
    repo_p.obtener.return_value = type("P", (), {"id_partida": 2})()
    repo_j.obtener.return_value = crear_jugador(id_partida=2)
    with pytest.raises(ValueError):
        await s.reponer_del_draft(1, 1, carta_id=5)


@pytest.mark.asyncio
async def test_reponer_del_draft_max_alcanzado():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1, estado=EstadoPartida.en_juego))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_partida=1))
    repo_c = crear_repo_carta_mock(contar_en_mano_return=6)
    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)

    res = await s.reponer_del_draft(1, 1, carta_id=10)
    assert res.cartas == []
    assert res.max_alcanzado is True
    assert res.fin_de_mazo is False
    assert res.sin_cartas is False
    repo_c.obtener_draft_disponible.assert_not_awaited()


@pytest.mark.asyncio
async def test_reponer_del_draft_repone_y_rellena():
    # Setup partida/jugador vÃ¡lidos
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=77, estado=EstadoPartida.en_juego))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=10, id_partida=77))
    # Draft tiene la carta pedida, mazo no queda vacÃ­o (contar_en_mazo > 0)
    c_draft = crear_carta(id_carta=5, id_partida=77, id_jugador=None, posicion=PosicionCarta.draft)
    repo_c = crear_repo_carta_mock(
        contar_en_mano_return=2,
        obtener_draft_disponible_return=[c_draft],
        contar_en_mazo_return=3,
        mover_primera_carta_mazo_a_draft_return=crear_carta(id_carta=100, id_partida=77, posicion=PosicionCarta.draft),
    )
    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)

    res = await s.reponer_del_draft(77, 10, carta_id=5)

    # Se moviÃ³ a la mano
    assert len(res.cartas) == 1
    assert res.cartas[0].id_carta == 5
    assert res.cartas[0].posicion == PosicionCarta.mano
    assert res.cartas[0].id_jugador == 10
    # Se repuso el draft desde el mazo
    repo_c.guardar_muchas.assert_awaited_once()
    repo_c.mover_primera_carta_mazo_a_draft.assert_awaited_once_with(77)
    # No finaliza la partida
    assert res.fin_de_mazo is False
    assert res.max_alcanzado is False
    assert res.sin_cartas is False
    repo_p.guardar.assert_not_awaited()


@pytest.mark.asyncio
async def test_reponer_del_draft_sin_disponible_finaliza():
    # Si no hay carta en draft, finaliza
    partida = crear_partida_en_juego(id_partida=50, estado=EstadoPartida.en_juego)
    repo_p = crear_repo_partida_mock(obtener_return=partida)
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_partida=50))
    repo_c = crear_repo_carta_mock(contar_en_mano_return=0, obtener_draft_disponible_return=[])
    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)

    res = await s.reponer_del_draft(50, 1, carta_id=999)

    assert res.cartas == []
    assert res.fin_de_mazo is True
    assert res.sin_cartas is True
    repo_p.guardar.assert_awaited()
    repo_p.confirmar.assert_awaited()


@pytest.mark.asyncio
async def test_reponer_del_draft_fin_de_mazo():
    # Hay carta en draft, pero el mazo queda en cero -> finaliza partida
    partida = crear_partida_en_juego(id_partida=60, estado=EstadoPartida.en_juego)
    repo_p = crear_repo_partida_mock(obtener_return=partida)
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_partida=60, id_jugador=7))
    c_draft = crear_carta(id_carta=3, id_partida=60, id_jugador=None, posicion=PosicionCarta.draft)
    repo_c = crear_repo_carta_mock(
        contar_en_mano_return=1,
        obtener_draft_disponible_return=[c_draft],
        contar_en_mazo_return=0,  # gatilla finalizaciÃ³n
        mover_primera_carta_mazo_a_draft_return=None,
    )
    s = ServicioJuego(repo_p, jugadores=repo_j, cartas=repo_c)

    res = await s.reponer_del_draft(60, 7, carta_id=3)

    assert len(res.cartas) == 1
    assert res.fin_de_mazo is True
    repo_p.guardar.assert_awaited()
    repo_p.confirmar.assert_awaited()


@pytest.mark.asyncio
async def test_robar_set():
    # partida y jugador vÃ¡lidos
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=10, estado=EstadoPartida.en_juego))
    rj = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=99, id_partida=10))
    
    # set pertenece a otro jugador
    set_obj = crear_set(id_set=7, id_partida=10, id_jugador=33, nombre="Parker Pyne")

    # cartas del set
    c1 = crear_carta(id_carta=1, id_partida=10, id_jugador=33, posicion=PosicionCarta.set)
    c2 = crear_carta(id_carta=2, id_partida=10, id_jugador=33, posicion=PosicionCarta.set)
    rc = crear_repo_carta_mock()

    # Creamos el repo de sets mockeado acÃ¡, porque usamos las cartas de arriba.
    rs = crear_repo_set_mock(
    obtener_set_por_id_return=set_obj,
    obtener_cartas_del_set_return=[c1, c2],
    )

    s = ServicioJuego(repo_p, jugadores=rj, cartas=rc, sets=rs)
    res = await s.robar_set(partida_id=10, jugador_id=99, set_id=7)

    assert hasattr(res, "set")
    assert res.set is set_obj
    assert set_obj.id_jugador == 99
    rs.obtener_cartas_del_set.assert_awaited_once_with(7)
    # cartas transferidas
    assert all(c.id_jugador == 99 for c in [c1, c2])
    rc.guardar_muchas.assert_awaited_once()


@pytest.mark.asyncio
async def test_robar_set_errores():
    # repos obligatorios faltan
    repo_p = crear_repo_partida_mock()
    rj = crear_repo_jugador_mock()
    s = ServicioJuego(repo_p, jugadores=rj, cartas=None, sets=None)
    with pytest.raises(ValueError):
        await s.robar_set(1, 1, 1)

    # jugador no encontrado
    rs = crear_repo_set_mock()
    rc = crear_repo_carta_mock()
    rj = crear_repo_jugador_mock(obtener_return=None)
    s = ServicioJuego(repo_p, jugadores=rj, cartas=rc, sets=rs)
    with pytest.raises(JugadorNoEncontrado):
        await s.robar_set(1, 1, 1)

    # partida no encontrada
    rj = crear_repo_jugador_mock(obtener_return=crear_jugador(id_partida=1))
    repo_p = crear_repo_partida_mock(obtener_return=None)
    s = ServicioJuego(repo_p, jugadores=rj, cartas=rc, sets=rs)
    with pytest.raises(PartidaNoEncontrada):
        await s.robar_set(1, 1, 1)

    # jugador no pertenece a la partida
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=2, estado=EstadoPartida.en_juego))
    rj = crear_repo_jugador_mock(obtener_return=crear_jugador(id_partida=3))
    s = ServicioJuego(repo_p, jugadores=rj, cartas=rc, sets=rs)
    with pytest.raises(JugadorNoEnPartida):
        await s.robar_set(2, 1, 1)

    # set no encontrado
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=5, estado=EstadoPartida.en_juego))
    rj = crear_repo_jugador_mock(obtener_return=crear_jugador(id_partida=5))
    rs = crear_repo_set_mock(obtener_set_por_id_return=None)
    s = ServicioJuego(repo_p, jugadores=rj, cartas=rc, sets=rs)
    with pytest.raises(SetNoEncontrado):
        await s.robar_set(5, 1, 7)

    # set no pertenece a la partida
    set_otro = crear_set(id_set=9, id_partida=99, id_jugador=3, nombre="X")
    rs = crear_repo_set_mock(obtener_set_por_id_return=set_otro)
    s = ServicioJuego(repo_p, jugadores=rj, cartas=rc, sets=rs)
    with pytest.raises(SetNoEnPartida):
        await s.robar_set(5, 1, 9)

    # no puede robar su propio set
    set_propio = crear_set(id_set=11, id_partida=5, id_jugador=1, nombre="Y")
    rs = crear_repo_set_mock(obtener_set_por_id_return=set_propio)
    s = ServicioJuego(repo_p, jugadores=rj, cartas=rc, sets=rs)
    with pytest.raises(NoPuedeRobarSuPropioSet):
        await s.robar_set(5, 1, 11)


@pytest.mark.asyncio
async def test_listar_en_espera_sin_partidas():
    s = ServicioJuego(partidas=None)
    res = await s.listar_en_espera()
    assert res == []

@pytest.mark.asyncio
async def test_obtener_por_id_sin_partidas():
    s = ServicioJuego(partidas=None)
    res = await s.obtener_por_id(1)
    assert res is None

@pytest.mark.asyncio
async def test_listar_jugadores_sin_repo():
    s = ServicioJuego(partidas=None)
    res = await s.listar_jugadores(1)
    assert res == []

@pytest.mark.asyncio
async def test_obtener_cantidad_mano_sin_cartas():
    s = ServicioJuego(partidas=None)
    res = await s.obtener_cantidad_mano(1, 1)
    assert res.cantidad == 0

@pytest.mark.asyncio
async def test_obtener_cantidad_cartas_en_mazo_sin_cartas():
    s = ServicioJuego(partidas=None)
    res = await s.obtener_cantidad_cartas_en_mazo(1)
    assert res.cantidad == 0

@pytest.mark.asyncio
async def test_obtener_cantidad_manos_sin_cartas():
    s = ServicioJuego(partidas=None)
    res = await s.obtener_cantidad_manos(1)
    assert res.cartas_por_jugador == {}

@pytest.mark.asyncio
async def test_obtener_cantidad_secretos_sin_secretos():
    s = ServicioJuego(partidas=None)
    res = await s.obtener_cantidad_secretos(1)
    assert res.secretos_por_jugador == {}

@pytest.mark.asyncio
async def test_obtener_secretos_propios_sin_repo():
    s = ServicioJuego(partidas=None)
    res = await s.obtener_secretos_propios(1, 1)
    assert res.secretos == []

@pytest.mark.asyncio
async def test_crear_partida_sin_repo_jugadores():
    from app.capa_2_logica.servicio_juego import ServicioJuego
    from datetime import datetime
    from tests.mocks.repos_mocks import crear_repo_partida_mock, crear_partida_en_espera
    repo_partida = crear_repo_partida_mock(crear_return=crear_partida_en_espera())
    s = ServicioJuego(partidas=repo_partida, jugadores=None)
    with pytest.raises(RuntimeError):
        await s.crear_partida("Ana", datetime(2000,1,1), 2, 4, 1)

@pytest.mark.asyncio
async def test_iniciar_partida_cambia_estado_y_guarda():
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_espera(cantidad_jugadores=3, minimo=2))
    s = ServicioJuego(partidas=repo_partida)
    res = await s.iniciar_partida(1)
    assert res.partida.estado.name == "en_juego"

@pytest.mark.asyncio
async def test_iniciar_y_preparar_partida_flujo_completo():
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_espera(cantidad_jugadores=2, minimo=2, maximo=4))
    repo_jugador = crear_repo_jugador_mock(
        listar_por_partida_return=[
            crear_jugador(id_jugador=1, fecha_nacimiento=date(1990, 1, 1)),
            crear_jugador(id_jugador=2, fecha_nacimiento=date(1991, 2, 2))
        ]
    )
    repo_carta = crear_repo_carta_mock()
    repo_secreto = crear_repo_secreto_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, cartas=repo_carta, secretos=repo_secreto)
    res = await s.iniciar_y_preparar_partida(1, 2)
    assert hasattr(res, "partida")
    assert hasattr(res, "cartas") or hasattr(res, "repartidas")

@pytest.mark.asyncio
async def test_repartir_cartas_sin_repo():
    s = ServicioJuego(partidas=None, cartas=None)
    res = await s.repartir_cartas(1, 3)
    assert res == RepartirCartasResultado(repartidas={}, mazo=[])


@pytest.mark.asyncio
async def test_repartir_cartas_sin_jugadores():
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_espera(cantidad_jugadores=0, maximo=4))
    s = ServicioJuego(repo_partida, jugadores=None, cartas=None)
    res = await s.repartir_cartas(1, 3)
    assert res == RepartirCartasResultado(repartidas={}, mazo=[])

@pytest.mark.asyncio
async def test_obtener_por_id_partida_no_existe():
    repo_partida = crear_repo_partida_mock(obtener_return=None)
    s = ServicioJuego(partidas=repo_partida)
    res = await s.obtener_por_id(999)
    assert res is None

@pytest.mark.asyncio
async def test_listar_en_espera_devuelve_dicts():
    partida = crear_partida_en_espera(id_partida=1)
    repo_partida = crear_repo_partida_mock(listar_en_espera_return=[partida])
    s = ServicioJuego(partidas=repo_partida)
    res = await s.listar_en_espera()
    assert isinstance(res, list)
    assert res[0]["id_partida"] == 1

@pytest.mark.asyncio
async def test_obtener_cantidad_manos_sin_jugadores():
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_espera())
    repo_carta = crear_repo_carta_mock()
    s = ServicioJuego(partidas=repo_partida, jugadores=None, cartas=repo_carta)
    res = await s.obtener_cantidad_manos(1)
    assert isinstance(res, CantidadManosResultado)
    assert res.cartas_por_jugador == {}

@pytest.mark.asyncio
async def test_obtener_cantidad_secretos_sin_jugadores():
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_espera())
    repo_secreto = crear_repo_secreto_mock()
    s = ServicioJuego(partidas=repo_partida, jugadores=None, secretos=repo_secreto)
    res = await s.obtener_cantidad_secretos(1)
    assert isinstance(res, CantidadSecretosResultado)
    assert res.secretos_por_jugador == {}

@pytest.mark.asyncio
async def test_iniciar_partida_no_encontrada():
    repo_partida = crear_repo_partida_mock(obtener_return=None)
    s = ServicioJuego(partidas=repo_partida)
    with pytest.raises(PartidaNoEncontrada):
        await s.iniciar_partida(999)

@pytest.mark.asyncio
async def test_iniciar_partida_ya_en_juego():
    partida = crear_partida_en_juego(estado=EstadoPartida.en_juego)
    repo_partida = crear_repo_partida_mock(obtener_return=partida)
    s = ServicioJuego(partidas=repo_partida)
    with pytest.raises(PartidaYaEnJuego):
        await s.iniciar_partida(1)

@pytest.mark.asyncio
async def test_iniciar_partida_minimo_no_alcanzado():
    partida = crear_partida_en_espera(cantidad_jugadores=1, minimo=2)
    repo_partida = crear_repo_partida_mock(obtener_return=partida)
    s = ServicioJuego(partidas=repo_partida)
    with pytest.raises(MinimoJugadoresNoAlcanzado):
        await s.iniciar_partida(1)

@pytest.mark.asyncio
async def test_unirse_a_partida_maximo_alcanzado():
    partida = crear_partida_en_espera(cantidad_jugadores=4, maximo=4)
    repo_partida = crear_repo_partida_mock(obtener_return=partida)
    repo_jugador = crear_repo_jugador_mock()
    s = ServicioJuego(partidas=repo_partida, jugadores=repo_jugador)
    with pytest.raises(MaximoJugadoresAlcanzado):
        await s.unirse_a_partida(1, "Ana", datetime(2000,1,1))

@pytest.mark.asyncio
async def test_descartar_carta_sin_repo_cartas():
    # Si no hay repo de cartas, retorna DescartarResultado con carta=None
    repo_partida = crear_repo_partida_mock()
    repo_jugador = crear_repo_jugador_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, cartas=None)
    res = await s.descartar_carta(1, 1, 1)
    assert res.carta is None

@pytest.mark.asyncio
async def test_asignar_turnos_sin_repo_jugadores():
    # Si no hay repo de jugadores, retorna lista vacÃ­a
    repo_partida = crear_repo_partida_mock()
    s = ServicioJuego(repo_partida, jugadores=None)
    res = await s.asignar_turnos(1)
    assert res == []

@pytest.mark.asyncio
async def test_repartir_secretos_sin_repo_secretos():
    # Si no hay repo de secretos, retorna secretos_repartidos vacÃ­o
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_espera(cantidad_jugadores=2))
    repo_jugador = crear_repo_jugador_mock(listar_por_partida_return=[crear_jugador(id_jugador=1), crear_jugador(id_jugador=2)])
    repo_carta = crear_repo_carta_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, cartas=repo_carta, secretos=None)
    res = await s.repartir_secretos(1)
    assert res.secretos_repartidos == {}

@pytest.mark.asyncio
async def test_listar_jugadores_repo_vacio():
    # Si el repo de jugadores estÃ¡ vacÃ­o, retorna lista vacÃ­a
    repo_partida = crear_repo_partida_mock()
    s = ServicioJuego(repo_partida, jugadores=None)
    res = await s.listar_jugadores(1)
    assert res == []

@pytest.mark.asyncio
async def test_ver_del_descarte_sin_cartas():
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_espera())
    repo_jugador = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=1, id_partida=1))
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, cartas=None)
    res = await s.ver_del_descarte(1, 1)
    assert res.descarte == []

@pytest.mark.asyncio
async def test_ver_draft_jugador_no_en_partida():
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_espera())
    repo_jugador = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=1, id_partida=2))  # id_partida distinto
    repo_carta = crear_repo_carta_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, cartas=repo_carta)
    with pytest.raises(ValueError):
        await s.ver_draft(1, 1)

@pytest.mark.asyncio
async def test_robar_set_no_encontrado():
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_espera())
    repo_jugador = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=1, id_partida=1))
    repo_set = crear_repo_set_mock(obtener_set_por_id_return=None)
    repo_carta = crear_repo_carta_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, sets=repo_set, cartas=repo_carta)
    with pytest.raises(SetNoEncontrado):
        await s.robar_set(1, 1, 999)

@pytest.mark.asyncio
async def test_robar_set_no_puede_robar_su_propio_set():
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_espera())
    repo_jugador = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=1, id_partida=1))
    set_obj = crear_set(id_set=10, id_partida=1, id_jugador=1)
    repo_set = crear_repo_set_mock(obtener_set_por_id_return=set_obj)
    repo_carta = crear_repo_carta_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, sets=repo_set, cartas=repo_carta)
    with pytest.raises(NoPuedeRobarSuPropioSet):
        await s.robar_set(1, 1, 10)

@pytest.mark.asyncio
async def test_unirse_a_partida_sin_repo_jugadores():
    # Si el repo de jugadores es None, debe lanzar RuntimeError
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_espera(id_partida=1, cantidad_jugadores=1, maximo=4))
    s = ServicioJuego(partidas=repo_partida, jugadores=None)
    with pytest.raises(RuntimeError):
        await s.unirse_a_partida(1, "Ana", datetime(2000, 1, 1))

@pytest.mark.asyncio
async def test_unirse_a_partida_partida_no_encontrada():
    # Si la partida no existe, debe lanzar PartidaNoEncontrada
    repo_partida = crear_repo_partida_mock(obtener_return=None)
    repo_jugador = crear_repo_jugador_mock()
    s = ServicioJuego(partidas=repo_partida, jugadores=repo_jugador)
    with pytest.raises(PartidaNoEncontrada):
        await s.unirse_a_partida(99, "Ana", datetime(2000, 1, 1))

@pytest.mark.asyncio
async def test_descartar_carta_sin_metodo_obtener_carta():
    # Si el repo de cartas no tiene 'obtener_carta', retorna carta=None
    repo_partida = crear_repo_partida_mock()
    repo_jugador = crear_repo_jugador_mock()
    class CartasSinObtener:
        async def obtener_cantidad_descartadas(self, partida_id): return 0
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, cartas=CartasSinObtener())
    res = await s.descartar_carta(1, 1, 1)
    assert res.carta is None

@pytest.mark.asyncio
async def test_descartar_carta_no_encontrada():
    # Si la carta no existe, retorna carta=None
    repo_partida = crear_repo_partida_mock()
    repo_jugador = crear_repo_jugador_mock()
    repo_carta = crear_repo_carta_mock(obtener_carta_return=None)
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, cartas=repo_carta)
    res = await s.descartar_carta(1, 1, 1)
    assert res.carta is None

@pytest.mark.asyncio
async def test_obtener_cartas_propias_sin_repo_cartas():
    # Si el repo de cartas es None, retorna ObtenerCartasResultado vacÃ­o
    repo_partida = crear_repo_partida_mock()
    repo_jugador = crear_repo_jugador_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, cartas=None)
    res = await s.obtener_cartas_propias(1, 1)
    assert res.cartas == []

@pytest.mark.asyncio
async def test_obtener_cartas_propias_sin_repo_jugadores():
    # Si el repo de jugadores es None, retorna ObtenerCartasResultado vacÃ­o
    repo_partida = crear_repo_partida_mock()
    repo_carta = crear_repo_carta_mock()
    s = ServicioJuego(repo_partida, jugadores=None, cartas=repo_carta)
    res = await s.obtener_cartas_propias(1, 1)
    assert res.cartas == []

@pytest.mark.asyncio
async def test_obtener_cartas_propias_partida_no_encontrada():
    # Si la partida no existe, lanza PartidaNoEncontrada
    repo_partida = crear_repo_partida_mock(obtener_return=None)
    repo_jugador = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=1, id_partida=1))
    repo_carta = crear_repo_carta_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, cartas=repo_carta)
    with pytest.raises(PartidaNoEncontrada):
        await s.obtener_cartas_propias(1, 1)

@pytest.mark.asyncio
async def test_ver_del_descarte_sin_repo_jugadores():
    # Si el repo de jugadores es None, retorna VerDescarteResultado vacÃ­o
    repo_partida = crear_repo_partida_mock()
    repo_carta = crear_repo_carta_mock()
    s = ServicioJuego(repo_partida, jugadores=None, cartas=repo_carta)
    res = await s.ver_del_descarte(1, 1)
    assert res.descarte == []

@pytest.mark.asyncio
async def test_obtener_cantidad_manos_partida_no_encontrada():
    # Si la partida no existe, debe lanzar PartidaNoEncontrada
    repo_partida = crear_repo_partida_mock(obtener_return=None)
    repo_jugador = crear_repo_jugador_mock()
    repo_carta = crear_repo_carta_mock()
    s = ServicioJuego(partidas=repo_partida, jugadores=repo_jugador, cartas=repo_carta)
    with pytest.raises(PartidaNoEncontrada):
        await s.obtener_cantidad_manos(123)

@pytest.mark.asyncio
async def test_obtener_cantidad_manos_sin_jugadores_en_partida():
    # Si no hay jugadores en la partida, retorna dict vacÃ­o
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=77, estado=EstadoPartida.en_juego))
    repo_jugador = crear_repo_jugador_mock(listar_por_partida_return=[])
    repo_carta = crear_repo_carta_mock()
    s = ServicioJuego(partidas=repo_partida, jugadores=repo_jugador, cartas=repo_carta)
    res = await s.obtener_cantidad_manos(77)
    assert res.cartas_por_jugador == {}

@pytest.mark.asyncio
async def test_obtener_cantidad_secretos_sin_jugadores_en_partida():
    # Si no hay jugadores en la partida, retorna dict vacÃ­o
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=77, estado=EstadoPartida.en_juego))
    repo_jugador = crear_repo_jugador_mock(listar_por_partida_return=[])
    repo_secreto = crear_repo_secreto_mock()
    s = ServicioJuego(partidas=repo_partida, jugadores=repo_jugador, secretos=repo_secreto)
    res = await s.obtener_cantidad_secretos(77)
    assert res.secretos_por_jugador == {}

@pytest.mark.asyncio
async def test_obtener_cantidad_mano_repo_cartas_none():
    # Si el repo de cartas es None, retorna cantidad 0
    repo_partida = crear_repo_partida_mock()
    s = ServicioJuego(repo_partida, cartas=None)
    res = await s.obtener_cantidad_mano(1, 1)
    assert res.cantidad == 0

@pytest.mark.asyncio
async def test_obtener_cantidad_cartas_en_mazo_repo_cartas_none():
    # Si el repo de cartas es None, retorna cantidad 0
    repo_partida = crear_repo_partida_mock()
    s = ServicioJuego(repo_partida, cartas=None)
    res = await s.obtener_cantidad_cartas_en_mazo(1)
    assert res.cantidad == 0

@pytest.mark.asyncio
async def test_repartir_cartas_partida_no_encontrada():
    # Si la partida no existe, retorna resultado vacÃ­o
    repo_partida = crear_repo_partida_mock(obtener_return=None)
    repo_jugador = crear_repo_jugador_mock()
    repo_carta = crear_repo_carta_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, cartas=repo_carta)
    res = await s.repartir_cartas(1, 3)
    assert res.repartidas == {}
    assert res.mazo == []

@pytest.mark.asyncio
async def test_repartir_cartas_sin_jugadores_en_partida():
    # Si no hay jugadores en la partida, retorna resultado vacÃ­o
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_espera(id_partida=1))
    repo_jugador = crear_repo_jugador_mock(listar_por_partida_return=[])
    repo_carta = crear_repo_carta_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, cartas=repo_carta)
    res = await s.repartir_cartas(1, 3)
    assert res.repartidas == {}
    assert res.mazo == []

@pytest.mark.asyncio
async def test_listar_en_espera_repo_none():
    # Si el repo de partidas es None, retorna lista vacÃ­a
    s = ServicioJuego(partidas=None)
    res = await s.listar_en_espera()
    assert res == []

@pytest.mark.asyncio
async def test_obtener_por_id_repo_none():
    # Si el repo de partidas es None, retorna None
    s = ServicioJuego(partidas=None)
    res = await s.obtener_por_id(123)
    assert res is None

@pytest.mark.asyncio
async def test_listar_jugadores_repo_none():
    # Si el repo de jugadores es None, retorna lista vacÃ­a
    repo_partida = crear_repo_partida_mock()
    s = ServicioJuego(repo_partida, jugadores=None)
    res = await s.listar_jugadores(1)
    assert res == []

@pytest.mark.asyncio
async def test_obtener_cantidad_secretos_repo_secretos_none():
    # Si el repo de secretos es None, retorna dict vacÃ­o
    repo_partida = crear_repo_partida_mock()
    repo_jugador = crear_repo_jugador_mock()
    s = ServicioJuego(partidas=repo_partida, jugadores=repo_jugador, secretos=None)
    res = await s.obtener_cantidad_secretos(1)
    assert res.secretos_por_jugador == {}

@pytest.mark.asyncio
async def test_obtener_cantidad_manos_repo_cartas_none():
    # Si el repo de cartas es None, retorna dict vacÃ­o
    repo_partida = crear_repo_partida_mock()
    repo_jugador = crear_repo_jugador_mock()
    s = ServicioJuego(partidas=repo_partida, jugadores=repo_jugador, cartas=None)
    res = await s.obtener_cantidad_manos(1)
    assert res.cartas_por_jugador == {}

@pytest.mark.asyncio
async def test_obtener_cantidad_manos_repo_jugadores_none():
    # Si el repo de jugadores es None, retorna dict vacÃ­o
    repo_partida = crear_repo_partida_mock()
    repo_carta = crear_repo_carta_mock()
    s = ServicioJuego(partidas=repo_partida, jugadores=None, cartas=repo_carta)
    res = await s.obtener_cantidad_manos(1)
    assert res.cartas_por_jugador == {}

@pytest.mark.asyncio
async def test_obtener_secretos_propios_jugador_no_encontrado():
    # Si el jugador no existe, lanza ValueError
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_jugador = crear_repo_jugador_mock(obtener_return=None)
    repo_secreto = crear_repo_secreto_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, secretos=repo_secreto)
    with pytest.raises(ValueError):
        await s.obtener_secretos_propios(1, 99)

@pytest.mark.asyncio
async def test_obtener_secretos_propios_partida_no_encontrada():
    # Si la partida no existe, retorna secretos vacÃ­os
    repo_partida = crear_repo_partida_mock(obtener_return=None)
    repo_jugador = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=1, id_partida=1))
    repo_secreto = crear_repo_secreto_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, secretos=repo_secreto)
    res = await s.obtener_secretos_propios(1, 1)
    assert res.secretos == []

@pytest.mark.asyncio
async def test_obtener_secretos_propios_jugador_no_en_partida():
    # Si el jugador no pertenece a la partida, lanza ValueError
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=2))
    repo_jugador = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=1, id_partida=99))
    repo_secreto = crear_repo_secreto_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, secretos=repo_secreto)
    with pytest.raises(ValueError):
        await s.obtener_secretos_propios(2, 1)

@pytest.mark.asyncio
async def test_ver_del_descarte_jugador_no_encontrado():
    # Si el jugador no existe, lanza ValueError
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_jugador = crear_repo_jugador_mock(obtener_return=None)
    repo_carta = crear_repo_carta_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, cartas=repo_carta)
    with pytest.raises(ValueError):
        await s.ver_del_descarte(1, 99)

@pytest.mark.asyncio
async def test_ver_del_descarte_partida_no_encontrada():
    # Si la partida no existe, lanza PartidaNoEncontrada
    repo_partida = crear_repo_partida_mock(obtener_return=None)
    repo_jugador = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=1, id_partida=1))
    repo_carta = crear_repo_carta_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, cartas=repo_carta)
    with pytest.raises(PartidaNoEncontrada):
        await s.ver_del_descarte(1, 1)

@pytest.mark.asyncio
async def test_ver_del_descarte_jugador_no_en_partida():
    # Si el jugador no pertenece a la partida, lanza ValueError
    repo_partida = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=2))
    repo_jugador = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=1, id_partida=99))
    repo_carta = crear_repo_carta_mock()
    s = ServicioJuego(repo_partida, jugadores=repo_jugador, cartas=repo_carta)
    with pytest.raises(ValueError):
        await s.ver_del_descarte(2, 1)

@pytest.mark.asyncio
async def test_revelar_secreto_exitoso():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=3, id_partida=1))

    secreto = crear_secreto(id_secreto=3, id_partida=1, id_jugador=3, estado=EstadoSecreto.oculto)
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[secreto])

    servicio = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s)
    resultado = await servicio.revelar_secreto(partida_id=1, jugador_id=3, secreto_id=3)

    assert isinstance(resultado, RevelarSecretoResultado)
    assert resultado.secreto.id_secreto == 3
    assert resultado.secreto.estado == EstadoSecreto.revelado

@pytest.mark.asyncio
async def test_revelar_secreto_no_encontrado():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=2, id_partida=1))

    # El secreto con ID 99 no estÃ¡ en la lista
    otro_secreto = crear_secreto(id_secreto=88, id_partida=1, id_jugador=2, estado=EstadoSecreto.oculto)
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[otro_secreto])

    servicio = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s)

    with pytest.raises(SecretoNoEncontrado):
        await servicio.revelar_secreto(partida_id=1, jugador_id=2, secreto_id=99)

@pytest.mark.asyncio
async def test_revelar_secreto_no_disponible():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=2, id_partida=1))

    # El secreto existe pero ya estÃ¡ revelado
    secreto = crear_secreto(id_secreto=99, id_partida=1, id_jugador=2, estado=EstadoSecreto.revelado)
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[secreto])

    servicio = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s)

    with pytest.raises(SecretoNoDisponible):
        await servicio.revelar_secreto(partida_id=1, jugador_id=2, secreto_id=99)

@pytest.mark.asyncio
async def test_abandonar_partida_ok_decrementa_y_elimina():
    partida = crear_partida_en_espera(id_partida=1, cantidad_jugadores=3)
    partida.id_jugador_creador = 10  # owner
    repo_p = crear_repo_partida_mock(obtener_return=partida)
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=20, id_partida=1))

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j)
    res = await s.abandonar_partida(1, 20)

    assert res.partida_id == 1
    assert res.jugador_id == 20
    assert res.cantidad_jugadores == 2  # decrementa
    repo_j.eliminar.assert_awaited_once_with(20)
    repo_p.confirmar.assert_awaited()

@pytest.mark.asyncio
async def test_abandonar_partida_owner_no_puede():
    partida = crear_partida_en_espera(id_partida=1, cantidad_jugadores=3)
    partida.id_jugador_creador = 20  # el que intenta abandonar es el owner
    repo_p = crear_repo_partida_mock(obtener_return=partida)
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=20, id_partida=1))

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j)
    with pytest.raises(CreadorNoPuedeAbandonarPartida):
        await s.abandonar_partida(1, 20)

@pytest.mark.asyncio
async def test_abandonar_partida_partida_en_juego_no_abandonable():
    partida = crear_partida_en_juego(id_partida=1, estado=EstadoPartida.en_juego, cantidad_jugadores=3)
    partida.id_jugador_creador = 10
    repo_p = crear_repo_partida_mock(obtener_return=partida)
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=20, id_partida=1))

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j)
    with pytest.raises(PartidaEnJuegoNoAbandonable):
        await s.abandonar_partida(1, 20)

@pytest.mark.asyncio
async def test_abandonar_partida_jugador_no_encontrado():
    partida = crear_partida_en_espera(id_partida=1, cantidad_jugadores=2)
    partida.id_jugador_creador = 10
    repo_p = crear_repo_partida_mock(obtener_return=partida)
    repo_j = crear_repo_jugador_mock(obtener_return=None)

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j)
    with pytest.raises(JugadorNoEncontrado):
        await s.abandonar_partida(1, 99)

@pytest.mark.asyncio
async def test_abandonar_partida_partida_no_encontrada():
    repo_p = crear_repo_partida_mock(obtener_return=None)
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=20, id_partida=1))

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j)
    with pytest.raises(PartidaNoEncontrada):
        await s.abandonar_partida(1, 20)

@pytest.mark.asyncio
async def test_abandonar_partida_jugador_no_en_partida():
    partida = crear_partida_en_espera(id_partida=1, cantidad_jugadores=3)
    partida.id_jugador_creador = 10
    repo_p = crear_repo_partida_mock(obtener_return=partida)
    # jugador en otra partida
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=20, id_partida=99))

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j)
    with pytest.raises(JugadorNoEnPartida):
        await s.abandonar_partida(1, 20)

@pytest.mark.asyncio
async def test_abandonar_partida_no_decrementa_ni_elimina_si_cantidad_igual_a_uno():
    # Caso lÃ­mite segÃºn implementaciÃ³n actual: si cantidad_jugadores <= 1, no elimina ni decrementa
    partida = crear_partida_en_espera(id_partida=1, cantidad_jugadores=1)
    partida.id_jugador_creador = 10
    repo_p = crear_repo_partida_mock(obtener_return=partida)
    # jugador no es owner (estado inconsistente, pero nos permite cubrir rama)
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=20, id_partida=1))

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j)
    res = await s.abandonar_partida(1, 20)

    assert res.cantidad_jugadores == 1
    repo_j.eliminar.assert_not_awaited()
      
@pytest.mark.asyncio
async def test_robar_secreto_exitoso():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=2, id_partida=1))

    secreto = crear_secreto(id_secreto=3, id_partida=1, id_jugador=3, estado=EstadoSecreto.revelado)
    repo_s = crear_repo_secreto_mock(obtener_secretos_revelados_return=[secreto])

    servicio = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s)
    resultado = await servicio.robar_secreto(partida_id=1, jugador_id=2, secreto_id=3)

    assert secreto.estado == EstadoSecreto.oculto
    assert secreto.id_jugador == 2

@pytest.mark.asyncio
async def test_robar_secreto_no_encontrado():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=2, id_partida=1))

    # El secreto con ID 99 no estÃ¡ en la lista
    otro_secreto = crear_secreto(id_secreto=88, id_partida=1, id_jugador=5, estado=EstadoSecreto.revelado)
    repo_s = crear_repo_secreto_mock(obtener_secretos_revelados_return=[otro_secreto])

    servicio = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s)

    with pytest.raises(SecretoNoEncontrado):
        await servicio.robar_secreto(partida_id=1, jugador_id=2, secreto_id=99)

@pytest.mark.asyncio
async def test_robar_secreto_no_disponible():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=2, id_partida=1))

    # El secreto existe pero ya estÃ ¡oculto
    secreto = crear_secreto(id_secreto=99, id_partida=1, id_jugador=9, estado=EstadoSecreto.oculto)
    # con lo siguiente, estamos asumiendo que la
    # consulta a la base de datos se puede hacer mal
    repo_s = crear_repo_secreto_mock(obtener_secretos_revelados_return=[secreto])

    servicio = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s)

    with pytest.raises(SecretoNoDisponible):
        await servicio.robar_secreto(partida_id=1, jugador_id=2, secreto_id=99)
       

@pytest.mark.asyncio
async def test_revelar_asesino():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=3, id_partida=1))

    secreto = crear_secreto(id_secreto=3, id_partida=1, id_jugador=3, estado=EstadoSecreto.oculto, tipo=TipoSecreto.asesino)
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[secreto])

    servicio = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s)
    with pytest.raises(AsesinoRevelado):
        await servicio.revelar_secreto(partida_id=1, jugador_id=3, secreto_id=3)

@pytest.mark.asyncio
async def test_verificar_seleccionar_ok_sin_posicion():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    # origen y seleccionado distintos, y el set pertenece a otro jugador (no al seleccionado)
    repo_j.obtener = AsyncMock(side_effect=[crear_jugador(id_jugador=10, id_partida=1), crear_jugador(id_jugador=20, id_partida=1)])
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[crear_secreto(id_secreto=1, id_partida=1, id_jugador=20)])
    repo_sets = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=5, id_partida=1, id_jugador=10))

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s, sets=repo_sets)
    # no debe levantar
    await s.verificar_seleccionar_jugador_set(1, 10, 5, 20, None)


@pytest.mark.asyncio
async def test_verificar_seleccionar_ok_con_posicion_valida():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=2))
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    repo_j.obtener = AsyncMock(side_effect=[crear_jugador(id_jugador=11, id_partida=2), crear_jugador(id_jugador=22, id_partida=2)])
    secretos_lista = [crear_secreto(id_secreto=i, id_partida=2, id_jugador=22) for i in (1,2,3)]
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=secretos_lista, contar_secretos_jugador_return=len(secretos_lista))
    repo_sets = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=6, id_partida=2, id_jugador=11))

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s, sets=repo_sets)
    # posicion 2 existe -> no debe levantar
    await s.verificar_seleccionar_jugador_set(2, 11, 6, 22, 2)


@pytest.mark.asyncio
async def test_verificar_seleccionar_no_secretos_lanza_excepcion():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=3))
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    repo_j.obtener = AsyncMock(side_effect=[crear_jugador(id_jugador=12, id_partida=3), crear_jugador(id_jugador=24, id_partida=3)])
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[])
    repo_sets = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=7, id_partida=3, id_jugador=12))

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s, sets=repo_sets)
    with pytest.raises(SecretoNoEncontrado):
        await s.verificar_seleccionar_jugador_set(3, 12, 7, 24, None)


@pytest.mark.asyncio
async def test_verificar_seleccionar_posicion_fuera_de_rango_lanza_excepcion():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=4))
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    repo_j.obtener = AsyncMock(side_effect=[crear_jugador(id_jugador=13, id_partida=4), crear_jugador(id_jugador=26, id_partida=4)])
    secretos_lista = [crear_secreto(id_secreto=1, id_partida=4, id_jugador=26)]
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=secretos_lista, contar_secretos_jugador_return=1)
    repo_sets = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=8, id_partida=4, id_jugador=13))

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s, sets=repo_sets)
    with pytest.raises(SecretoNoEncontrado):
        await s.verificar_seleccionar_jugador_set(4, 13, 8, 26, 1)


@pytest.mark.asyncio
async def test_verificar_seleccionar_origen_no_encontrado_lanza_excepcion():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=5))
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    # origen no encontrado -> primera llamada None
    repo_j.obtener = AsyncMock(side_effect=[None])
    repo_s = crear_repo_secreto_mock()
    repo_sets = crear_repo_set_mock()

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s, sets=repo_sets)
    with pytest.raises(JugadorNoEncontrado):
        await s.verificar_seleccionar_jugador_set(5, 999, 1, 2, None)


@pytest.mark.asyncio
async def test_verificar_seleccionar_set_no_encontrado_lanza_excepcion():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=6))
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    repo_j.obtener = AsyncMock(side_effect=[crear_jugador(id_jugador=14, id_partida=6), crear_jugador(id_jugador=28, id_partida=6)])
    repo_sets = crear_repo_set_mock(obtener_set_por_id_return=None)
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[crear_secreto(id_secreto=1, id_partida=6, id_jugador=28)])

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s, sets=repo_sets)
    with pytest.raises(SetNoEncontrado):
        await s.verificar_seleccionar_jugador_set(6, 14, 999, 28, None)


@pytest.mark.asyncio
async def test_verificar_seleccionar_set_no_corresponde_lanza_excepcion():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=7))
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    repo_j.obtener = AsyncMock(side_effect=[crear_jugador(id_jugador=15, id_partida=7), crear_jugador(id_jugador=30, id_partida=7)])
    # set pertenece a jugador diferente
    repo_sets = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=9, id_partida=7, id_jugador=99))
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[crear_secreto(id_secreto=1, id_partida=7, id_jugador=30)])

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s, sets=repo_sets)
    with pytest.raises(SetNoCorrespondeAlJugadorSeleccionado):
        await s.verificar_seleccionar_jugador_set(7, 15, 9, 30, None)


@pytest.mark.asyncio
async def test_verificar_seleccionar_no_puede_aplicarse_efecto_de_su_propio_set_lanza_excepcion():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=8))
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    # origen == propietario del set
    repo_j.obtener = AsyncMock(side_effect=[crear_jugador(id_jugador=16, id_partida=8), crear_jugador(id_jugador=16, id_partida=8)])
    repo_sets = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=10, id_partida=8, id_jugador=16))
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[crear_secreto(id_secreto=1, id_partida=8, id_jugador=16)])

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s, sets=repo_sets)
    with pytest.raises(NoPuedeAplicarseEfectosAsiMismo):
        await s.verificar_seleccionar_jugador_set(8, 16, 10, 16, None)

@pytest.mark.asyncio  
async def test_ocultar_secreto_exitoso():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=2))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=3, id_partida=2))

    secreto = crear_secreto(id_secreto=2, id_partida=2, id_jugador=3, estado=EstadoSecreto.revelado)
    repo_s = crear_repo_secreto_mock(obtener_secreto_return=secreto)

    servicio = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s)
    resultado = await servicio.ocultar_secreto(partida_id=2, jugador_id=3, secreto_id=2)

    assert isinstance(resultado, OcultarSecretoResultado)
    assert resultado.secreto.id_secreto == 2
    assert resultado.secreto.estado == EstadoSecreto.oculto

@pytest.mark.asyncio
async def test_ocultar_secreto_no_encontrado():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=2))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=3, id_partida=2))
    repo_s = crear_repo_secreto_mock(obtener_secreto_return=None)  # simula que no se encuentra el secreto

    servicio = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s)

    with pytest.raises(SecretoNoEncontrado):
        await servicio.ocultar_secreto(partida_id=2, jugador_id=3, secreto_id=99)

@pytest.mark.asyncio
async def test_ocultar_secreto_no_disponible():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=2))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=3, id_partida=2))

    # secreto ya oculto, no deberia poder ocultarse de nuevo
    secreto = crear_secreto(id_secreto=2, id_partida=2, id_jugador=3, estado=EstadoSecreto.oculto)
    repo_s = crear_repo_secreto_mock(obtener_secreto_return=secreto)

    servicio = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s)

    with pytest.raises(SecretoNoDisponible):
        await servicio.ocultar_secreto(partida_id=2, jugador_id=3, secreto_id=2)

@pytest.mark.asyncio
async def test_verificar_seleccionar_miss_marple_sin_posicion_lanza_posicion_no_proporcionada():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=9))
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    repo_j.obtener = AsyncMock(side_effect=[crear_jugador(id_jugador=17, id_partida=9), crear_jugador(id_jugador=34, id_partida=9)])
    repo_sets = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=12, id_partida=9, id_jugador=17, nombre="Miss Marple"))
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[crear_secreto(id_secreto=1, id_partida=9, id_jugador=34)])

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s, sets=repo_sets)
    with pytest.raises(PosicionSecretoNoProporcionada):
        await s.verificar_seleccionar_jugador_set(9, 17, 12, 34, None)

@pytest.mark.asyncio
async def test_verificar_seleccionar_hercule_poirot_sin_posicion_lanza_posicion_no_proporcionada():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=10))
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    repo_j.obtener = AsyncMock(side_effect=[crear_jugador(id_jugador=18, id_partida=10), crear_jugador(id_jugador=36, id_partida=10)])
    repo_sets = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=13, id_partida=10, id_jugador=18, nombre="Hercule Poirot"))
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[crear_secreto(id_secreto=1, id_partida=10, id_jugador=36)])

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s, sets=repo_sets)
    with pytest.raises(PosicionSecretoNoProporcionada):
        await s.verificar_seleccionar_jugador_set(10, 18, 13, 36, None)

@pytest.mark.asyncio
async def test_verificar_seleccionar_parker_pyne_lanza_no_puede_aplicarse_efectos():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=11))
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    repo_j.obtener = AsyncMock(side_effect=[crear_jugador(id_jugador=19, id_partida=11), crear_jugador(id_jugador=38, id_partida=11)])
    repo_sets = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=14, id_partida=11, id_jugador=19, nombre="Parker Pyne"))
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[crear_secreto(id_secreto=1, id_partida=11, id_jugador=38)])

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s, sets=repo_sets)
    with pytest.raises(NoPuedeAplicarseEfectosAsiMismo):
        await s.verificar_seleccionar_jugador_set(11, 19, 14, 38, None)

@pytest.mark.asyncio
async def test_verificar_seleccionar_mr_satterthwaite_con_posicion_lanza_set_no_soporta():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=12))
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    repo_j.obtener = AsyncMock(side_effect=[crear_jugador(id_jugador=20, id_partida=12), crear_jugador(id_jugador=40, id_partida=12)])
    repo_sets = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=15, id_partida=12, id_jugador=20, nombre="Mr Satterthwaite"))
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[crear_secreto(id_secreto=1, id_partida=12, id_jugador=40)])

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s, sets=repo_sets)
    with pytest.raises(SetNoSoportaSeleccionDeJugador):
        await s.verificar_seleccionar_jugador_set(12, 20, 15, 40, 1)

@pytest.mark.asyncio
async def test_verificar_seleccionar_bundle_con_posicion_lanza_set_no_soporta():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=13))
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    repo_j.obtener = AsyncMock(side_effect=[crear_jugador(id_jugador=21, id_partida=13), crear_jugador(id_jugador=42, id_partida=13)])
    repo_sets = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=16, id_partida=13, id_jugador=21, nombre='Lady Eileen "Bundle" Brent'))
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[crear_secreto(id_secreto=1, id_partida=13, id_jugador=42)])

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s, sets=repo_sets)
    with pytest.raises(SetNoSoportaSeleccionDeJugador):
        await s.verificar_seleccionar_jugador_set(13, 21, 16, 42, 1)

@pytest.mark.asyncio
async def test_verificar_seleccionar_beresford_con_posicion_lanza_set_no_soporta():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=14))
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    repo_j.obtener = AsyncMock(side_effect=[crear_jugador(id_jugador=22, id_partida=14), crear_jugador(id_jugador=44, id_partida=14)])
    repo_sets = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=17, id_partida=14, id_jugador=22, nombre="Beresford"))
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[crear_secreto(id_secreto=1, id_partida=14, id_jugador=44)])

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s, sets=repo_sets)
    with pytest.raises(SetNoSoportaSeleccionDeJugador):
        await s.verificar_seleccionar_jugador_set(14, 22, 17, 44, 1)

@pytest.mark.asyncio
async def test_verificar_seleccionar_mr_satterthwaite_ok_sin_posicion():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=15))
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    repo_j.obtener = AsyncMock(side_effect=[crear_jugador(id_jugador=23, id_partida=15), crear_jugador(id_jugador=46, id_partida=15)])
    repo_sets = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=18, id_partida=15, id_jugador=23, nombre="Mr Satterthwaite"))
    repo_s = crear_repo_secreto_mock(obtener_secretos_return=[crear_secreto(id_secreto=1, id_partida=15, id_jugador=46)])

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, secretos=repo_s, sets=repo_sets)
    # No debe lanzar porque este set no requiere posición
    await s.verificar_seleccionar_jugador_set(15, 23, 18, 46, None)

@pytest.mark.asyncio
async def test_aplicar_efectos_set_poirot_revela_ok():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=2, id_partida=1))
    repo_set = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=5, id_partida=1, id_jugador=3, nombre="Hercule Poirot"))
    # orden de secretos del jugador colocamos el afectado en índice 1
    secreto = crear_secreto(id_secreto=7, id_partida=1, id_jugador=2, estado=EstadoSecreto.oculto)
    otro = crear_secreto(id_secreto=99, id_partida=1, id_jugador=2, estado=EstadoSecreto.oculto)
    repo_s = crear_repo_secreto_mock(obtener_secreto_return=secreto, obtener_secretos_return=[otro, secreto])
    s = ServicioJuego(repo_p, jugadores=repo_j, sets=repo_set, secretos=repo_s)
    s.revelar_secreto = AsyncMock(return_value=object())
    res = await s.aplicar_efectos_set(1, 2, 5, 7)
    s.revelar_secreto.assert_awaited_once_with(1, 2, 7)
    assert res.posicion_secreto == 1
    assert getattr(res.secreto_afectado, "id_secreto", None) == 7

@pytest.mark.asyncio
async def test_aplicar_efectos_set_mr_satterthwaite_con_wildcard():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=2, id_partida=1))
    set_obj = crear_set(id_set=5, id_partida=1, id_jugador=3, nombre="Mr Satterthwaite")
    repo_set = crear_repo_set_mock(obtener_set_por_id_return=set_obj, obtener_cartas_del_set_return=[type("C", (), {"nombre": "Harley Quin Wildcard"})()])
    secreto = crear_secreto(id_secreto=7, id_partida=1, id_jugador=2, estado=EstadoSecreto.oculto)
    otro = crear_secreto(id_secreto=88, id_partida=1, id_jugador=2, estado=EstadoSecreto.oculto)
    repo_s = crear_repo_secreto_mock(obtener_secreto_return=secreto, obtener_secretos_return=[otro, secreto])
    s = ServicioJuego(repo_p, jugadores=repo_j, sets=repo_set, secretos=repo_s)
    s.revelar_secreto = AsyncMock(return_value=object())
    s.robar_secreto = AsyncMock(return_value=object())
    res = await s.aplicar_efectos_set(1, 2, 5, 7)
    s.revelar_secreto.assert_awaited_once_with(1, 2, 7)
    s.robar_secreto.assert_awaited_once_with(1, 3, 7)
    assert res.posicion_secreto == 1
    assert getattr(res.secreto_afectado, "id_secreto", None) == 7

@pytest.mark.asyncio
async def test_aplicar_efectos_set_mr_satterthwaite_sin_wildcard():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=2, id_partida=1))
    set_obj = crear_set(id_set=5, id_partida=1, id_jugador=3, nombre="Mr Satterthwaite")
    repo_set = crear_repo_set_mock(obtener_set_por_id_return=set_obj, obtener_cartas_del_set_return=[type("C", (), {"nombre": "Otra"})()])
    secreto = crear_secreto(id_secreto=7, id_partida=1, id_jugador=2, estado=EstadoSecreto.oculto)
    otro = crear_secreto(id_secreto=55, id_partida=1, id_jugador=2, estado=EstadoSecreto.oculto)
    repo_s = crear_repo_secreto_mock(obtener_secreto_return=secreto, obtener_secretos_return=[otro, secreto])
    s = ServicioJuego(repo_p, jugadores=repo_j, sets=repo_set, secretos=repo_s)
    s.revelar_secreto = AsyncMock(return_value=object())
    s.robar_secreto = AsyncMock()
    res = await s.aplicar_efectos_set(1, 2, 5, 7)
    s.revelar_secreto.assert_awaited_once_with(1, 2, 7)
    s.robar_secreto.assert_not_awaited()
    assert res.posicion_secreto == 1
    assert getattr(res.secreto_afectado, "id_secreto", None) == 7

@pytest.mark.asyncio
async def test_aplicar_efectos_set_parker_pyne_oculta_objetivo():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=2, id_partida=1))
    set_obj = crear_set(id_set=5, id_partida=1, id_jugador=3, nombre="Parker Pyne")
    repo_set = crear_repo_set_mock(obtener_set_por_id_return=set_obj)
    # La lógica real oculta el secreto específico del jugador objetivo
    secreto_revelado_objetivo = crear_secreto(id_secreto=7, id_partida=1, id_jugador=2, estado=EstadoSecreto.revelado)
    otro = crear_secreto(id_secreto=77, id_partida=1, id_jugador=2, estado=EstadoSecreto.revelado)
    repo_s = crear_repo_secreto_mock(obtener_secreto_return=secreto_revelado_objetivo, obtener_secretos_return=[otro, secreto_revelado_objetivo])
    s = ServicioJuego(repo_p, jugadores=repo_j, sets=repo_set, secretos=repo_s)
    s.ocultar_secreto = AsyncMock(return_value=object())
    res = await s.aplicar_efectos_set(1, 2, 5, 7)
    s.ocultar_secreto.assert_awaited_once_with(1, 2, 7)
    assert res.posicion_secreto == 1
    assert getattr(res.secreto_afectado, "id_secreto", None) == 7

@pytest.mark.asyncio
async def test_aplicar_efectos_set_parker_pyne_sin_revelados_lanza():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=2, id_partida=1))
    set_obj = crear_set(id_set=5, id_partida=1, id_jugador=3, nombre="Parker Pyne")
    repo_set = crear_repo_set_mock(obtener_set_por_id_return=set_obj)
    # No incluimos el secreto en la lista ordenada para que falle la búsqueda por posición
    otro = crear_secreto(id_secreto=123, id_partida=1, id_jugador=2, estado=EstadoSecreto.revelado)
    repo_s = crear_repo_secreto_mock(obtener_secreto_return=None, obtener_secretos_revelados_return=[], obtener_secretos_return=[otro])
    s = ServicioJuego(repo_p, jugadores=repo_j, sets=repo_set, secretos=repo_s)
    with pytest.raises(SecretoNoEncontrado):
        await s.aplicar_efectos_set(1, 2, 5, 7)

@pytest.mark.asyncio
async def test_aplicar_efectos_set_errores_basicos():
    # Partida no encontrada
    repo_p = crear_repo_partida_mock(obtener_return=None)
    s = ServicioJuego(repo_p)
    with pytest.raises(PartidaNoEncontrada):
        await s.aplicar_efectos_set(1, 2, 5, 7)

    # Set no encontrado
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_set = crear_repo_set_mock(obtener_set_por_id_return=None)
    s = ServicioJuego(repo_p, sets=repo_set)
    with pytest.raises(SetNoEncontrado):
        await s.aplicar_efectos_set(1, 2, 5, 7)

    # Set no en partida
    set_obj = crear_set(id_set=5, id_partida=99, id_jugador=3, nombre="Hercule Poirot")
    repo_set = crear_repo_set_mock(obtener_set_por_id_return=set_obj)
    s = ServicioJuego(repo_p, sets=repo_set)
    with pytest.raises(SetNoEnPartida):
        await s.aplicar_efectos_set(1, 2, 5, 7)

    # Jugador no encontrado
    repo_j = crear_repo_jugador_mock(obtener_return=None)
    repo_set = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=5, id_partida=1, id_jugador=3, nombre="Hercule Poirot"))
    s = ServicioJuego(repo_p, jugadores=repo_j, sets=repo_set)
    with pytest.raises(JugadorNoEncontrado):
        await s.aplicar_efectos_set(1, 2, 5, 7)

    # Jugador no en partida
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=2, id_partida=99))
    s = ServicioJuego(repo_p, jugadores=repo_j, sets=repo_set)
    with pytest.raises(JugadorNoEnPartida):
        await s.aplicar_efectos_set(1, 2, 5, 7)

    # Secreto no encontrado
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=2, id_partida=1))
    # Lista de secretos vacía asegura que falle por posición no encontrada
    repo_s = crear_repo_secreto_mock(obtener_secreto_return=None, obtener_secretos_return=[])
    s = ServicioJuego(repo_p, jugadores=repo_j, sets=repo_set, secretos=repo_s)
    with pytest.raises(SecretoNoEncontrado):
        await s.aplicar_efectos_set(1, 2, 5, 7)

@pytest.mark.asyncio
async def test_aplicar_efectos_set_posicion():
    """Verifica que posicion_secreto se tome el índice del secreto en la lista ordenada."""
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=2, id_partida=1))
    repo_set = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=5, id_partida=1, id_jugador=3, nombre="Hercule Poirot"))
    # orden: [5, 7, 8] -> el 7 está en índice 1
    sec_a = crear_secreto(id_secreto=5, id_partida=1, id_jugador=2, estado=EstadoSecreto.oculto)
    sec_b = crear_secreto(id_secreto=7, id_partida=1, id_jugador=2, estado=EstadoSecreto.oculto)
    sec_c = crear_secreto(id_secreto=8, id_partida=1, id_jugador=2, estado=EstadoSecreto.oculto)
    repo_s = crear_repo_secreto_mock(obtener_secreto_return=sec_b, obtener_secretos_return=[sec_a, sec_b, sec_c])
    s = ServicioJuego(repo_p, jugadores=repo_j, sets=repo_set, secretos=repo_s)
    s.revelar_secreto = AsyncMock(return_value=object())
    res = await s.aplicar_efectos_set(1, 2, 5, 7)
    assert res.posicion_secreto == 1
    assert getattr(res.secreto_afectado, "id_secreto", None) == 7


@pytest.mark.asyncio
async def test_aplicar_efectos_set_asesino_revelado_burbujea_excepcion():
    repo_p = crear_repo_partida_mock(obtener_return=crear_partida_en_juego(id_partida=1))
    repo_j = crear_repo_jugador_mock(obtener_return=crear_jugador(id_jugador=2, id_partida=1))
    repo_set = crear_repo_set_mock(obtener_set_por_id_return=crear_set(id_set=5, id_partida=1, id_jugador=3, nombre="Hercule Poirot"))
    # preparar secreto asesino como parte de la lista ordenada
    asesino = crear_secreto(id_secreto=7, id_partida=1, id_jugador=2, estado=EstadoSecreto.oculto)
    otro = crear_secreto(id_secreto=6, id_partida=1, id_jugador=2, estado=EstadoSecreto.oculto)
    repo_s = crear_repo_secreto_mock(obtener_secreto_return=asesino, obtener_secretos_return=[otro, asesino])
    s = ServicioJuego(repo_p, jugadores=repo_j, sets=repo_set, secretos=repo_s)
    # simular que revelar_secreto lanza AsesinoRevelado
    s.revelar_secreto = AsyncMock(side_effect=AsesinoRevelado())
    with pytest.raises(AsesinoRevelado):
        await s.aplicar_efectos_set(1, 2, 5, 7)


# la funcion a testear es sincrona en realidad, asi que puedo hacer esto
@pytest.mark.parametrize("tipo_accion, payload, esperado", [
    ("jugar_evento", {"nombre": "Evento Normal"}, True),
    ("jugar_evento", {"nombre": "cards off the table"}, False),
    ("jugar_set", {}, True),
    ("agregar_a_set", {}, True),
    ("jugar_nsf", {}, True),
    ("otra_cosa_loca", {}, False),
    ("jugar_evento", {}, True), # el test de payload vacio
 ])
 def test_regla_nsf_cancelable_simple(tipo_accion: str, payload: Dict[str, Any], esperado: bool):
    """
    verifico los casos simples de cancelacion.
    Para la funcion que testeo, no necesito mocks 
    (pues es sincrona y no esta dentro de ninguna clase)
    """

    resultado = _regla_nsf_es_cancelable_simple(tipo_accion, payload)
    assert resultado == esperado
    

@pytest.mark.asyncio
async def test_accion_cancelable_beresford_en_set():
    tommy = crear_carta(id_carta=100, nombre="Tommy Beresford")
    tuppence = crear_carta(id_carta=101, nombre="Tuppence Beresford")

    repo_c = crear_repo_carta_mock(obtener_cartas_propias_return=[tommy, tuppence])
    
    s = ServicioJuego(
        partidas=crear_repo_partida_mock(),
        jugadores=crear_repo_jugador_mock(),
        cartas=repo_c,
        )
    
    payload = {"cartas_id": [100, 101], "id_jugador": 1} # no manejo el id del jugador en la funcion que testeo
    
    res = await s.es_accion_cancelable_en_contexto(
        partida_id=1,
        tipo_accion="jugar_set",
        payload=payload,
        id_jugador_accion=1
        )

    assert res == False
    s.obtener_cartas_propias.assert_called_once_with(1,1)

@pytest.mark.asyncio
async def test_accion_cancelable_set_normal():

    carta = crear_carta(id_carta=101, nombre="Hercule Poirot")

    repo_c = crear_repo_carta_mock(obtener_cartas_propias_return=[carta])
    
    s = ServicioJuego(
        partidas=crear_repo_partida_mock(),
        jugadores=crear_repo_jugador_mock(),
        cartas=repo_c,
        )
    
    payload = {"cartas_id": [101], "id_jugador": 1} 
    
    res = await s.es_accion_cancelable_en_contexto(
        partida_id=1,
        tipo_accion="jugar_set",
        payload=payload,
        id_jugador_accion=1
        )

    assert res == True

@pytest.mark.asyncio
async def test_es_carta_nsf_bonito():

    partida = crear_partida_en_juego(id_partida=1)
    jugador = crear_jugador(id_jugador=2, id_partida=1)
    nsf = crear_carta(id_carta=12, nombre="Not So Fast")

    repo_p = crear_repo_partida_mock(obtener_return=partida)
    repo_j = crear_repo_jugador_mock(obtener_return=jugador)
    repo_c = crear_repo_carta_mock(obtener_carta_return=nsf)

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, cartas=repo_c)

    try:
        await s.es_carta_nsf(partida_id=1, jugador_id=2, carta_id=12)
    except Exception as e:
        pytest.fail(f"fallo y no deberia haber pasado" {e}")

    repo_j.obtener.assert_called_once_with(2)
    repo_p.obtener.assert_called_once_with(1)
    repo_c.obtener_carta.assert_called_once_with(1, 2, 12)

@pytest.mark.asyncio
async def test_es_carta_nsf_falla_no_es_nsf():
        
    partida = crear_partida_en_juego(id_partida=1)
    jugador = crear_jugador(id_jugador=2, id_partida=1)
    nsf = crear_carta(id_carta=12, nombre="Hercule Poirot")

    repo_p = crear_repo_partida_mock(obtener_return=partida)
    repo_j = crear_repo_jugador_mock(obtener_return=jugador)
    repo_c = crear_repo_carta_mock(obtener_carta_return=nsf)

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, cartas=repo_c)

    with pytest.raises(ValueError, match="no_es_nsf_pero_intento_actuar_como_nsf"):
        await s.es_carta_nsf(partida_id=1, jugador_id=2, carta_id=12)

@pytest.mark.asyncio
async def test_es_carta_nsf_jugador_no_en_partida():

    partida = crear_partida_en_juego(id_partida=1)
    jugador = crear_jugador(id_jugador=2, id_partida=2)
    nsf = crear_carta(id_carta=12, nombre="Not So Fast")

    repo_p = crear_repo_partida_mock(obtener_return=partida)
    repo_j = crear_repo_jugador_mock(obtener_return=jugador)
    repo_c = crear_repo_carta_mock(obtener_carta_return=nsf)

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, cartas=repo_c)

    with pytest.raises(ValueError, match="jugador_no_en_partida"):
        await s.es_carta_nsf(partida_id=1, jugador_id=2, carta_id=12)

    assert s.cartas.obtener_carta.called == False
    
@pytest.mark.asyncio
async def test_es_carta_nsf_jugador_no_encontrado():
    
    partida = crear_partida_en_juego(id_partida=1)
    nsf = crear_carta(id_carta=12, nombre="Not So Fast")

    repo_p = crear_repo_partida_mock(obtener_return=partida)
    repo_j = crear_repo_jugador_mock()
    repo_c = crear_repo_carta_mock(obtener_carta_return=nsf)

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, cartas=repo_c)

    with pytest.raises(ValueError, match="jugador_no_encontrado"):
        await s.es_carta_nsf(partida_id=1, jugador_id=2, carta_id=12)

    assert s.cartas.obtener_carta.called == False

@pytest.mark.asyncio
async def test_es_carta_nsf_partida_no_encontrada():

    jugador = crear_jugador(id_jugador=2, id_partida=2)
    nsf = crear_carta(id_carta=12, nombre="Not So Fast")

    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock(obtener_return=jugador)
    repo_c = crear_repo_carta_mock(obtener_carta_return=nsf)

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, cartas=repo_c)

    with pytest.raises(PartidaNoEncontrada):
        await s.es_carta_nsf(partida_id=1, jugador_id=2, carta_id=12)

    assert s.cartas.obtener_carta.called == False

@pytest.mark.asyncio
async def test_es_carta_nsf_no_hay_tal_carta():

    partida = crear_partida_en_juego(id_partida=1)
    jugador = crear_jugador(id_jugador=2, id_partida=2)

    repo_p = crear_repo_partida_mock(obtener_return=partida)
    repo_j = crear_repo_jugador_mock(obtener_return=jugador)
    repo_c = crear_repo_carta_mock()

    s = ServicioJuego(partidas=repo_p, jugadores=repo_j, cartas=repo_c)

    with pytest.raises(ValueError, match="no_hay_tal_carta"):
        await s.es_carta_nsf(partida_id=1, jugador_id=2, carta_id=12)

    assert s.cartas.obtener_carta.called == True
