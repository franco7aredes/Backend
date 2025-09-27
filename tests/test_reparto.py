import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from app.db.models.cartas_models import PosicionCarta, Carta
from app.db.models.jugadores_models import Jugador
from app.db.models.partidas_models import Partida
from app.db.models.obtener_cartas import repartir_cartas_a_jugadores

# Voy a mockear objetos de BD
class MockCarta(object):
    def __init__(self, id_carta, id_partida, posicion, id_jugador=None):
        self.id_carta = id_carta
        self.id_partida = id_partida
        self.posicion = posicion
        self.id_jugador = id_jugador

class MockJugador(object):
    def __init__(self, id_jugador, id_partida):
        self.id_jugador = id_jugador
        self.id_partida = id_partida


@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

@patch('app.db.models.obtener_cartas.Carta', MockCarta) # Cambio mi modelo carta por el mock
@patch('app.db.models.obtener_cartas.random.shuffle') # Evito barajar para controlar mejor

def test_repartir_cartas_equitativamente(mock_shuffle, mock_db):
    PARTIDA_ID=10
    NUM_CARTAS = 6
    NUM_JUGADORES = 5

    # 1. configuro los mocks de la BD
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock() # Simulo que la partida existe

    # Simulo 5 jugadores
    jugadores_mock = [MockJugador(id_jugador=i, id_partida=PARTIDA_ID) for i in range(1, NUM_JUGADORES+1)]
    mock_db.query.return_value.filter.return_value.all.return_value = jugadores_mock

    # Ejecuto la funcion
    resultado = repartir_cartas_a_jugadores(mock_db, PARTIDA_ID, NUM_CARTAS)

    repartidas = resultado["repartidas"]
    mazo = resultado["mazo"]

    # Total de cartas
    assert len(repartidas) == NUM_JUGADORES
    assert (NUM_JUGADORES * NUM_CARTAS) + len(mazo) == 61

    # verificacion de posesion
    jugador_1_cartas = repartidas[1]
    assert jugador_1_cartas[0].id_jugador == 1
    assert jugador_1_cartas[0].posicion == PosicionCarta.mano
    
    # verificacion de que el resto esta en mazo
    assert mazo[0].id_jugador is None
    assert mazo[0].posicion == PosicionCarta.mazo

def test_repartir_cartas_sin_jugadorse(mock_db):
    PARTIDA_ID=10

    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = []

    resultado = repartir_cartas_a_jugadores(mock_db, PARTIDA_ID, 6)

    assert resultado == []
