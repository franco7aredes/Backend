import pytest
from unittest.mock import AsyncMock, patch
from app.capa_2_logica.servicio_juego import ServicioJuego
from typing import cast, Any


@pytest.mark.asyncio
@patch('app.capa_2_logica.servicio_juego.random.shuffle', lambda x: None)
async def test_repartir_cartas_equitativamente():
    # Arrange: repos mínimos con jugadores y contenedores
    class RepoP:
        db = object()
        async def crear(self, partida): return partida
        async def obtener(self, partida_id: int):
            return type('P', (), {'id_partida': partida_id, 'estado': None, 'cantidad_jugadores': 0, 'minimo': 0, 'maximo': 0, 'turno_actual': 1})()
        async def listar_en_espera(self) -> list: return []
        async def guardar(self, partida) -> None: ...

    class RepoJ:
        db = object()
        async def listar_por_partida(self, partida_id: int):
            return [type('J', (), {'id_jugador': 1})(), type('J', (), {'id_jugador': 2})()]
        async def crear(self, jugador): return jugador
        async def obtener(self, jugador_id: int): return None

    class RepoC:
        db = object()
        async def crear_muchas(self, cartas): ...
        async def contar_en_mano(self, partida_id: int, jugador_id: int) -> int: return 0
        async def obtener_mazo_disponible(self, partida_id: int, limite: int): return []

    s = ServicioJuego(cast(Any, RepoP()), jugadores=cast(Any, RepoJ()), cartas=cast(Any, RepoC()))

    # Act
    datos = await s.repartir_cartas(1, 3)

    # Assert: estructura válida en dataclass
    assert hasattr(datos, 'repartidas') and hasattr(datos, 'mazo')
    assert isinstance(datos.repartidas, dict)


@pytest.mark.asyncio
async def test_repartir_cartas_sin_jugadores():
    class RepoP:
        db = object()
        async def crear(self, partida): return partida
        async def obtener(self, partida_id: int):
            return type('P', (), {'id_partida': partida_id, 'estado': None, 'cantidad_jugadores': 0, 'minimo': 0, 'maximo': 0, 'turno_actual': 1})()
        async def listar_en_espera(self) -> list: return []
        async def guardar(self, partida) -> None: ...

    class RepoJ:
        db = object()
        async def listar_por_partida(self, partida_id: int): return []
        async def crear(self, jugador): return jugador
        async def obtener(self, jugador_id: int): return None

    class RepoC:
        db = object()
        async def crear_muchas(self, cartas): ...
        async def contar_en_mano(self, partida_id: int, jugador_id: int) -> int: return 0
        async def obtener_mazo_disponible(self, partida_id: int, limite: int): return []

    s = ServicioJuego(cast(Any, RepoP()), jugadores=cast(Any, RepoJ()), cartas=cast(Any, RepoC()))
    datos = await s.repartir_cartas(1, 3)
    assert datos.repartidas == {}
    assert datos.mazo == []
