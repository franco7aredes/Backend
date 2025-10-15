import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import PartidaNoEncontrada
from app.capa_2_logica.resultados import CantidadSecretosResultado


@pytest.mark.asyncio
async def test_secretos_cantidades_ok_emite_broadcast(async_client, monkeypatch):
    # Mock del servicio
    class S:
        async def obtener_cantidad_secretos(self, *a, **k): ...
    svc = S()
    valores = {3: 2, 7: 4}
    setattr(svc, "obtener_cantidad_secretos", AsyncMock(return_value=CantidadSecretosResultado(secretos_por_jugador=valores)))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: svc

    # Mock del administrador WS
    import app.capa_3_api.websockets.ApiWS as wsmod
    monkeypatch.setattr(wsmod.administrador, "difundir_a_partida", AsyncMock())

    resp = await async_client.get("/partidas/9/secretos/cantidades")
    assert resp.status_code == 200
    body = resp.json()

    # La respuesta es lista de {id_jugador, cantidad}
    assert isinstance(body, list)

    assert body == [{"id_jugador": 3, "cantidad": 2}, {"id_jugador": 7, "cantidad": 4}]

    wsmod.administrador.difundir_a_partida.assert_any_call(
        9,
        {
            "evento": "secretos_actualizados",
            "partida_id": 9,
            "secretos": [{"id_jugador": 3, "cantidad": 2}, {"id_jugador": 7, "cantidad": 4}],
        },
    )

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_secretos_cantidades_partida_no_encontrada(async_client):
    class S:
        async def obtener_cantidad_secretos(self, *a, **k): ...
    async def raise_nf(*_, **__):
        raise PartidaNoEncontrada()

    svc = S()
    setattr(svc, "obtener_cantidad_secretos", raise_nf)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: svc

    resp = await async_client.get("/partidas/999/secretos/cantidades")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Partida no encontrada"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)