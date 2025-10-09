import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import PartidaNoEncontrada, MaximoJugadoresAlcanzado


@pytest.mark.asyncio
async def test_unirse_a_partida_con_exito_bonito(async_client, monkeypatch):
    class P:
        id_partida = 4
        estado = "En espera"
        id_jugador_creador = 1
    class J:
        id_jugador = 55
        nombre = "TestJugador"
        id_avatar = 1
        orden_turno = 1

    class S:
        async def unirse_a_partida(self, *args, **kwargs): ...
        async def listar_jugadores(self, partida_id: int): ...
    mock_service = S()
    setattr(mock_service, "unirse_a_partida", AsyncMock(return_value=(P(), J())))
    setattr(mock_service, "listar_jugadores", AsyncMock(return_value=[J()]))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    import app.capa_3_api.routers.partidas as rpart
    monkeypatch.setattr(rpart.administrador, "enviar_mensaje", AsyncMock())
    monkeypatch.setattr(rpart.administrador, "difundir_a_partida", AsyncMock())

    jugador_data = {"nombre": "TestJugador", "fecha_nacimiento": "1990-01-01T00:00:00"}
    resp = await async_client.put("/partidas/4/unirse", json=jugador_data)
    assert resp.status_code == 201
    body = resp.json()
    assert body["mensaje"] == "jugador agregado"
    assert body["jugador_id"] == 55

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_unirse_a_partida_llena_bonito(async_client):
    class S:
        async def unirse_a_partida(self, *args, **kwargs): ...
    async def raise_full(*_, **__):
        raise MaximoJugadoresAlcanzado()
    mock_service = S()
    setattr(mock_service, "unirse_a_partida", raise_full)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    jugador_data = {"nombre": "JugadorExtra", "fecha_nacimiento": "1990-01-01T00:00:00"}
    resp = await async_client.put("/partidas/5/unirse", json=jugador_data)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "La partida ya tiene el máximo de jugadores"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_unirse_a_partida_no_encontrada_bonito(async_client):
    class S:
        async def unirse_a_partida(self, *args, **kwargs): ...
    async def raise_nf(*_, **__):
        raise PartidaNoEncontrada()
    mock_service = S()
    setattr(mock_service, "unirse_a_partida", raise_nf)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    jugador_data = {"nombre": "JugadorInexistente", "fecha_nacimiento": "1990-01-01T00:00:00"}
    resp = await async_client.put("/partidas/999/unirse", json=jugador_data)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Partida no encontrada"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)
