import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.resultados import DescartarResultado
from app.capa_0_definicion_bd.models.cartas_modelos import Carta as CartaModelo, PosicionCarta, TipoCarta


@pytest.mark.asyncio
async def test_descartar_carta_bonito(async_client):
    class S:
        async def descartar_carta(self, *args, **kwargs): ...
    mock_service = S()
    carta = CartaModelo(id_carta=1, id_partida=1, id_jugador=None, posicion=PosicionCarta.descarte, nombre="Carta X", tipo=TipoCarta.detective)
    setattr(mock_service, "descartar_carta", AsyncMock(return_value=DescartarResultado(carta=carta)))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    import app.capa_3_api.routers.mazo as rmazo
    setattr(rmazo.administrador, "difundir_a_partida", AsyncMock())


    resp = await async_client.patch("/partida/1/descartar", json={"jugador_id": 9, "carta_id": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id_carta"] == 1
    assert data["posicion"] == "descarte"
    assert data["tipo"] == "detective"

    # Verificar que se llamo al menos una vez
    assert rmazo.administrador.difundir_a_partida.await_count >= 1

    # Verificar lo que se envio
    args, kwargs = rmazo.administrador.difundir_a_partida.call_args
    partida_id_enviado, mensaje_enviado = args
    assert partida_id_enviado == 1
    assert mensaje_enviado == {
        "evento": "jugador_descarto",
        "partida_id": 1,
        "jugador_id": 9,
        "carta": 1,
    }

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_descartar_carta_sin_mano_bonito(async_client):
    class S:
        async def descartar_carta(self, *args, **kwargs): ...
    mock_service = S()
    setattr(mock_service, "descartar_carta", AsyncMock(return_value=None))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.patch("/partida/1/descartar", json={"jugador_id": 9, "carta_id": 1})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No se encontró carta para descartar en esta partida"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_get_mano_bonito(async_client):
    class S:
        async def obtener_cantidad_mano(self, *args, **kwargs): ...
    mock_service = S()
    setattr(mock_service, "obtener_cantidad_mano", AsyncMock(return_value=0))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.get("/partida/1/mano/9")
    assert resp.status_code == 200
    assert resp.json()["cantidad"] == 0

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)
