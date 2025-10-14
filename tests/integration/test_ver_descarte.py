import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import PartidaNoEncontrada
from app.capa_2_logica.resultados import VerDescarteResultado
from app.capa_0_definicion_bd.models.cartas_modelos import TipoCarta, PosicionCarta


@pytest.mark.asyncio
async def test_ver_descarte_ok_emite_mensaje(async_client, monkeypatch):
    # Mock del servicio
    class S:
        async def ver_del_descarte(self, *args, **kwargs): ...
    svc = S()

    c1 = type ("C", (), {})()
    c1.id_carta = 1
    c1.id_partida = 7
    c1.id_jugador = None
    c1.posicion = PosicionCarta.descarte
    c1.nombre = "Hercule Poirot"
    c1.tipo = TipoCarta.detective
    c1.orden_del_descarte = 1

    c2 = type ("C", (), {})()
    c2.id_carta = 3
    c2.id_partida = 7
    c2.id_jugador = None
    c2.posicion = PosicionCarta.descarte
    c2.nombre = "Hercule Poirot"
    c2.tipo = TipoCarta.detective
    c2.orden_del_descarte = 2

    c3 = type ("C", (), {})()
    c3.id_carta = 6
    c3.id_partida = 7
    c3.id_jugador = None
    c3.posicion = PosicionCarta.descarte
    c3.nombre = "Not so fast"
    c3.tipo = TipoCarta.instant
    c3.orden_del_descarte = 3

    c4 = type ("C", (), {})()
    c4.id_carta = 10
    c4.id_partida = 7
    c4.id_jugador = None
    c4.posicion = PosicionCarta.descarte
    c4.nombre = "Not so fast"
    c4.tipo = TipoCarta.instant
    c4.orden_del_descarte = 4
    
    c5 = type ("C", (), {})()
    c5.id_carta = 2
    c5.id_partida = 7
    c5.id_jugador = None
    c5.posicion = PosicionCarta.descarte
    c5.nombre = "Hercule Poirot"
    c5.tipo = TipoCarta.detective
    c5.orden_del_descarte = 5

    desc = [c1, c2, c3, c4, c5] 
    setattr(svc, "ver_del_descarte", AsyncMock(return_value=VerDescarteResultado(descarte=desc)))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: svc

    # mock del administrador WS
    import app.capa_3_api.websockets.ApiWS as wsmod
    monkeypatch.setattr(wsmod.administrador, "enviar_mensaje", AsyncMock())

    resp = async_client.get("/partida/7/descarte", params={"jugador_id": 2})
    assert resp.status_code == 200
    body = resp.json()

    # La respuesta es solo el codigo, tengo que revisar el WS

    wsmod.administrador.enviar_mensaje.assert_any_call(
        2,
        {"cantidad": 5,
        "cartas":[c1, c2, c3, c4, c5],
        }
    )

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_ver_descarte_partida_no_encontrada(async_client):
    class S:
        async def ver_del_descarte(self, *args, **kwargs): ...
    async def raise_nf(*_, **__):
        raise PartidaNoEncontrada()

    svc = S()
    setattr=(svc, "ver_del_descarte", raise_nf)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: svc

    resp = await async_client.get("partida/7/descarte", params={"jugador_id":2})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Partida no encontrada"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego,None)
