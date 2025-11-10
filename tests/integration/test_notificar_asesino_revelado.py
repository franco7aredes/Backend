import pytest
from unittest.mock import AsyncMock
import app.capa_3_api.websockets.ApiWS as wsmod
from app.capa_3_api.utilidades_asincronas import _notificar_asesino_revelado


@pytest.mark.asyncio
async def test_notificar_asesino_revelado(monkeypatch):
    mock_difundir = AsyncMock()
    monkeypatch.setattr(wsmod.administrador, "difundir_a_partida", mock_difundir)

    await _notificar_asesino_revelado(1)

    # veo si se hizo la difusion
    mock_difundir.assert_called_once_with(
        1,
        {"evento": "asesino revelado"}
        )
