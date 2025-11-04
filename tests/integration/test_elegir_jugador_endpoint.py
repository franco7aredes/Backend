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

        async def verificar_seleccionar_jugador_set(self, partida_id, jugador_id, set_id, id_seleccionado, posicion_secreto):
            if self.next_exception:
                exc = self.next_exception
                raise exc() if isinstance(exc, type) else exc
            return None

    inst = ServicioMock()
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: inst
    yield inst
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.fixture
def difundir_mock(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(rsets.administrador, "difundir_a_partida", mock)
    return mock

@pytest.fixture
def enviar_mensaje_mock(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(rsets.administrador, "enviar_mensaje", mock)
    return mock

@pytest.mark.asyncio
async def test_elegir_jugador_ok_200_y_broadcast(async_client, servicio_mock_override, difundir_mock, enviar_mensaje_mock):
    body = {
        "id_jugador": 10,
        "id_seleccionado": 20,
        "posicion_secreto": 2
    }
    resp = await async_client.post("/partidas/1/sets/elegir_jugador?set_id=5", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mensaje"] == "Destino seleccionado correctamente"
    assert data["set_id"] == 5
    assert data["jugador_id"] == 10
    assert data["id_seleccionado"] == 20
    assert data["secreto_posicion"] == 2
    difundir_mock.assert_awaited_once()
    enviar_mensaje_mock.assert_awaited_once()

@pytest.mark.parametrize(
    "exc, status_code, texto",
    [
        (PartidaNoEncontrada, 404, "Partida no encontrada"),
        (JugadorNoEncontrado, 404, "Jugador no encontrado"),
        (JugadorNoEnPartida, 400, "El jugador no pertenece a la partida indicada"),
        (SetNoEncontrado, 404, "Set no encontrado"),
        (SetNoEnPartida, 400, "El set no pertenece a la partida indicada"),
        (NoPuedeRobarSuPropioSet, 400, "No puede seleccionar su propio set"),
        (SetNoCorrespondeAlJugadorSeleccionado, 400, "El set no corresponde al jugador seleccionado"),
        (SecretoNoEncontrado, 400, "El jugador seleccionado no tiene un secreto en la posición indicada"),
    ],
)
@pytest.mark.asyncio
async def test_elegir_jugador_errores(async_client, servicio_mock_override, difundir_mock, enviar_mensaje_mock, exc, status_code, texto):
    servicio_mock_override.next_exception = exc
    body = {
        "id_jugador": 10,
        "id_seleccionado": 20,
        "posicion_secreto": 1
    }
    resp = await async_client.post("/partidas/1/sets/elegir_jugador?set_id=5", json=body)
    assert resp.status_code == status_code
    assert texto in resp.text
    difundir_mock.assert_not_awaited()
    enviar_mensaje_mock.assert_not_awaited()

@pytest.mark.asyncio
async def test_elegir_jugador_falla_notificacion_no_rompe(async_client, servicio_mock_override, monkeypatch, enviar_mensaje_mock):
    boom = AsyncMock(side_effect=Exception("ws ex"))
    monkeypatch.setattr(rsets.administrador, "difundir_a_partida", boom)
    body = {
        "id_jugador": 10,
        "id_seleccionado": 20,
        "posicion_secreto": 1
    }
    resp = await async_client.post("/partidas/1/sets/elegir_jugador?set_id=5", json=body)
    assert resp.status_code == 200