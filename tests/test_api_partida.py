from fastapi.testclient import TestClient
from Backend.app.main import app
from Backend.app.schemas.partidas import PartidaCreada, Partida, Jugador

# Nota: ir complejizando los tests a medida que se hacen features
client = TestClient(app)

def test_listar_partidas():
    """ testea el GET de /partidas """
    response = client.get("/partidas")
    assert response.status_code == 200

def test_crear_partida_exitoso():
    """ testea el POST de /partidas """
    payload = {
        "jugador_creador": "John salchichon",
        "fecha_nac":"1980-04-20",
        "minimo": 2,
        "maximo": 4
    }
    response = client.post("/partidas", json=payload)
    # Pydantic/FASTApi devuelven 422 en caso de datos invalidos
    # y 201 en caso de bien hecho
    assert response.status_code == 201
    assert response.json() == {
        "jugador_creador": "John salchichon",
        "fecha_nac": "1980-04-20",
        "minimo": 2,
        "maximo": 4
    }

def test_crear_partida_error_validacion():
    payload = {
        "jugador_creador": "John salchichon",
        "fecha_nac":"1980-04-20",
        "minimo": "2",
        "maximo": "4"
    }
    response = client.post("/partidas", json=payload)
    assert response.status_code == 422
    assert "validation_error" in response.json()['detail'][0]['type']
