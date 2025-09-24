from databases import SessionLocal
from models.partidas_models import Partida, EstadoPartida
from models.jugadores_models import Jugador
from datetime import date


db = SessionLocal()

# crear una partida de ejemplo
partida = Partida(
    estado=EstadoPartida.en_espera,
    id_jugador_creador=1, 
    cantidad_jugadores=2,
    turno_actual=1,
    minimo=2,
    maximo=6
)

db.add(partida)
db.commit()
db.refresh(partida)

# crear jugadores
jugador1 = Jugador(
    nombre="Leandro",
    fecha_nacimiento=date(2002, 5, 20),
    orden_turno=1,
    id_avatar=1,
    id_partida=partida.id_partida
)

jugador2 = Jugador(
    nombre="Joaquin",
    fecha_nacimiento=date(2000, 8, 12),
    orden_turno=2,
    id_avatar=2,
    id_partida=partida.id_partida
)

db.add_all([jugador1, jugador2])
db.commit()
db.close()