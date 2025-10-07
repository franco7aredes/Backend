import pytest
from unittest.mock import AsyncMock
from typing import List, Optional

from app.capa_2_logica.servicio_juego import ServicioJuego
from app.capa_2_logica.errores import PartidaNoEncontrada
from app.capa_0_definicion_bd.models.partidas_modelos import Partida as PartidaModelo, EstadoPartida
from app.capa_0_definicion_bd.models.jugadores_modelos import Jugador as JugadorModelo
from app.capa_0_definicion_bd.models.cartas_modelos import Carta as CartaModelo, PosicionCarta


@pytest.mark.asyncio
async def test_terminar_turno_avanza_bien():
    # Mocks de repos
    class RepoP:
        db = object()
        async def crear(self, partida: PartidaModelo) -> PartidaModelo: ...
        async def obtener(self, partida_id: int) -> Optional[PartidaModelo]: ...
        async def listar_en_espera(self) -> List[PartidaModelo]: ...
        async def guardar(self, partida: PartidaModelo) -> None: ...

    class RepoJ:
        db = object()
        async def listar_por_partida(self, partida_id: int) -> List[JugadorModelo]: ...
        async def crear(self, jugador: JugadorModelo) -> JugadorModelo: ...
        async def obtener(self, jugador_id: int) -> Optional[JugadorModelo]: ...

    repo_partida = RepoP()
    repo_jugador = RepoJ()

    class P:  # mínima estructura
        id_partida = 1
        estado = EstadoPartida.en_juego
        cantidad_jugadores = 3
        turno_actual = 1
    class J:
        id_jugador = 10
        orden_turno = 1

    repo_partida.obtener = AsyncMock(return_value=P())
    repo_partida.guardar = AsyncMock()
    repo_jugador.obtener = AsyncMock(return_value=J())

    s = ServicioJuego(repo_partida, jugadores=repo_jugador)
    nuevo = await s.terminar_turno(1, 10)
    assert nuevo.turno_nuevo == 2
    repo_partida.guardar.assert_awaited()


@pytest.mark.asyncio
async def test_iniciar_y_preparar_partida_not_found():
    class RepoP2:
        db = object()
        async def crear(self, partida: PartidaModelo) -> PartidaModelo: ...
        async def obtener(self, partida_id: int) -> Optional[PartidaModelo]: ...
        async def listar_en_espera(self) -> List[PartidaModelo]: ...
        async def guardar(self, partida: PartidaModelo) -> None: ...

    repo_partida = RepoP2()
    repo_partida.obtener = AsyncMock(return_value=None)
    s = ServicioJuego(repo_partida)

    with pytest.raises(PartidaNoEncontrada):
        await s.iniciar_y_preparar_partida(999, 3)


@pytest.mark.asyncio
async def test_iniciar_partida_errores():
    class RepoP:
        db = object()
        async def crear(self, partida: PartidaModelo) -> PartidaModelo: ...
        async def obtener(self, partida_id: int) -> Optional[PartidaModelo]: ...
        async def listar_en_espera(self) -> List[PartidaModelo]: ...
        async def guardar(self, partida: PartidaModelo) -> None: ...

    repo_p0 = RepoP()
    s = ServicioJuego(repo_p0)
    # not found
    repo_p0.obtener = AsyncMock(return_value=None)
    with pytest.raises(PartidaNoEncontrada):
        await s.iniciar_partida(1)

    # ya en juego
    class P:
        estado = EstadoPartida.en_juego
        cantidad_jugadores = 2
        minimo = 2
    repo_p0.obtener = AsyncMock(return_value=P())
    from app.capa_2_logica.errores import PartidaYaEnJuego
    with pytest.raises(PartidaYaEnJuego):
        await s.iniciar_partida(1)

    # minimo no alcanzado
    class P2:
        estado = EstadoPartida.en_espera
        cantidad_jugadores = 1
        minimo = 2
    repo_p0.obtener = AsyncMock(return_value=P2())
    from app.capa_2_logica.errores import MinimoJugadoresNoAlcanzado
    with pytest.raises(MinimoJugadoresNoAlcanzado):
        await s.iniciar_partida(1)


@pytest.mark.asyncio
async def test_unirse_a_partida_errores():
    class RepoP:
        db = object()
        async def crear(self, partida: PartidaModelo) -> PartidaModelo: ...
        async def obtener(self, partida_id: int) -> Optional[PartidaModelo]: ...
        async def listar_en_espera(self) -> List[PartidaModelo]: ...
        async def guardar(self, partida: PartidaModelo) -> None: ...

    class RepoJ:
        db = object()
        async def listar_por_partida(self, partida_id: int) -> List[JugadorModelo]: ...
        async def crear(self, jugador: JugadorModelo) -> JugadorModelo: ...
        async def obtener(self, jugador_id: int) -> Optional[JugadorModelo]: ...

    repo_p1 = RepoP()
    repo_j1 = RepoJ()
    s = ServicioJuego(repo_p1, jugadores=repo_j1)

    # not found
    repo_p1.obtener = AsyncMock(return_value=None)
    with pytest.raises(PartidaNoEncontrada):
        await s.unirse_a_partida(1, "A", __import__('datetime').datetime(2000,1,1))

    # llena
    class P:
        id_partida = 1
        estado = EstadoPartida.en_espera
        cantidad_jugadores = 4
        maximo = 4
    repo_p1.obtener = AsyncMock(return_value=P())
    from app.capa_2_logica.errores import MaximoJugadoresAlcanzado
    with pytest.raises(MaximoJugadoresAlcanzado):
        await s.unirse_a_partida(1, "A", __import__('datetime').datetime(2000,1,1))


