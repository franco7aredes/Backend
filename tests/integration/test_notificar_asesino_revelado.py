import pytest
from unittest.mock import AsyncMock
import app.capa_3_api.websockets.ApiWS as wsmod
from app.capa_3_api.utilidades_asyncronas import _notificar_asesino_revelado


@pytest.mark.asyncio
async def test_notificar_asesino_revelado(monkeypatch):
    monkeypatch.setattr(wsmod.administrador, "difundir_a_partida", AsyncMock())
    _notificar_asesino_revelado(1)

    # veo si se hizo la difusion
    wsmod.administrador.difundir_a_partida.assert_any_call(
        1,
        {"evento": "asesino revelado"}
        )
