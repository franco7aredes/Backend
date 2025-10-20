import pytest
from unittest.mock import AsyncMock, ANY

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import PartidaNoEncontrada
from app.capa_2_logica.resultados import VerDescarteResultado
from app.capa_0_definicion_bd.models.cartas_modelos import TipoCarta, PosicionCarta

from tests.mocks.repos_mocks import (
    crear_carta
)

@pytest.mark.asyncio
async def test_ver_descarte_ok_emite_mensaje(async_client, monkeypatch):
    # Mock del servicio
    class S:
        async def ver_del_descarte(self, *args, **kwargs): ...
    svc = S()

    c1 = crear_carta(id_carta=1, id_partida=7, id_jugador=None, posicion=PosicionCarta.descarte, orden_en_descarte=1)
    c1.nombre, c1.tipo = "Hercule Poirot", TipoCarta.detective

    c2 = crear_carta(id_carta=3, id_partida=7, id_jugador=None, posicion=PosicionCarta.descarte, orden_en_descarte=2)
    c2.nombre, c2.tipo = "Hercule Poirot", TipoCarta.detective

    c3 = crear_carta(id_carta=6, id_partida=7, id_jugador=None, posicion=PosicionCarta.descarte, orden_en_descarte=3)
    c3.nombre, c3.tipo = "Not so fast", TipoCarta.instant

    c4 = crear_carta(id_carta=10, id_partida=7, id_jugador=None, posicion=PosicionCarta.descarte, orden_en_descarte=4)
    c4.nombre, c4.tipo = "Not so fast", TipoCarta.instant
    
    c5 = crear_carta(id_carta=2, id_partida=7, id_jugador=None, posicion=PosicionCarta.descarte, orden_en_descarte=5)
    c5.nombre, c5.tipo = "Hercule Poirot", TipoCarta.detective

    desc = [c1, c2, c3, c4, c5] 
    setattr(svc, "ver_del_descarte", AsyncMock(return_value=VerDescarteResultado(descarte=desc)))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: svc

    # mock del administrador WS
    import app.capa_3_api.websockets.ApiWS as wsmod
    monkeypatch.setattr(wsmod.administrador, "enviar_mensaje", AsyncMock())

    resp = await async_client.get("/partida/7/descarte", params={"jugador_id": 2})
    assert resp.status_code == 200

    # La respuesta es solo el codigo, tengo que revisar el WS

    wsmod.administrador.enviar_mensaje.assert_any_call(
        {"cantidad": 5,
        "cartas":ANY
        },
        2
    )

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_ver_descarte_partida_no_encontrada(async_client):
    class S:
        async def ver_del_descarte(self, *args, **kwargs): ...
    async def raise_nf(*_, **__):
        raise PartidaNoEncontrada()

    svc = S()
    setattr(svc, "ver_del_descarte", raise_nf)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: svc

    resp = await async_client.get("partida/7/descarte", params={"jugador_id":2})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Partida no encontrada"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego,None)

@pytest.mark.asyncio
async def test_ver_primeras_del_descarte_jugador_no_encontrado_bonito(async_client):
    class S:
        async def ver_del_descarte(self, *args, **kwargs): ...
    async def raise_err(*_, **__):
        raise ValueError("jugador_no_encontrado")
    mock_service = S()
    setattr(mock_service, "ver_del_descarte", raise_err)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.get("/partida/1/descarte?jugador_id=9")
    assert resp.status_code == 404
    assert "Jugador no encontrado" in resp.text

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_ver_primeras_del_descarte_jugador_no_en_partida_bonito(async_client):
    class S:
        async def ver_del_descarte(self, *args, **kwargs): ...
    async def raise_err(*_, **__):
        raise ValueError("jugador_no_en_partida")
    mock_service = S()
    setattr(mock_service, "ver_del_descarte", raise_err)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.get("/partida/1/descarte?jugador_id=9")
    assert resp.status_code == 400
    assert "El jugador no pertenece" in resp.text

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_ver_primeras_del_descarte_error_interno_bonito(async_client):
    class S:
        async def ver_del_descarte(self, *args, **kwargs): ...
    async def raise_err(*_, **__):
        raise Exception("error interno")
    mock_service = S()
    setattr(mock_service, "ver_del_descarte", raise_err)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.get("/partida/1/descarte?jugador_id=9")
    assert resp.status_code == 500
    assert "Error interno" in resp.text

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)