import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.resultados import ObtenerDraftResultado
from app.capa_0_definicion_bd.models.cartas_modelos import(
    Carta as CartaModelo,
    PosicionCarta,
    TipoCarta
)


@pytest.mark.asyncio
async def test_obtener_draft_bonito(async_client):
    class S:
        async def ver_draft(self, partida_id: int, jugador_id: int): ...
    mock_service = S()
    setattr(mock_service, "ver_draft",
        AsyncMock(return_value=ObtenerDraftResultado(
            draft=[
                CartaModelo(id_carta=1, id_partida=1, posicion=PosicionCarta.draft, nombre="Not so fast", tipo=TipoCarta.instant),
                CartaModelo(id_carta=2, id_partida=1, posicion=PosicionCarta.draft, nombre="Not so fast", tipo=TipoCarta.instant),
                CartaModelo(id_carta=3, id_partida=1, posicion=PosicionCarta.draft, nombre="Not so fast", tipo=TipoCarta.instant),
            ]
        )))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.get("/partida/1/draft", params={"jugador_id": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mensaje"].startswith("Esto es el draft")
    assert len(body["cartas"]) == 3
    assert all (c["posicion"] == "draft" for c in body["cartas"])

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_obtener_draft_partida_no_encontrada_bonito(async_client):
    class S:
        async def ver_draft(self, *args, **kwargs): ...
    async def raise_err(*_, **__):
        from app.capa_2_logica.errores import PartidaNoEncontrada
        raise PartidaNoEncontrada()
    mock_service = S()
    setattr(mock_service, "ver_draft", raise_err)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.get("/partida/1/draft?jugador_id=9")
    assert resp.status_code == 404
    assert "Partida no encontrada" in resp.text

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_obtener_draft_jugador_no_encontrado_bonito(async_client):
    class S:
        async def ver_draft(self, *args, **kwargs): ...
    async def raise_err(*_, **__):
        raise ValueError("jugador_no_encontrado")
    mock_service = S()
    setattr(mock_service, "ver_draft", raise_err)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.get("/partida/1/draft?jugador_id=9")
    assert resp.status_code == 404
    assert "Jugador no encontrado" in resp.text

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_obtener_draft_jugador_no_en_partida_bonito(async_client):
    class S:
        async def ver_draft(self, *args, **kwargs): ...
    async def raise_err(*_, **__):
        raise ValueError("jugador_no_en_partida")
    mock_service = S()
    setattr(mock_service, "ver_draft", raise_err)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.get("/partida/1/draft?jugador_id=9")
    assert resp.status_code == 400
    assert "El jugador no pertenece" in resp.text

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)