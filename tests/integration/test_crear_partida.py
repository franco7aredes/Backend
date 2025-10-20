import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.resultados import CrearPartidaResultado
import app.capa_3_api.routers.partidas as rpart

@pytest.mark.asyncio
async def test_crear_partida_bonito(async_client, monkeypatch):
    # Mock del servicio
    class P:
        id_partida = 42
        estado = "En espera"
    class J:
        id_jugador = 99

    class S:
        async def crear_partida(self, *args, **kwargs): ...
    mock_service = S()
    setattr(mock_service, "crear_partida", AsyncMock(return_value=CrearPartidaResultado(partida=P(), jugador=J())))

    # Mock de broadcast
    monkeypatch.setattr(rpart.administrador, "difundir", AsyncMock())

    def _dep():
        return mock_service
    fastapi_app.dependency_overrides[obtener_servicio_juego] = _dep

    payload = {
        "jugador_creador": "Juan",
        "fecha_nac": "2002-04-20",
        "minimo": 2,
        "maximo": 4,
    }
    resp = await async_client.post("/partidas", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["mensaje"] == "partida creada con exito"
    assert data["id_partida"] == 42
    assert data["id_jugador_creador"] == 99

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


def test_crear_partida_sin_jugador(client):
    payload = {"fecha_nac": "2002-04-20", "minimo": 2, "maximo": 4}
    response = client.post("/partidas", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_crear_partida_fecha_invalida(client):
    payload = {"jugador_creador": "Juan", "fecha_nac": "10-03-2025", "minimo": 2, "maximo": 4}
    response = client.post("/partidas", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_crear_partida_error_invalidacion(client):
    payload = {"Nombre": 32, "fecha_nac": "10-03-2025", "minimo": "dos", "maximo": "cuatro"}
    response = client.post("/partidas", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()

@pytest.mark.asyncio
async def test_crear_partida_error_interno(async_client, monkeypatch):
    # Mock del servicio que lanza excepción inesperada
    class S:
        async def crear_partida(self, *args, **kwargs):
            raise Exception("fallo inesperado")

    monkeypatch.setattr(rpart.administrador, "difundir", AsyncMock())
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: S()

    payload = {
        "jugador_creador": "Juan",
        "fecha_nac": "2002-04-20",
        "minimo": 2,
        "maximo": 4,
    }
    resp = await async_client.post("/partidas", json=payload)
    assert resp.status_code == 500
    assert "Error interno del servidor" in resp.text

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)