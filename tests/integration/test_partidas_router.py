import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import PartidaNoEncontrada


@pytest.mark.asyncio
async def test_iniciar_partida_bonito_ok(async_client, monkeypatch):
    # Mock del servicio inyectado
    class MockServ:
        async def iniciar_y_preparar_partida(self, *args, **kwargs):
            ...
    mock_service = MockServ()
    mock_service.iniciar_y_preparar_partida = AsyncMock(return_value={"repartidas": {1: ["c1"]}})

    # Override de la dependencia en FastAPI
    def _dep():
        return mock_service
    fastapi_app.dependency_overrides[obtener_servicio_juego] = _dep

    # Mock de notificaciones en el propio router (capa 3)
    import app.capa_3_api.routers.partidas as rpart
    notify_mock = AsyncMock()
    broadcast_mock = AsyncMock()
    monkeypatch.setattr(rpart, "_notify_players_async", notify_mock)
    monkeypatch.setattr(rpart.administrador, "difundir_a_partida", broadcast_mock)

    resp = await async_client.patch("/partidas/77/iniciar", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"mensaje": "La partida comenzo", "estado": "En Juego"}

    # Validar que el router llamó a notificaciones mínimas
    notify_mock.assert_awaited()
    broadcast_mock.assert_awaited_with(77, {"evento": "partida_iniciada", "partida_id": 77, "estado": "En Juego"})

    # Limpiar override
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_iniciar_partida_bonito_not_found(async_client):
    class MockServ:
        async def iniciar_y_preparar_partida(self, *args, **kwargs):
            ...
    mock_service = MockServ()
    async def _raise(*args, **kwargs):
        raise PartidaNoEncontrada()
    mock_service.iniciar_y_preparar_partida = _raise

    def _dep():
        return mock_service
    fastapi_app.dependency_overrides[obtener_servicio_juego] = _dep

    resp = await async_client.patch("/partidas/999/iniciar", json={})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Partida no encontrada"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)
