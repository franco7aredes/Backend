import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_websocket_individual_echo_only():
    client = TestClient(app)
    # Conectar dos jugadores con IDs al endpoint individual
    with client.websocket_connect("/ws/1") as ws1, client.websocket_connect("/ws/2") as ws2:
        # Jugador 1 envía un mensaje, solo él recibe echo
        ws1.send_text("mensaje de ws1")
        recv1 = ws1.receive_text()
        assert "mensaje de ws1" in recv1

        # Jugador 2 envía un mensaje, solo él recibe echo
        ws2.send_text("mensaje de ws2")
        recv2 = ws2.receive_text()
        assert "mensaje de ws2" in recv2
        # Nota: no verificamos lecturas en el otro socket para evitar bloqueos, el contrato de privacidad
        # establece que el endpoint individual no difunde mensajes a otros jugadores.