@pytest.mark.asyncio
async def test_reponer_del_mazo_casos():
    class RepoP:
        db = object()
        async def crear(self, partida: PartidaModelo) -> PartidaModelo: ...
        async def obtener(self, partida_id: int) -> Optional[PartidaModelo]: ...
        async def listar_en_espera(self) -> List[PartidaModelo]: ...
        async def guardar(self, partida: PartidaModelo) -> None: ...

    class RepoJ:
        db = object()
        async def listar_por_partida(self, partida_id: int) -> List[JugadorModelo]: ...
        async def crear(self, jugador: JugadorModelo) -> JugadorModelo: ...
        async def obtener(self, jugador_id: int) -> Optional[JugadorModelo]: ...

    class RepoC:
        db = object()
        async def crear_muchas(self, cartas: List[CartaModelo]) -> None: ...
        async def contar_en_mano(self, partida_id: int, jugador_id: int) -> int: ...
        async def obtener_mazo_disponible(self, partida_id: int, limite: int) -> List[CartaModelo]: ...

    repo_p2 = RepoP()
    repo_j2 = RepoJ()
    repo_c2 = RepoC()
    s = ServicioJuego(repo_p2, jugadores=repo_j2, cartas=repo_c2)

    # jugador no encontrado
    repo_j2.obtener = AsyncMock(return_value=None)
    with pytest.raises(ValueError):
        await s.reponer_del_mazo(1, 99)

    # partida no encontrada
    class J: id_partida = 1
    repo_j2.obtener = AsyncMock(return_value=J())
    repo_p2.obtener = AsyncMock(return_value=None)
    from app.capa_2_logica.errores import PartidaNoEncontrada as PNE
    with pytest.raises(PNE):
        await s.reponer_del_mazo(1, 1)

    # jugador no pertenece a la partida indicada (jugador.id_partida != partida_id)
    class P: id_partida = 2
    class J2: id_partida = 2
    repo_p2.obtener = AsyncMock(return_value=P())
    repo_j2.obtener = AsyncMock(return_value=J2())
    with pytest.raises(ValueError):
        await s.reponer_del_mazo(1, 1)

    # max alcanzado
    repo_p2.obtener = AsyncMock(return_value=type("P2", (), {"id_partida": 1})())
    repo_j2.obtener = AsyncMock(return_value=type("J3", (), {"id_partida": 1})())
    repo_c2.contar_en_mano = AsyncMock(return_value=6)
    r = await s.reponer_del_mazo(1, 1)
    assert r.cartas == []
    assert r.fin_de_mazo is False
    assert r.max_alcanzado is True
    assert r.sin_cartas is False

    # sin cartas (mazo vacío) → marca Finalizada
    repo_j2.obtener = AsyncMock(return_value=type("J4", (), {"id_partida": 1})())
    repo_c2.contar_en_mano = AsyncMock(return_value=3)
    repo_c2.obtener_mazo_disponible = AsyncMock(return_value=[])
    partida = type("PP", (), {"id_partida": 1, "estado": EstadoPartida.en_juego})()
    repo_p2.obtener = AsyncMock(return_value=partida)
    repo_p2.guardar = AsyncMock()
    r2 = await s.reponer_del_mazo(1, 1)
    assert r2.sin_cartas is True
    repo_p2.guardar.assert_awaited()

    # feliz con una carta
    c = CartaModelo(id_carta=1, id_partida=1, id_jugador=None, posicion=PosicionCarta.mazo)
    repo_j2.obtener = AsyncMock(return_value=type("J5", (), {"id_partida": 1})())
    repo_c2.obtener_mazo_disponible = AsyncMock(return_value=[c])
    r3 = await s.reponer_del_mazo(1, 1)
    assert len(r3.cartas) == 1


@pytest.mark.asyncio
async def test_terminar_turno_errores():
    class RepoP:
        db = object()
        async def crear(self, partida: PartidaModelo) -> PartidaModelo: ...
        async def obtener(self, partida_id: int) -> Optional[PartidaModelo]: ...
        async def listar_en_espera(self) -> List[PartidaModelo]: ...
        async def guardar(self, partida: PartidaModelo) -> None: ...
        async def confirmar(self) -> None: ...

    class RepoJ:
        db = object()
        async def listar_por_partida(self, partida_id: int) -> List[JugadorModelo]: ...
        async def crear(self, jugador: JugadorModelo) -> JugadorModelo: ...
        async def obtener(self, jugador_id: int) -> Optional[JugadorModelo]: ...
        async def guardar_muchos(self, jugadores: List[JugadorModelo]) -> None: ...

    repo_p3 = RepoP()
    repo_j3 = RepoJ()
    s = ServicioJuego(repo_p3, jugadores=repo_j3)

    # partida no encontrada
    repo_p3.obtener = AsyncMock(return_value=None)
    with pytest.raises(PartidaNoEncontrada):
        await s.terminar_turno(1, 1)

    # partida no en juego
    class P:
        estado = EstadoPartida.en_espera
    repo_p3.obtener = AsyncMock(return_value=P())
    with pytest.raises(ValueError):
        await s.terminar_turno(1, 1)

    # jugador no encontrado
    class P2:
        estado = EstadoPartida.en_juego
        cantidad_jugadores = 2
        turno_actual = 1
    repo_p3.obtener = AsyncMock(return_value=P2())
    repo_j3.obtener = AsyncMock(return_value=None)
    with pytest.raises(ValueError):
        await s.terminar_turno(1, 2)

    # turno inválido
    class J: orden_turno = 2
    repo_j3.obtener = AsyncMock(return_value=J())
    with pytest.raises(PermissionError):
        await s.terminar_turno(1, 2)
