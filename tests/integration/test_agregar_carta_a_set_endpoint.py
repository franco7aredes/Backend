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
            self.resultado_ok = None
        async def agregar_carta_a_set_propio(self, partida_id, id_jugador, carta_id, set_id):
            if self.next_exception:
                exc = self.next_exception
                raise exc() if isinstance(exc, type) else exc
            return self.resultado_ok
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
async def test_agregar_carta_a_set_ok_200_y_broadcast(async_client, servicio_mock_override, difundir_mock):
    class DummySet:
        def __init__(self):
            self.id_set = 5
            self.id_partida = 1
            self.id_jugador = 10
            self.nombre = "Set de prueba"
    class DummyResultado:
        def __init__(self):
            self.set = DummySet()
    servicio_mock_override.resultado_ok = DummyResultado()
    body = {"id_jugador": 10, "carta_id": 7}
    resp = await async_client.patch("/partidas/1/sets/5/agregar_carta", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mensaje"] == "Carta agregada al set correctamente"
    assert data["set"]["id_set"] == 5
    assert data["set"]["id_partida"] == 1
    assert data["set"]["id_jugador"] == 10
    assert data["set"]["nombre"] == "Set de prueba"
    difundir_mock.assert_awaited_once()

@pytest.mark.parametrize(
    "exc, status_code, texto",
    [
        (PartidaNoEncontrada, 404, "Partida no encontrada"),
        (JugadorNoEncontrado, 404, "Jugador no encontrado"),
        (JugadorNoEnPartida, 400, "El jugador no pertenece a la partida indicada"),
        (SetNoEncontrado, 404, "Set no encontrado"),
        (SetNoCorrespondeAlJugadorSeleccionado, 400, "El set no corresponde al jugador seleccionado"),
        (CartaNoEncontrada, 404, "Carta no encontrada"),
        (CartaNoEnMano, 400, "no está en la mano"),
        (TipoCartaNoCompatibleConSet, 400, "solo se pueden agregar cartas de tipo detective"),
        (CartaNoCompatibleConSet, 400, "no es compatible"),
    ],
)
@pytest.mark.asyncio
async def test_agregar_carta_a_set_errores(async_client, servicio_mock_override, difundir_mock, exc, status_code, texto):
    servicio_mock_override.next_exception = exc
    body = {"id_jugador": 10, "carta_id": 7}
    resp = await async_client.patch("/partidas/1/sets/5/agregar_carta", json=body)
    assert resp.status_code == status_code
    assert texto.lower() in resp.text.lower()
    difundir_mock.assert_not_awaited()

@pytest.mark.asyncio
async def test_agregar_carta_a_set_falla_broadcast_no_rompe(async_client, servicio_mock_override, monkeypatch):
    boom = AsyncMock(side_effect=Exception("ws ex"))
    monkeypatch.setattr(rsets.administrador, "difundir_a_partida", boom)
    class DummySet:
        def __init__(self):
            self.id_set = 5
            self.id_partida = 1
            self.id_jugador = 10
            self.nombre = "Set de prueba"
    class DummyResultado:
        def __init__(self):
            self.set = DummySet()
    servicio_mock_override.resultado_ok = DummyResultado()
    body = {"id_jugador": 10, "carta_id": 7}
    resp = await async_client.patch("/partidas/1/sets/5/agregar_carta", json=body)
    assert resp.status_code == 200
