import pytest

def test_listar_partidas(client):

    from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida
    from app.db.models.jugadores_models import Jugador as JugadorModel
    from app.db.databases import SessionLocal
    import datetime

    session = SessionLocal()
    # Limpia las tablas antes de crear datos
    session.query(JugadorModel).delete()
    session.query(PartidaModel).delete()
    session.commit()

    # Crea dos jugadores creadores sin partida asignada
    jugador1 = JugadorModel(nombre="Jugador1", fecha_nacimiento=datetime.date(1990, 1, 1), orden_turno=1, id_avatar=1, id_partida=1)
    jugador2 = JugadorModel(nombre="Jugador2", fecha_nacimiento=datetime.date(1991, 2, 2), orden_turno=1, id_avatar=1, id_partida=2)
    session.add_all([jugador1, jugador2])
    session.commit()
    session.refresh(jugador1)
    session.refresh(jugador2)

    # Crea dos partidas en espera y una en juego usando los jugadores como creadores
    partida1 = PartidaModel(
        estado=EstadoPartida.en_espera,
        id_jugador_creador=jugador1.id_jugador,
        cantidad_jugadores=1,
        turno_actual=1,
        minimo=2,
        maximo=4
    )
    partida2 = PartidaModel(
        estado=EstadoPartida.en_espera,
        id_jugador_creador=jugador2.id_jugador,
        cantidad_jugadores=1,
        turno_actual=1,
        minimo=4,
        maximo=6
    )
    partida3 = PartidaModel(
        estado=EstadoPartida.en_juego,
        id_jugador_creador=jugador1.id_jugador,
        cantidad_jugadores=1,
        turno_actual=1,
        minimo=3,
        maximo=5
    )
    session.add_all([partida1, partida2, partida3])
    session.commit()
    session.refresh(partida1)
    session.refresh(partida2)
    session.refresh(partida3)

    # Actualiza el id_partida de los jugadores
    jugador1.id_partida = partida1.id_partida
    jugador2.id_partida = partida2.id_partida
    session.commit()
    session.close()

    response = client.get("/partidas")
    assert response.status_code == 200
    partidas = response.json()
    assert isinstance(partidas, list)
    assert len(partidas) == 2
    assert partidas[0]["minimo"] == 2
    assert partidas[0]["maximo"] == 4

def test_listar_partidas_metodo_invalido(client):
    response = client.post("/partidas", json={})
    assert response.status_code in (405, 422)

def test_listar_partidas_parametros_invalidos(client):
    response = client.get("/partidas", params={"minimo": "dos", "maximo": "cuatro"})
    assert response.status_code in (200, 422)