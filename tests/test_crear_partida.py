import pytest

def test_crear_partida(client):
    payload = {
        "jugador_creador": "Juan",
        "fecha_nac": "2002-04-20",
        "minimo": 2,
        "maximo": 4
    }
    response = client.post("/partidas", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "mensaje" in data
    assert data["mensaje"] == "partida creada con exito"
    assert "id_partida" in data
    assert "id_jugador_creador" in data
    assert isinstance(data["id_partida"], int)
    assert isinstance(data["id_jugador_creador"], int)

def test_crear_partida_sin_jugador(client):
    payload = {
        "fecha_nac": "2002-04-20",
        "minimo": 2,
        "maximo": 4
    }
    response = client.post("/partidas", json=payload)
    assert response.status_code == 422
    error_data = response.json()
    assert "detail" in error_data

def test_crear_partida_fecha_invalida(client):
    payload = {
        "jugador_creador": "Juan",
        "fecha_nac": "10-03-2025",
        "minimo": 2,
        "maximo": 4
    }
    response = client.post("/partidas", json=payload)
    assert response.status_code == 422
    error_data = response.json()
    assert "detail" in error_data

def test_crear_partida_error_invalidacion(client):
    payload = {
        "Nombre": 32,
        "fecha_nac": "10-03-2025",
        "minimo": "dos",
        "maximo": "cuatro"
    }
    response = client.post("/partidas", json=payload)
    assert response.status_code == 422
    error_data = response.json()
    assert "detail" in error_data


