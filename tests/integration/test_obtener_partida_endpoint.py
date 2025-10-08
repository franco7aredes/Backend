import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego


@pytest.mark.asyncio
async def test_obtener_partida_existente_bonito(async_client):
    class P:
        id_partida = 123
        minimo = 2
        maximo = 4
        id_jugador_creador = 7
        estado = "En espera"
        cantidad_jugadores = 1
        turno_actual = 1

    class S:
        async def obtener_por_id(self, partida_id: int): ...
    mock_service = S()
    setattr(mock_service, "obtener_por_id", AsyncMock(return_value=P()))

    def _dep():
        return mock_service
    fastapi_app.dependency_overrides[obtener_servicio_juego] = _dep

    response = await async_client.get("/partidas/123")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "id_partida": 123,
        "minimo": 2,
        "maximo": 4,
        "id_jugador_creador": 7,
        "estado": "En espera",
        "cantidad_jugadores": 1,
        "turno_actual": 1,
        "jugadores": [],
    }

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)
