import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.resultados import ReponerResultado, AsesinoResultado
from app.capa_0_definicion_bd.models.cartas_modelos import Carta as CartaModelo, PosicionCarta, TipoCarta
from app.capa_2_logica.errores import PartidaNoEncontrada


@pytest.mark.asyncio
async def test_reponer_del_draft(async_client, monkeypatch):
    class S:
        async def reponer_del_draft(self, *args, **kwargs): ...
        async def obtener_cantidad_cartas_en_mazo(self, partida_id): ...
    class J:
        cantidad = 10

    mock_service = S()
    setattr(mock_service, "reponer_del_draft", AsyncMock(return_value=ReponerResultado(
        cartas=[
            CartaModelo(id_carta=5, id_partida=10, id_jugador=99, posicion=PosicionCarta.mano, nombre="Carta X", tipo=TipoCarta.detective),
        ],
        fin_de_mazo=False,
        max_alcanzado=False,
        sin_cartas=False,
    )))
    setattr(mock_service, "obtener_cantidad_cartas_en_mazo", AsyncMock(return_value=J()))

    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    import app.capa_3_api.routers.mazo as rmazo
    monkeypatch.setattr(rmazo.administrador, "enviar_texto", AsyncMock())
    monkeypatch.setattr(rmazo.administrador, "enviar_mensaje", AsyncMock())
    monkeypatch.setattr(rmazo.administrador, "difundir_a_partida", AsyncMock())

    resp = await async_client.put("/partida/10/reponer_draft?carta_id=5", json={"jugador_id": 99})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mensaje"].startswith("Se repusieron 1 cartas")
    assert len(body["cartas"]) == 1
    assert body["cartas"][0]["posicion"] == "mano"

    assert rmazo.administrador.difundir_a_partida.await_count >= 1
    args = rmazo.administrador.difundir_a_partida.await_args[0][1]
    assert args["evento"] == "mazo_restante"
    assert args["mazo_restante"] == 10

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_reponer_draft_maximo_cartas(async_client):
    class S:
        async def reponer_del_draft(self, *args, **kwargs): ...
    mock_service = S()
    setattr(mock_service, "reponer_del_draft", AsyncMock(return_value=ReponerResultado(
        cartas=[],
        fin_de_mazo=False,
        max_alcanzado=True,
        sin_cartas=False,
    )))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.put("/partida/10/reponer_draft?carta_id=7", json={"jugador_id": 99})
    assert resp.status_code == 200
    assert resp.json()["mensaje"] == "El jugador ya tiene el maximo de cartas en la mano"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_reponer_draft_sin_cartas(async_client, monkeypatch):
    class S:
        async def reponer_del_draft(self, *args, **kwargs): ...
    mock_service = S()
    setattr(mock_service, "reponer_del_draft", AsyncMock(return_value=ReponerResultado(
        cartas=[],
        fin_de_mazo=False,
        max_alcanzado=False,
        sin_cartas=True,
    )))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    import app.capa_3_api.routers.mazo as rmazo
    monkeypatch.setattr(rmazo.administrador, "enviar_texto", AsyncMock())
    monkeypatch.setattr(rmazo.administrador, "enviar_mensaje", AsyncMock())
    monkeypatch.setattr(rmazo.administrador, "difundir_a_partida", AsyncMock())

    resp = await async_client.put("/partida/10/reponer_draft?carta_id=123", json={"jugador_id": 99})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No hay cartas disponibles en el draft"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_fin_de_mazo_al_reponer_draft(async_client, monkeypatch):
    class S:
        async def reponer_del_draft(self, *args, **kwargs): ...
        async def obtener_asesino(self, partida_id): ...
    mock_service = S()
    setattr(mock_service, "reponer_del_draft", AsyncMock(return_value=ReponerResultado(
        cartas=[CartaModelo(id_carta=9, id_partida=10, id_jugador=99, posicion=PosicionCarta.mano, nombre="C9", tipo=TipoCarta.detective)],
        fin_de_mazo=True,
        max_alcanzado=False,
        sin_cartas=False,
    )))
    setattr(mock_service, "obtener_asesino", AsyncMock(return_value=AsesinoResultado(asesino=5)))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    import app.capa_3_api.routers.mazo as rmazo
    send_text = AsyncMock()
    send_message = AsyncMock()
    broadcast = AsyncMock()
    monkeypatch.setattr(rmazo.administrador, "enviar_texto", send_text)
    monkeypatch.setattr(rmazo.administrador, "enviar_mensaje", send_message)
    monkeypatch.setattr(rmazo.administrador, "difundir_a_partida", broadcast)

    resp = await async_client.put("/partida/10/reponer_draft?carta_id=9", json={"jugador_id": 99})
    assert resp.status_code == 200
    _ = resp.json()
    assert send_text.await_count >= 1
    assert send_message.await_count >= 1
    assert broadcast.await_count >= 1

    args = broadcast.await_args[0][1]
    assert args["evento"] == "fin_de_mazo"
    assert args["asesino_id"] == 5

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_reponer_draft_jugador_inexistente(async_client):
    class S:
        async def reponer_del_draft(self, *args, **kwargs): ...
    async def raise_err(*_, **__):
        raise ValueError("jugador_no_encontrado")
    mock_service = S()
    setattr(mock_service, "reponer_del_draft", raise_err)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.put("/partida/10/reponer_draft?carta_id=5", json={"jugador_id": 9999})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Jugador no encontrado"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_reponer_draft_partida_inexistente(async_client):
    class S:
        async def reponer_del_draft(self, *args, **kwargs): ...
    async def raise_nf(*_, **__):
        raise PartidaNoEncontrada()
    mock_service = S()
    setattr(mock_service, "reponer_del_draft", raise_nf)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.put("/partida/9999/reponer_draft?carta_id=1", json={"jugador_id": 88})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Partida no encontrada"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)