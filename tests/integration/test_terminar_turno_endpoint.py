import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import PartidaNoEncontrada
from app.capa_2_logica.resultados import TurnoResultado


@pytest.mark.asyncio
async def test_terminar_turno_valido_bonito(async_client, monkeypatch):
    class S:
        async def terminar_turno(self, *args, **kwargs): ...
        async def listar_jugadores(self, partida_id: int): ...
    mock_service = S()
    setattr(mock_service, "terminar_turno", AsyncMock(return_value=TurnoResultado(turno_nuevo=2)))
    setattr(mock_service, "listar_jugadores", AsyncMock(return_value=[type("J", (), {"id_jugador": 1})()]))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    import app.capa_3_api.routers.partidas as rpart
    monkeypatch.setattr(rpart.administrador, "enviar_mensaje", AsyncMock())

    resp = await async_client.patch("/partidas/1/terminar_turno?id_enviada=1")
    assert resp.status_code == 200
    assert resp.json() == {"turno_nuevo": 2}

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_terminar_turno_invalido_bonito(async_client):
    class S:
        async def terminar_turno(self, *args, **kwargs): ...
    async def raise_err(*_, **__):
        raise PermissionError("turno_invalido")
    mock_service = S()
    setattr(mock_service, "terminar_turno", raise_err)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.patch("/partidas/1/terminar_turno?id_enviada=2")
    assert resp.status_code == 400

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_terminar_turno_partida_no_en_juego(async_client):
    class S:
        async def terminar_turno(self, *args, **kwargs):
            raise ValueError("partida_no_en_juego")
        async def listar_jugadores(self, partida_id: int):
            return []
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: S()
    resp = await async_client.patch("/partidas/1/terminar_turno?id_enviada=1")
    assert resp.status_code == 400
    assert "no está en juego" in resp.text
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_terminar_turno_jugador_no_encontrado(async_client):
    class S:
        async def terminar_turno(self, *args, **kwargs):
            raise ValueError("otro_error")
        async def listar_jugadores(self, partida_id: int):
            return []
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: S()
    resp = await async_client.patch("/partidas/1/terminar_turno?id_enviada=1")
    assert resp.status_code == 404
    assert "Jugador no encontrado" in resp.text
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_terminar_turno_error_interno(async_client):
    class S:
        async def terminar_turno(self, *args, **kwargs):
            raise Exception("fallo inesperado")
        async def listar_jugadores(self, partida_id: int):
            return []
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: S()
    resp = await async_client.patch("/partidas/1/terminar_turno?id_enviada=1")
    assert resp.status_code == 500
    assert "Error interno del servidor" in resp.text
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_terminar_turno_partida_no_encontrada(async_client):
    from app.capa_2_logica.errores import PartidaNoEncontrada
    class S:
        async def terminar_turno(self, *args, **kwargs):
            raise PartidaNoEncontrada()
        async def listar_jugadores(self, partida_id: int):
            return []
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: S()
    resp = await async_client.patch("/partidas/1/terminar_turno?id_enviada=1")
    assert resp.status_code == 404
    assert "Partida no encontrada" in resp.text
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)