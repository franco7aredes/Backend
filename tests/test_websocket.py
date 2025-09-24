import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_websocket_multiple_clients_broadcast():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws1, client.websocket_connect("/ws") as ws2:
        ws1.send_text("mensaje de ws1")
        data1 = ws1.receive_text()
        data2 = ws2.receive_text()
        assert "mensaje de ws1" in data1
        assert "mensaje de ws1" in data2

        ws2.send_text("mensaje de ws2")
        data1 = ws1.receive_text()
        data2 = ws2.receive_text()
        assert "mensaje de ws2" in data1
        assert "mensaje de ws2" in data2