import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.databases import Base
from app.db.models.jugadores_models import Jugador
from app.db.models.partidas_models import Partida, EstadoPartida
from app.db.models.cartas_models import PosicionCarta, Carta
from datetime import date
import sqlalchemy.exc


# configuracion de base de datos en memoria
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)

# sesion de prueba con DB limpia por test

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

# test

def test_insertar_jugador_y_partida(db):
    partida = Partida(
        estado=EstadoPartida.en_espera,
        id_jugador_creador=1,
        cantidad_jugadores=4,
        turno_actual=1,
        minimo=2,
        maximo=6
    )

    db.add(partida)
    db.commit()
    db.refresh(partida)

    jugador = Jugador(
        nombre="Leandro",
        fecha_nacimiento=date(1990, 5, 15),
        orden_turno=1,
        id_avatar=3,
        id_partida=partida.id_partida
    )
    db.add(jugador)
    db.commit()
    db.refresh(jugador)

    partida.id_jugador_creador = jugador.id_jugador
    db.commit()

    assert jugador.id_jugador is not None
    assert partida.id_partida is not None
    assert partida.id_jugador_creador == jugador.id_jugador
    assert jugador.nombre == "Leandro"
    assert partida.estado == EstadoPartida.en_espera



def test_partida_sin_estado(db):
    partida = Partida(
        id_jugador_creador=1,
        cantidad_jugadores=4,
        turno_actual=1,
        minimo=2,
        maximo=4
    )
    db.add(partida)
    try:
        db.commit()
        assert False, "La partida sin estado no debería haberse creado"
    except Exception:
        assert True


def test_estado_partida_valido(db):
    partida = Partida(
        estado=EstadoPartida.Finalizada,
        id_jugador_creador=1,
        cantidad_jugadores=3,
        turno_actual=1,
        minimo=2,
        maximo=4
    )
    db.add(partida)
    db.commit()
    assert partida.estado == EstadoPartida.Finalizada

def test_varios_jugadores_en_una_partida(db):
    partida = Partida(
        estado=EstadoPartida.en_juego,
        id_jugador_creador=1,
        cantidad_jugadores=3,
        turno_actual=1,
        minimo=2,
        maximo=4
    )
    db.add(partida)
    db.commit()

    jugadores = [
        Jugador(nombre="Joa", fecha_nacimiento=date(1995,1,1), orden_turno=1, id_avatar=1, id_partida=partida.id_partida),
        Jugador(nombre="Facu", fecha_nacimiento=date(2002,2,2), orden_turno=2, id_avatar=2, id_partida=partida.id_partida),
        Jugador(nombre="Gero", fecha_nacimiento=date(2004,3,3), orden_turno=3, id_avatar=3, id_partida=partida.id_partida),
    ]
    db.add_all(jugadores)
    db.commit()

    resultado = db.query(Jugador).filter_by(id_partida=partida.id_partida).all()
    assert len(resultado) == 3

def test_cartas_en_jugadores(db):
    partida = Partida(
        estado=EstadoPartida.en_juego,
        id_jugador_creador=1,
        cantidad_jugadores=3,
        turno_actual=1,
        minimo=2,
        maximo=4
    )
    db.add(partida)
    db.commit()

    jugadores = [
        Jugador(nombre="Joa", fecha_nacimiento=date(1995,1,1), orden_turno=1, id_avatar=1, id_partida=partida.id_partida),
        Jugador(nombre="Facu", fecha_nacimiento=date(2002,2,2), orden_turno=2, id_avatar=2, id_partida=partida.id_partida),
        Jugador(nombre="Gero", fecha_nacimiento=date(2004,3,3), orden_turno=3, id_avatar=3, id_partida=partida.id_partida),
    ]
    db.add_all(jugadores)
    db.commit()

    joa_id = jugadores[0].id_jugador
    facu_id = jugadores[1].id_jugador
    gero_id = jugadores[2].id_jugador
    cartas = [
       Carta(id_partida=partida.id_partida, id_jugador=joa_id, posicion=mano),
       Carta(id_partida=partida.id_partida, id_jugador=facu_id, posicion=mano),
       Carta(id_partida=partida.id_partida, id_jugador=gero_id, posicion=mano),
       Carta(id_partida=partida.id_partida, posicion=mazo),
       Carta(id_partida=partida.id_partida, posicion=descarte),
       Carta(id_partida=partida.id_partida, posicion=mazo)
    ]
    db.add_all(cartas)
    db.commit()

    mano_joa = db.query(Carta).filter_by(id_jugador=joa_id).all()
    assert len(mano_joa) == 1
    mano_facu = db.query(Carta).filter_by(id_jugador=facu_id).all()
    assert len(mano_facu) == 1
    mano_gero = db.query(Carta).filter_by(id_jugador=gero_id).all()
    assert len(mano_gero) == 1
    mazo = db.query(Carta).filter_by(posicion=mazo).all()
    assert len(mazo) == 2
    descarte= db.query(Carta).filter_by(posicion=descarte).all()
    assert len(descarte) == 1
