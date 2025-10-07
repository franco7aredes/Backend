import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego


@pytest.mark.asyncio
async def test_descartar_carta_bonito(async_client):
    class S:
        async def descartar_carta(self, *args, **kwargs): ...
    mock_service = S()
    setattr(mock_service, "descartar_carta", AsyncMock(return_value=1))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.patch("/partida/1/descartar", json={"jugador_id": 9})
    assert resp.status_code == 200
    data = resp.json()
    assert data["mensaje"].startswith("Carta 1 descartada por jugador")

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_descartar_carta_sin_mano_bonito(async_client):
    class S:
        async def descartar_carta(self, *args, **kwargs): ...
    mock_service = S()
    setattr(mock_service, "descartar_carta", AsyncMock(return_value=None))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.patch("/partida/1/descartar", json={"jugador_id": 9})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No se encontró carta para descartar en esta partida"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_get_mano_bonito(async_client):
    class S:
        async def obtener_cantidad_mano(self, *args, **kwargs): ...
    mock_service = S()
    setattr(mock_service, "obtener_cantidad_mano", AsyncMock(return_value=0))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.get("/partida/1/mano/9")
    assert resp.status_code == 200
    assert resp.json()["cantidad"] == 0

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)
