import pytest
from fastapi.testclient import TestClient
from app.main import app as fastapi_app
from app.schemas.partidas import PartidaCreada, Partida, Jugador
from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida
from app.db.models.jugadores_models import Jugador as JugadorModel
import datetime

# Uso el cliente y la base de datos centralizados por conftest.py
@pytest.fixture
def client():
    return TestClient(fastapi_app)

def test_terminar_turno_valido(client):
    """ testea el PATCH de /partidas/{partidas_id}/terminar_turno"""
    from app.db.databases import SessionLocal
    
    # Creo 3 jugadores con partida asignada
    jugador1 = JugadorModel(nombre="Jugador1", fecha_nacimiento=datetime.date(1990, 1, 1), orden_turno=1, id_avatar=1, id_partida=1)
    jugador2 = JugadorModel(nombre="Jugador2", fecha_nacimiento=datetime.date(1991, 2, 2), orden_turno=3, id_avatar=5, id_partida=1)

    jugador3 = JugadorModel(nombre="Jugador3", fecha_nacimiento=datetime.date(1992, 2, 2), orden_turno=2, id_avatar=3, id_partida=1)

    session = SessionLocal()
    # limpio las tablas antes de crear datos
    session.query(JugadorModel).delete()
    session.query(PartidaModel).delete()
    session.commit()

    session.add_all([jugador1, jugador2, jugador3])
    session.commit()
    session.refresh(jugador1)
    session.refresh(jugador2)
    session.refresh(jugador3)

    partida1 = PartidaModel(
        estado=EstadoPartida.en_juego,
        id_jugador_creador=jugador1.id_jugador,
        cantidad_jugadores=3,
        turno_actual=1,
        minimo=2,
        maximo=4
    )

    session.add(partida1)
    session.commit()
    session.refresh(partida1)

    # me quiero asegurar de que los ids de partidas coincidad, asi que los aseguro
    jugador1.id_partida = partida1.id_partida
    jugador2.id_partida = partida1.id_partida
    jugador3.id_partida = partida1.id_partida

    response = client.patch("/partidas/1/terminar_turno", json={"id_enviada": 1})
    assert response.status_code == 200

def test_terminar_turno_invalido(client):
    response = client.patch("/partidas/1/terminar_turno", json={"id_enviada": 5})
    assert response.status_code in (405,422,404)
