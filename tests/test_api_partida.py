
import pytest
from fastapi.testclient import TestClient
from app.main import app as fastapi_app
from app.schemas.partidas import PartidaCreada, Partida, Jugador

# Usa el cliente y la base de datos centralizados por conftest.py
@pytest.fixture
def client():
    return TestClient(fastapi_app)

def test_listar_partidas(client):
    """ testea el GET de /partidas """
    response = client.get("/partidas")
    assert response.status_code == 200

def test_crear_partida_exitoso(client):
    """ testea el POST de /partidas """
    payload = {
        "jugador_creador": "John salchichon",
        "fecha_nac":"1980-04-20",
        "minimo": 2,
        "maximo": 4
    }
    response = client.post("/partidas", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["mensaje"] == "partida creada con exito"

def test_crear_partida_error_validacion(client):
    payload = {
        "jugador_creador": "John salchichon",
        "fecha_nac":"1980-04-20",
        "minimo": "dos",
        "maximo": "cuatro"
    }
    response = client.post("/partidas", json=payload)
    assert response.status_code == 422
    # este assert busca el error en particular: el de dar un str para
    # un int
    assert response.json()['detail'][0]['type'] == 'int_parsing'
