from pydantic import BaseModel, ConfigDict
from datetime import datetime, date
from typing import List


class Jugador(BaseModel):
    id_jugador: int
    nombre: str
    fecha_nacimiento: date | datetime
    id_avatar: int | None = None
    orden_turno: int | None = None
    model_config = ConfigDict(from_attributes=True)


class JugadorCrear(BaseModel):
    nombre: str
    fecha_nacimiento: datetime
    id_avatar: int | None = 1


class PartidaCrear(BaseModel):
    jugador_creador: str
    fecha_nac: datetime
    minimo: int
    maximo: int
    id_avatar: int | None = 1


class Partida(BaseModel):
    id_partida: int
    minimo: int
    maximo: int
    id_jugador_creador: int | None = None
    estado: str
    cantidad_jugadores: int
    turno_actual: int
    jugadores: List[Jugador] = []
    model_config = ConfigDict(from_attributes=True)
