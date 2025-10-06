from app.capa_0_definicion_bd.models.partidas_models import Partida as PartidaModel, EstadoPartida
from app.capa_0_definicion_bd.models.jugadores_models import Jugador as JugadorModel
from app.capa_0_definicion_bd.base_datos.base_datos_sincronica import SessionLocal
from datetime import date

def test_obtener_partida_existente(client):
    db = SessionLocal()

    partida = PartidaModel(
        estado=EstadoPartida.en_espera,
        id_jugador_creador=0, 
        cantidad_jugadores=1,
        turno_actual=1,
        minimo=2,
        maximo=4
    )
    db.add(partida)
    db.commit()
    db.refresh(partida)

    jugador_creador = JugadorModel(
        nombre="Gero",
        id_avatar=0,
        orden_turno=1,
        fecha_nacimiento=date(2000, 1, 1),
        id_partida=partida.id_partida
    )
    db.add(jugador_creador)
    db.commit()
    db.refresh(jugador_creador)

    partida.id_jugador_creador = jugador_creador.id_jugador
    db.commit()
    db.refresh(partida)

    response = client.get(f"/partidas/{partida.id_partida}")
    assert response.status_code == 200
    data = response.json()

    assert data["id_partida"] == partida.id_partida
    assert data["minimo"] == 2
    assert data["maximo"] == 4
    assert data["estado"] == "En espera"  
    assert data["cantidad_jugadores"] == 1
    assert data["turno_actual"] == 1
    assert data["id_jugador_creador"] == jugador_creador.id_jugador