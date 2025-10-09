import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego


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
