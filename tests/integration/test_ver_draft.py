import pytest
from unittest.mock import Asyncmock

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
    fastapi_app.dependency_overrides[ver_draft] = lambda: mock_service

    resp = await async_client.get("/partida/1/draft", params={"jugador_id": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mensaje"].startswith("Esto es el draft")
    assert len(body["cartas"]) == 3
    assert all (c["posicion"] == "draft" for c in body["cartas"])

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)
