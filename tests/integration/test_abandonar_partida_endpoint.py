import pytest
from unittest.mock import AsyncMock
from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import *
import app.capa_3_api.routers.partidas as rpart

# Fixture: ServiceMock configurable y override centralizado
@pytest.fixture
def servicio_mock_override():
    class ServicioMock:
        def __init__(self):
            self.next_exception = None
            self.next_result = None

        async def abandonar_partida(self, partida_id: int, id_jugador: int):
            if self.next_exception:
                # Acepta clase de excepción o instancia
                exc = self.next_exception
                raise exc() if isinstance(exc, type) else exc
            return self.next_result

    inst = ServicioMock()
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: inst
    yield inst
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

# Fixture: parche del broadcast
@pytest.fixture
def difundir_mock(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(rpart.administrador, "difundir_a_partida", mock)
    return mock

@pytest.mark.asyncio
async def test_abandonar_partida_ok_204_y_broadcast(async_client, servicio_mock_override, difundir_mock):
    class Resultado:
        partida_id = 1
        jugador_id = 20
        cantidad_jugadores = 2

    servicio_mock_override.next_result = Resultado()
    resp = await async_client.delete("/partidas/1/abandonar?id_jugador=20")
    assert resp.status_code == 204
    difundir_mock.assert_called_once()

@pytest.mark.parametrize(
    "exc, status_code, texto",
    [
        (CreadorNoPuedeAbandonarPartida, 400, "El creador no puede abandonar la partida"),
        (PartidaEnJuegoNoAbandonable, 400, "No se puede abandonar una partida ya comenzada"),
        (PartidaNoEncontrada, 404, "Partida no encontrada"),
        (JugadorNoEncontrado, 404, "Jugador no encontrado"),
        (JugadorNoEnPartida, 400, "El jugador no pertenece a la partida"),
    ],
)
@pytest.mark.asyncio
async def test_abandonar_partida_errores(async_client, servicio_mock_override, exc, status_code, texto):
    servicio_mock_override.next_exception = exc
    resp = await async_client.delete("/partidas/1/abandonar?id_jugador=20")
    assert resp.status_code == status_code
    assert texto in resp.text

@pytest.mark.asyncio
async def test_abandonar_partida_falla_notificacion_no_rompe(async_client, servicio_mock_override, monkeypatch):
    class Resultado:
        partida_id = 1
        jugador_id = 20
        cantidad_jugadores = 2

    servicio_mock_override.next_result = Resultado()

    boom = AsyncMock(side_effect=Exception("ws ex"))
    monkeypatch.setattr(rpart.administrador, "difundir_a_partida", boom)

    resp = await async_client.delete("/partidas/1/abandonar?id_jugador=20")
    assert resp.status_code == 204