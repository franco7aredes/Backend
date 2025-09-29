import pytest
from fastapi.testclient import TestClient
from app.main import app as fastapi_app
from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida
from app.db.models.jugadores_models import Jugador as JugadorModel
import datetime

# Uso el cliente y la base de datos centralizados por conftest.py
@pytest.fixture
def client():
    return TestClient(fastapi_app)

def test_terminar_turno_valido(client):
    """Testea el PATCH de /partidas/{partida_id}/terminar_turno con IDs reales"""
    from app.db.databases import SessionLocal

    session = SessionLocal()
    # limpiar tablas
    session.query(JugadorModel).delete()
    session.query(PartidaModel).delete()
    session.commit()

    # Crear partida primero con creador temporal (0)
    partida1 = PartidaModel(
        estado=EstadoPartida.en_juego,
        id_jugador_creador=0,
        cantidad_jugadores=3,
        turno_actual=1,
        minimo=2,
        maximo=4
    )
    session.add(partida1)
    session.commit()
    session.refresh(partida1)

    # Crear 3 jugadores asociados a la partida
    jugador1 = JugadorModel(nombre="Jugador1", fecha_nacimiento=datetime.date(1990, 1, 1), orden_turno=1, id_avatar=1, id_partida=partida1.id_partida)
    jugador2 = JugadorModel(nombre="Jugador2", fecha_nacimiento=datetime.date(1991, 2, 2), orden_turno=3, id_avatar=5, id_partida=partida1.id_partida)
    jugador3 = JugadorModel(nombre="Jugador3", fecha_nacimiento=datetime.date(1992, 2, 2), orden_turno=2, id_avatar=3, id_partida=partida1.id_partida)
    session.add_all([jugador1, jugador2, jugador3])
    session.commit()
    session.refresh(jugador1)
    session.refresh(jugador2)
    session.refresh(jugador3)

    # Actualizar creador con un jugador real
    partida1.id_jugador_creador = jugador1.id_jugador
    session.commit()

    # Llamar al endpoint usando IDs reales
    response = client.patch(f"/partidas/{partida1.id_partida}/terminar_turno?id_enviada={jugador1.id_jugador}")
    assert response.status_code == 200

    session.refresh(partida1)
    partida_actualizada = session.query(PartidaModel).filter(PartidaModel.id_partida == partida1.id_partida).first()
    assert partida_actualizada.turno_actual == 2

def test_terminar_turno_invalido(client):
    from app.db.databases import SessionLocal

    session = SessionLocal()
    # limpiar tablas
    session.query(JugadorModel).delete()
    session.query(PartidaModel).delete()
    session.commit()

    # Crear partida y jugadores
    partida = PartidaModel(
        estado=EstadoPartida.en_juego,
        id_jugador_creador=0,
        cantidad_jugadores=2,
        turno_actual=1,
        minimo=2,
        maximo=4
    )
    session.add(partida)
    session.commit()
    session.refresh(partida)

    j1 = JugadorModel(nombre="J1", fecha_nacimiento=datetime.date(1990,1,1), orden_turno=1, id_avatar=1, id_partida=partida.id_partida)
    j2 = JugadorModel(nombre="J2", fecha_nacimiento=datetime.date(1991,1,1), orden_turno=2, id_avatar=2, id_partida=partida.id_partida)
    session.add_all([j1, j2])
    session.commit()
    session.refresh(j1)
    session.refresh(j2)

    partida.id_jugador_creador = j1.id_jugador
    session.commit()

    # Intenta terminar turno con el jugador que NO tiene el turno actual
    resp = client.patch(f"/partidas/{partida.id_partida}/terminar_turno?id_enviada={j2.id_jugador}")
    assert resp.status_code == 400
