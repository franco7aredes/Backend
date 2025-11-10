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
            self.asesino_id = 99  # valor por defecto para el endpoint

        async def aplicar_efectos_set(self, partida_id, jugador_id, set_id, secreto_id):
            if self.next_exception:
                exc = self.next_exception
                raise exc() if isinstance(exc, type) else exc
            class Estado:
                name = "revelado"
            class Tipo:
                name = "asesino"
            class Secreto:
                def __init__(self):
                    self.tipo = Tipo()
                    self.estado = Estado()
            class Resultado:
                def __init__(self):
                    self.secreto_afectado = Secreto()
                    self.posicion_secreto = 1
            return Resultado()

        async def obtener_asesino(self, partida_id):
            class R:
                def __init__(self, asesino):
                    self.asesino = asesino
            return R(self.asesino_id)

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
    assert data["secreto_estado"] == "revelado"
    assert data["secreto_tipo"] == "asesino"
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
    data = resp.json()
    assert resp.status_code == 200
    assert data["mensaje"] == "Efecto del set aplicado correctamente"
    assert "secreto_estado" in data
    assert "secreto_tipo" in data

@pytest.mark.asyncio
async def test_aplicar_efecto_set_entra_en_desgracia_200_y_broadcast_doble(async_client, servicio_mock_override, difundir_mock):
    # el servicio lanzará la excepción de negocio
    servicio_mock_override.next_exception = JugadorEnDesgraciaSocial()
    body = {"jugador_id": 10, "secreto_id": 7}
    resp = await async_client.post("/partidas/1/sets/5/aplicar_efecto", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mensaje"] == "Efecto del set aplicado correctamente"
    assert data["jugador_entra_en_desgracia_social"] is True
    # se emiten 2 broadcasts: entrada en desgracia + eco del efecto
    assert difundir_mock.await_count == 2

@pytest.mark.asyncio
async def test_aplicar_efecto_set_sale_de_desgracia_200_y_broadcast_doble(async_client, servicio_mock_override, difundir_mock):
    servicio_mock_override.next_exception = JugadorSaleDeDesgraciaSocial()
    body = {"jugador_id": 10, "secreto_id": 7}
    resp = await async_client.post("/partidas/1/sets/5/aplicar_efecto", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mensaje"] == "Efecto del set aplicado correctamente"
    assert data["jugador_sale_de_desgracia_social"] is True
    assert difundir_mock.await_count == 2

@pytest.mark.asyncio
async def test_aplicar_efecto_set_asesino_revelado_200_y_broadcast(async_client, servicio_mock_override, difundir_mock):
    servicio_mock_override.next_exception = AsesinoRevelado()
    body = {"jugador_id": 10, "secreto_id": 7}
    resp = await async_client.post("/partidas/1/sets/5/aplicar_efecto", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mensaje"] == "Se reveló el asesino. La partida finaliza."
    # asesino: un solo broadcast
    difundir_mock.assert_awaited_once()

@pytest.mark.asyncio
async def test_aplicar_efecto_set_broadcast_falla_en_desgracia_no_rompe(async_client, servicio_mock_override, monkeypatch):
    servicio_mock_override.next_exception = JugadorEnDesgraciaSocial()
    boom = AsyncMock(side_effect=Exception("ws ex"))
    monkeypatch.setattr(rsets.administrador, "difundir_a_partida", boom)
    body = {"jugador_id": 10, "secreto_id": 7}
    resp = await async_client.post("/partidas/1/sets/5/aplicar_efecto", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mensaje"] == "Efecto del set aplicado correctamente"

@pytest.mark.asyncio
async def test_aplicar_efecto_set_fin_por_desgracia_200_y_broadcast(async_client, servicio_mock_override, difundir_mock):
    # el servicio lanzará la excepción de fin global
    servicio_mock_override.next_exception = FinPorDesgraciaSocial()
    servicio_mock_override.asesino_id = 42
    body = {"jugador_id": 10, "secreto_id": 7}

    resp = await async_client.post("/partidas/1/sets/5/aplicar_efecto", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mensaje"] == "La partida finaliza por desgracia social."
    assert data["asesinoId"] == 42

    # Se notifica una sola vez a la partida con el evento fin_por_desgracia_social
    difundir_mock.assert_awaited_once()
    # Validar payload mínimo del broadcast
    args, kwargs = difundir_mock.await_args
    assert args[0] == 1  # partida_id
    payload = args[1]
    assert payload["evento"] == "fin_por_desgracia_social"
    assert payload["asesinoId"] == 42

@pytest.mark.asyncio
async def test_aplicar_efecto_set_fin_por_desgracia_broadcast_falla_no_rompe(async_client, servicio_mock_override, monkeypatch):
    servicio_mock_override.next_exception = FinPorDesgraciaSocial()
    servicio_mock_override.asesino_id = 7
    boom = AsyncMock(side_effect=Exception("ws ex"))
    # forzamos fallo del broadcast del fin por desgracia social
    monkeypatch.setattr(rsets.administrador, "difundir_a_partida", boom)

    body = {"jugador_id": 10, "secreto_id": 7}
    resp = await async_client.post("/partidas/1/sets/5/aplicar_efecto", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mensaje"] == "La partida finaliza por desgracia social."
    assert data["asesinoId"] == 7