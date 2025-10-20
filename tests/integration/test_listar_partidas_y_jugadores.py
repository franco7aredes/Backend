import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from tests.mocks.repos_mocks import *
from datetime import date


@pytest.mark.asyncio
async def test_listar_partidas_bonito(async_client):
    # Mock del servicio para devolver solo las partidas en espera
    class P:
        def __init__(self, id_partida, minimo, maximo, id_creador, cant, turno, estado="En espera"):
            self.id_partida = id_partida
            self.minimo = minimo
            self.maximo = maximo
            self.id_jugador_creador = id_creador
            self.cantidad_jugadores = cant
            self.turno_actual = turno
            self.estado = estado

    class S:
        async def listar_en_espera(self): ...
    mock_service = S()
    # usar setattr para evitar quejas del type checker
    setattr(mock_service, "listar_en_espera", AsyncMock(return_value=[
        P(1, 2, 4, 10, 1, 1),
        P(2, 4, 6, 11, 1, 1),
    ]))

    def _dep():
        return mock_service
    fastapi_app.dependency_overrides[obtener_servicio_juego] = _dep

    resp = await async_client.get("/partidas")
    assert resp.status_code == 200
    partidas = resp.json()
    assert isinstance(partidas, list)
    assert len(partidas) == 2
    assert partidas[0]["minimo"] == 2
    assert partidas[0]["maximo"] == 4
    assert partidas[0]["estado"] == "En espera"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_listar_partidas_metodo_invalido(async_client):
    resp = await async_client.post("/partidas", json={})
    assert resp.status_code in (405, 422)


@pytest.mark.asyncio
async def test_listar_partidas_parametros_invalidos(async_client):
    resp = await async_client.get("/partidas", params={"minimo": "dos", "maximo": "cuatro"})
    assert resp.status_code in (200, 422)

@pytest.mark.asyncio
async def test_listar_partidas_error_interno(async_client):
    class S:
        async def listar_en_espera(self):
            raise Exception("fallo inesperado")
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: S()
    resp = await async_client.get("/partidas")
    assert resp.status_code == 500
    assert "Error interno del servidor" in resp.text
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_listar_jugadores_partida_no_encontrada(async_client):
    class S:
        async def obtener_por_id(self, partida_id: int): return None
        async def listar_jugadores(self, partida_id: int): return []
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: S()
    resp = await async_client.get("/partidas/999/jugadores")
    assert resp.status_code == 404
    assert "Partida no encontrada" in resp.text
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_listar_jugadores_partida_error_interno(async_client):
    class S:
        async def obtener_por_id(self, partida_id: int): raise Exception("fallo inesperado")
        async def listar_jugadores(self, partida_id: int): return []
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: S()
    resp = await async_client.get("/partidas/999/jugadores")
    assert resp.status_code == 500
    assert "Error interno del servidor" in resp.text
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_listar_jugadores_partida(async_client):

    partida_mock = crear_partida_en_espera(id_partida=1)
    jugador1 = crear_jugador(id_jugador=1, nombre="Ana", orden_turno=1, fecha_nacimiento=date(2000, 1, 1))
    jugador2 = crear_jugador(id_jugador=2, nombre="Beto", orden_turno=2, fecha_nacimiento=date(1999, 5, 5))

    class ServicioMock:
        async def obtener_por_id(self, partida_id: int): return partida_mock
        async def listar_jugadores(self, partida_id: int): return [jugador1, jugador2]

    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: ServicioMock()
    resp = await async_client.get("/partidas/1/jugadores")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["id_jugador"] == 1
    assert data[0]["nombre"] == "Ana"
    assert data[0]["fecha_nacimiento"] == "2000-01-01"
    assert data[1]["id_jugador"] == 2
    assert data[1]["nombre"] == "Beto"
    assert data[1]["fecha_nacimiento"] == "1999-05-05"
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)