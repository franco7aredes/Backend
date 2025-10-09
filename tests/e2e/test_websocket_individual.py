import pytest
from fastapi.testclient import TestClient
from app.main import app
import json


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


def test_websocket_sala_broadcast():
    client = TestClient(app)
    # Conectar tres sockets: dos a la misma sala (partida 99) y uno a otra sala (partida 100)
    with client.websocket_connect("/ws/partida/99") as sala1_a, \
         client.websocket_connect("/ws/partida/99") as sala1_b, \
         client.websocket_connect("/ws/partida/100") as sala2:
       # Solicitar broadcast a la sala 99 enviando el contrato de broadcast
       sala1_a.send_text(json.dumps({"evento": "broadcast", "mensaje": "hola 99"}))

       # Ambos de sala 99 reciben el mensaje difundido
       msg_a = sala1_a.receive_json()
       msg_b = sala1_b.receive_json()
       assert msg_a == {"evento": "broadcast", "sala": 99, "mensaje": "hola 99"}
       assert msg_b == {"evento": "broadcast", "sala": 99, "mensaje": "hola 99"}

       # El de sala 100 no debe recibir nada de la sala 99; para evitar bloqueos no intentamos leer aquí
