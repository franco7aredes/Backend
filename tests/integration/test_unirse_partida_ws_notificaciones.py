from unittest.mock import AsyncMock
import pytest

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego


@pytest.mark.asyncio
async def test_unirse_a_partida_ws_bonito(async_client, monkeypatch):
    class P:
        id_partida = 1
        estado = "En espera"
        id_jugador_creador = 1
    class J:
        def __init__(self, id, nombre, avatar=1, orden=1):
            self.id_jugador = id
            self.nombre = nombre
            self.id_avatar = avatar
            self.orden_turno = orden

    class S:
        async def unirse_a_partida(self, *args, **kwargs): ...
        async def listar_jugadores(self, partida_id: int): ...
    mock_service = S()
    setattr(mock_service, "unirse_a_partida", AsyncMock(side_effect=[(P(), J(10, "Pepito")), (P(), J(11, "Juancito"))]))
    setattr(mock_service, "listar_jugadores", AsyncMock(return_value=[J(10, "Pepito"), J(11, "Juancito")]))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    import app.capa_3_api.routers.partidas as rpart
    send_message = AsyncMock()
    monkeypatch.setattr(rpart.administrador, "enviar_mensaje", send_message)

    jugador1 = {"nombre": "Pepito", "fecha_nacimiento": "2001-01-10T00:00:00"}
    jugador2 = {"nombre": "Juancito", "fecha_nacimiento": "2003-01-01T00:00:00"}

    response1 = await async_client.put("/partidas/1/unirse", json=jugador1)
    response2 = await async_client.put("/partidas/1/unirse", json=jugador2)

    assert response1.status_code == 201
    assert response2.status_code == 201
    assert response1.json()["mensaje"] == "jugador agregado"
    assert response2.json()["mensaje"] == "jugador agregado"
    assert "jugador_id" in response1.json()
    assert "jugador_id" in response2.json()

    assert send_message.await_count >= 2
    ultimo_mensaje = send_message.call_args[0][0]
    assert ultimo_mensaje["evento"] == "jugadores_actualizados"
    assert len(ultimo_mensaje["jugadores"]) == 2
    assert {j["nombre"] for j in ultimo_mensaje["jugadores"]} == {"Pepito", "Juancito"}

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)
