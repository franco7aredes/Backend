import pytest
from unittest.mock import AsyncMock
from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.resultados import RobarSetResultado
from app.capa_2_logica.errores import (
    PartidaNoEncontrada,
    JugadorNoEncontrado,
    JugadorNoEnPartida,
    SetNoEncontrado,
    SetNoEnPartida,
    NoPuedeRobarSuPropioSet,
)
from app.capa_0_definicion_bd.models.sets_modelos import Set as SetModelo

@pytest.mark.asyncio
async def test_robar_set_ok(async_client, monkeypatch):
    class S:
        async def robar_set(self, partida_id, jugador_id, set_id): ...
    set_obj = SetModelo(id_set=7, id_partida=10, id_jugador=99, nombre="Set robado")
    mock_service = S()
    setattr(mock_service, "robar_set", AsyncMock(return_value=RobarSetResultado(set=set_obj)))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    import app.capa_3_api.routers.sets as rsets
    monkeypatch.setattr(rsets.administrador, "difundir_a_partida", AsyncMock())

    resp = await async_client.patch("/partida/10/set/7/robar?jugador_id=99")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mensaje"].startswith("Set robado correctamente")
    assert body["set"]["id_set"] == 7
    assert body["set"]["id_jugador"] == 99

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
@pytest.mark.parametrize("exc,code,detail", [
    (PartidaNoEncontrada(), 404, "Partida no encontrada"),
    (JugadorNoEncontrado(), 404, "Jugador no encontrado"),
    (JugadorNoEnPartida(), 400, "El jugador no pertenece a la partida indicada"),
    (SetNoEncontrado(), 404, "Set no encontrado"),
    (SetNoEnPartida(), 400, "El set no pertenece a la partida indicada"),
    (NoPuedeRobarSuPropioSet(), 400, "No se puede robar el propio set"),
])
async def test_robar_set_errores(async_client, exc, code, detail):
    class S:
        async def robar_set(self, partida_id, jugador_id, set_id):
            raise exc
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: S()

    resp = await async_client.patch("/partida/10/set/7/robar?jugador_id=99")
    assert resp.status_code == code
    assert resp.json()["detail"] == detail

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)