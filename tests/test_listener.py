import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import object_session
from app.db.models.partidas_models import Partida, EstadoPartida
from app.db.models.cartas_models import PosicionCarta, Carta
from app.db.models.jugadores_models import Jugador
from app.core.async_utils import _dispatch_async_notification

from app.db.models.partidas_models import repartir_cartas

@pytest.fixture
def mock_session():
    session = MagicMock()
    return session

@pytest.mark.asyncio
@patch('app.db.models.partidas_models._dispatch_async_notification') # Aislamos la funcion q nos interesa
@patch('app.db.models.partidas_models.repartir_cartas_a_jugadores')
@patch('app.db.models.partidas_models.object_session') 

def test_listener_reparte_y_notifica(mock_obj_session, mock_repartir, mock_dispatch, mock_session):
    PARTIDA_ID = 5

    mock_obj_session.return_value = mock_session

    mock_carta_repartida = MagicMock(spec=Carta, id+jugador=1, posicion=PosicionCarta.mano)
    mock_carta_mazo = MagicMock(spec=Carta, id+jugador=None, posicion=PosicionCarta.mazo)

    mock_repartir.return_value = {
        "repartidas": {1:[mock_carta_repartida]},
        "mazo": [mock_carta_mazo]
    }

    # Creo un objeto partida (el target)
    partida_target = Partida(id_partida=PARTIDA_ID, estado=EstadoPartida.en_espera.value)

    # 1. Ejecutar el listener simulando el cambio de estado
    repartir_cartas(partida_target, EstadoPartida.en_juego.value, EstadoPartida.en_espera.value, None)

    # 2. Verificaciones de Persistencia
    mock_session.add_all.assert_called_once()

    mock_session.commit.assert_called_once()

    # 3. Verificacion de notificacion
    mock_dispatch.assert_called_once()

    # Verificar que los datos enviados son las cartas repartidas
    # Debe ser llamado con el diccionario de repartidas
    llamada_dispatch = mock_dispatch.call_args[0][0]
    assert len(llamada_dispatch) == 1
    assert llamada_dispatch[1][0] == mock_carta_repartida

def test_listener_maneja_fallo_commit(mock_obj_session, mock_repartir, mock_dispatch, mock_session):
    
    mock_session.commit.side_effect = Exception("Error de db simulado")
    mock_obj_session.return_value = mock_session
    mock_repartir.return_value = {"repartidas": {1:[MagicMock()]}, "mazo": []}

    partida_target = Partida(id_partida=5, estado=EstadoPartida.en_espera.value)

    repartir_cartas(partida_target, EstadoPartida.en_juego.value, EstadoPartida.en_espera.value, None)

    # Verificacion de Rollback
    mock_session.rollback,.assert_called_once()

    # Verificacion de que no se llamo la notificacion
    mock_dispatch.assert_not_called()
