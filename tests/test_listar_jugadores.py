from unittest.mock import AsyncMock, patch
import pytest
from app.capa_0_definicion_bd.models.partidas_models import Partida as PartidaModel, EstadoPartida


@pytest.mark.asyncio
async def test_unirse_a_partida_ws_broadcast(async_client, db_async):
    # crear la partida
    partida = PartidaModel(
        estado=EstadoPartida.en_espera,
        cantidad_jugadores=0,
        maximo=4,
        minimo=2,
        id_jugador_creador=1,
        turno_actual=1,
    )
    db_async.add(partida)
    await db_async.flush()
    await db_async.refresh(partida)
    await db_async.commit()

    jugador1 = {"nombre": "Pepito", "fecha_nacimiento": "2001-01-10T00:00:00"}
    jugador2 = {"nombre": "Juancito", "fecha_nacimiento": "2003-01-01T00:00:00"}

    # mockear manager.send_message
    with patch("app.capa_3_api.routers.partidas.manager.send_message", new_callable=AsyncMock) as mock_send:
        response1 = await async_client.put(f"/partidas/{partida.id_partida}/unirse", json=jugador1)
        response2 = await async_client.put(f"/partidas/{partida.id_partida}/unirse", json=jugador2)

        # validar respuesta HTTP
        assert response1.status_code == 201
        assert response2.status_code == 201
        assert response1.json()["mensaje"] == "jugador agregado"
        assert response2.json()["mensaje"] == "jugador agregado"
        assert "jugador_id" in response1.json()
        assert "jugador_id" in response2.json()

        # verifica que send_message fue llamado al menos dos veces
        assert mock_send.await_count >= 2

        ultimo_mensaje = mock_send.call_args[0][0]  # primer argumento = mensaje
        assert ultimo_mensaje["evento"] == "jugadores_actualizados"
        assert len(ultimo_mensaje["jugadores"]) == 2
        assert {j["nombre"] for j in ultimo_mensaje["jugadores"]} == {"Pepito", "Juancito"}