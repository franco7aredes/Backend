import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import object_session
from app.db.models.partidas_models import Partida, EstadoPartida
from app.db.models.cartas_models import PosicionCarta, Carta
from app.db.models.jugadores_models import Jugador
from app.core.async_utils import _dispatch_async_notification

from app.db.models.partidas_models import repartir_cartas

class MockJugador:
    def __init__(self, id_jugador: int, id_partida: int):
        self.id_jugador = id_jugador
        self.id_partida = id_partida

    
     # Necesario para el diccionario de repartidas
    def __repr__(self):
        return f"<MockJugador id={self.id_jugador}>"

    # Necesario para que funcione el MagicMock si se usa spec=Jugador o similar
    def __eq__(self, other):
        return self.id_jugador == other.id_jugador

@pytest.fixture
def mock_session():
    session = MagicMock()
    return session

@pytest.mark.asyncio
@patch('app.db.models.partidas_models._dispatch_async_notification') # Aislamos la funcion q nos interesa
@patch('app.db.models.partidas_models.repartir_cartas_a_jugadores')
@patch('sqlalchemy.orm.session.object_session') 

def test_listener_reparte_y_notifica(mock_obj_session, mock_repartir, mock_dispatch, mock_session):
    PARTIDA_ID = 5
    NUM_JUGADORES = 5
    
    # 1. Mocks de los objetos que la DB "devolvería"
    partida_mock = MagicMock(
        spec=Partida,
        id_partida=PARTIDA_ID, 
        estado=EstadoPartida.en_espera.value, 
        cantidad_jugadores=NUM_JUGADORES, 
        minimo=2
    )
    jugadores_mock = [MockJugador(id_jugador=i, id_partida=PARTIDA_ID) for i in range(1, NUM_JUGADORES + 1)]

    # 2. Configuración del Mock de la Sesión (mock_session) para las consultas
    
    # Mock para la query de Partida (.query(Partida).filter(...).first())
    mock_partida_query_chain = MagicMock()
    mock_partida_query_chain.filter.return_value.first.return_value = partida_mock

    # Mock para la query de Jugadores (.query(Jugador).filter(...).all())
    mock_jugador_query_chain = MagicMock()
    mock_jugador_query_chain.filter.return_value.all.return_value = jugadores_mock
    
    # Usamos side_effect en mock_session.query para simular las dos llamadas secuenciales
    mock_session.query.side_effect = [
        mock_partida_query_chain,  # Primera llamada: db.query(Partida)
        mock_jugador_query_chain   # Segunda llamada: db.query(Jugador)
    ]
    
    # 3. Configuración general de Mocks
    mock_obj_session.return_value = mock_session # Pasa el chequeo if object_session is None
    
    # Configuración de retorno para repartir_cartas_a_jugadores
    mock_carta_repartida = MagicMock(spec=Carta, id_jugador=1, posicion=PosicionCarta.mano)
    mock_carta_mazo = MagicMock(spec=Carta, id_jugador=None, posicion=PosicionCarta.mazo)

    # El diccionario de repartidas debe coincidir con el número de jugadores mock
    repartidas = {j.id_jugador: [mock_carta_repartida] for j in jugadores_mock}

    mock_repartir.return_value = {
        "repartidas": repartidas,
        "mazo": [mock_carta_mazo]
    }

    # 4. Ejecutar el listener
    repartir_cartas(
        target=partida_mock, 
        value=EstadoPartida.en_juego.value, 
        oldvalue=EstadoPartida.en_espera.value, 
        initiator=None
    )

    # 5. Verificaciones
    
    # Verifica que repartir_cartas_a_jugadores fue llamado
    mock_repartir.assert_called_once_with(mock_session, PARTIDA_ID, NUM_JUGADORES)
    
    # Verificaciones de Persistencia (usan mock_session)
    mock_session.add_all.assert_called_once()
    mock_session.commit.assert_called_once()
    
    # Verificación de notificacion
    mock_dispatch.assert_called_once()

    # Verificar que los datos enviados son las cartas repartidas
    llamada_dispatch = mock_dispatch.call_args[0]
    repartidas_enviadas = llamada_dispatch[0]
    assert repartidas_enviadas == repartidas

# --- TEST 2: Manejo de Fallo de Commit ---

@pytest.mark.asyncio 
@patch('app.db.models.partidas_models._dispatch_async_notification')
@patch('app.db.models.partidas_models.repartir_cartas_a_jugadores')
@patch('sqlalchemy.orm.session.object_session')
def test_listener_maneja_fallo_commit(mock_obj_session, mock_repartir, mock_dispatch, mock_session):
    PARTIDA_ID = 5
    NUM_JUGADORES = 4
    
    # 1. Configuración de Mocks de Query (Necesaria para que la lógica corra antes del commit)
    partida_mock = MagicMock(spec=Partida, id_partida=PARTIDA_ID, estado=EstadoPartida.en_espera.value)
    jugadores_mock = [MockJugador(id_jugador=i, id_partida=PARTIDA_ID) for i in range(1, NUM_JUGADORES + 1)]
    
    mock_partida_query_chain = MagicMock()
    mock_partida_query_chain.filter.return_value.first.return_value = partida_mock
    mock_jugador_query_chain = MagicMock()
    mock_jugador_query_chain.filter.return_value.all.return_value = jugadores_mock
    
    mock_session.query.side_effect = [
        mock_partida_query_chain,
        mock_jugador_query_chain
    ]
    
    # 2. Configuración de Fallo de Commit y Mocks Generales
    mock_session.commit.side_effect = Exception("Error de db simulado")
    mock_obj_session.return_value = mock_session
    
    # Retorno de repartir_cartas_a_jugadores
    mock_repartir.return_value = {"repartidas": {1:[MagicMock()]}, "mazo": []}

    # 3. Crear el target
    partida_target = Partida(
        id_partida=PARTIDA_ID,
        estado=EstadoPartida.en_espera.value,
        cantidad_jugadores=4,
        minimo=2
    )

    # 4. Ejecutar el listener
    repartir_cartas(
        target=partida_target, 
        value=EstadoPartida.en_juego.value, 
        oldvalue=EstadoPartida.en_espera.value, 
        initiator=None
    )

    # 5. Verificaciones
    
    # Verificacion de Rollback
    mock_session.rollback.assert_called_once()

    # Verificacion de que no se llamo la notificacion
    mock_dispatch.assert_not_called()

