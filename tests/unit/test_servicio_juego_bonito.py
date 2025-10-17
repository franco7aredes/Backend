import pytest
from unittest.mock import AsyncMock
from typing import List, Optional
from datetime import datetime, date

from app.capa_2_logica.servicio_juego import ServicioJuego
from app.capa_2_logica.errores import PartidaNoEncontrada
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
    # Repos de fábrica reutilizables
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
    repo_p3.obtener.return_value = crear_partida_en_juego(cantidad_jugadores=2, estado = EstadoPartida.en_juego, turno_actual=1)
    repo_j3.obtener.return_value = None
    with pytest.raises(ValueError):
        await s.terminar_turno(1, 2)

    # turno inválido
    repo_j3.obtener.return_value = crear_jugador(orden_turno=2)
    with pytest.raises(PermissionError):
        await s.terminar_turno(1, 2)


@pytest.mark.asyncio
async def test_obtener_cartas_propias():
    from app.capa_0_definicion_bd.models.cartas_modelos import TipoCarta

    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock()
    # jugador y partida válidos
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
async def test_obtener_draft_bonito():
    repo_p = crear_repo_partida_mock()
    repo_j = crear_repo_jugador_mock()

    repo_j.obtener.return_value = crear_jugador(id_jugador=10, id_partida=77)
    repo_p.obtener.return_value = crear_partida_en_juego(id_partida=77, estado=EstadoPartida.en_juego)

    # Cartas en draft mock
    c1 = crear_carta(id_carta=1, id_partida=77, posicion=PosicionCarta.draft)
    c1.nombre, c1.tipo = "Not so fast", TipoCarta.instant
    c2 = crear_carta(id_carta=4, id_partida=77, posicion=PosicionCarta.draft)
    c2.nombre, c2.tipo = "Not so fast", TipoCarta.instant
    c3 = crear_carta(id_carta=7, id_partida=77, posicion=PosicionCarta.draft)
    c3.nombre, c3.tipo = "Not so fast", TipoCarta.instant

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

    # Repositorio de secretos con el método mockeado correctamente
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

    # Cartas: 2 normales + 1 comodín
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
    