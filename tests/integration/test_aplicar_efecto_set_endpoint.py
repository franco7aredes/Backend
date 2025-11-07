import pytest
from unittest.mock import AsyncMock
from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import *
import app.capa_3_api.routers.sets as rsets

@pytest.fixture
def servicio_mock_override():
    class ServicioMock:
        def __init__(self):
            self.next_exception = None

        async def aplicar_efectos_set(self, partida_id, jugador_id, set_id, secreto_id):
            if self.next_exception:
                exc = self.next_exception
                raise exc() if isinstance(exc, type) else exc
            class Resultado:
                def __init__(self):
                    class Secreto:
                        def __init__(self):
                            self.tipo = None
                    self.secreto_afectado = Secreto()
                    self.posicion_secreto = 1
            return Resultado()

    inst = ServicioMock()
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: inst
    yield inst
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.fixture
def difundir_mock(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(rsets.administrador, "difundir_a_partida", mock)
    return mock

@pytest.mark.asyncio
async def test_aplicar_efecto_set_ok_200_y_broadcast(async_client, servicio_mock_override, difundir_mock):
    body = {
        "jugador_id": 10,
        "secreto_id": 7
    }
    resp = await async_client.post("/partidas/1/sets/5/aplicar_efecto", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mensaje"] == "Efecto del set aplicado correctamente"
    assert data["set_id"] == 5
    assert data["jugador_id"] == 10
    assert data["secreto_id"] == 7
    assert data["posicion_secreto"] == 1
    difundir_mock.assert_awaited_once()

@pytest.mark.parametrize(
    "exc, status_code, texto",
    [
        (PartidaNoEncontrada, 404, "Partida no encontrada"),
        (JugadorNoEncontrado, 404, "Jugador no encontrado"),
        (JugadorNoEnPartida, 400, "El jugador no pertenece a la partida indicada"),
        (SetNoEncontrado, 404, "Set no encontrado"),
        (SetNoEnPartida, 400, "El set no pertenece a la partida indicada"),
        (SecretoNoEncontrado, 404, "Secreto no encontrado"),
        (SecretoNoDisponible, 400, "El secreto no está disponible para esta acción"),
    ],
)
@pytest.mark.asyncio
async def test_aplicar_efecto_set_errores(async_client, servicio_mock_override, difundir_mock, exc, status_code, texto):
    servicio_mock_override.next_exception = exc
    body = {
        "jugador_id": 10,
        "secreto_id": 7
    }
    resp = await async_client.post("/partidas/1/sets/5/aplicar_efecto", json=body)
    assert resp.status_code == status_code
    assert texto in resp.text
    difundir_mock.assert_not_awaited()

@pytest.mark.asyncio
async def test_aplicar_efecto_set_falla_broadcast_no_rompe(async_client, servicio_mock_override, monkeypatch):
    boom = AsyncMock(side_effect=Exception("ws ex"))
    monkeypatch.setattr(rsets.administrador, "difundir_a_partida", boom)
    body = {
        "jugador_id": 10,
        "secreto_id": 7
    }
    resp = await async_client.post("/partidas/1/sets/5/aplicar_efecto", json=body)
    assert resp.status_code == 200