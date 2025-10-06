import pytest
from fastapi.testclient import TestClient
from app.capa_3_api.main import app

def test_websocket_multiple_clients_broadcast():
    client = TestClient(app)
    # Conectar dos jugadores con IDs
    with client.websocket_connect("/ws/1") as ws1, client.websocket_connect("/ws/2") as ws2:
        # Jugador 1 envía un mensaje, ambos deberían recibir el broadcast
        ws1.send_text("mensaje de ws1")
        # el emisor recibe 2 mensajes (echo + broadcast), el receptor 1 (broadcast)
        recv1_a = ws1.receive_text()
        recv1_b = ws1.receive_text()
        recv2 = ws2.receive_text()
        assert ("mensaje de ws1" in recv1_a) or ("mensaje de ws1" in recv1_b)
        assert "mensaje de ws1" in recv2

        # Jugador 2 envía un mensaje, ambos reciben
        ws2.send_text("mensaje de ws2")
        # ahora el emisor es ws2 (recibe 2 mensajes), el otro 1
        recv2_a = ws2.receive_text()
        recv2_b = ws2.receive_text()
        recv1 = ws1.receive_text()
        assert ("mensaje de ws2" in recv2_a) or ("mensaje de ws2" in recv2_b)
        assert "mensaje de ws2" in recv1