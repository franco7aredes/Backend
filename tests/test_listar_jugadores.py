# tests/test_api_ws.py
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida
from app.db.models.jugadores_models import Jugador as JugadorModel
from app.db.databases import SessionLocal

def test_unirse_a_partida_ws_broadcast(client: TestClient):
    # crear la partida
    with SessionLocal() as session:
        partida = PartidaModel(
            id_partida=10,
            estado=EstadoPartida.en_espera,
            cantidad_jugadores=0,
            maximo=4,
            minimo=2,
            id_jugador_creador=1,
            turno_actual=1
        )
        session.add(partida)
        session.commit()
        session.refresh(partida)

    jugador1 = {"nombre": "Pepito", "fecha_nacimiento": "2001-01-10T00:00:00"}
    jugador2 = {"nombre": "Juancito", "fecha_nacimiento": "2003-01-01T00:00:00"}

    # mockear manager.send_message
    with patch("app.routers.partidas.manager.send_message", new_callable=AsyncMock) as mock_send:
        response1 = client.put("/partidas/10/unirse", json=jugador1)
        response2 = client.put("/partidas/10/unirse", json=jugador2)



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