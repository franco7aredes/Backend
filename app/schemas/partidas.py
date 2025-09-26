from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List

class Jugador(BaseModel):
    id_jugador: int
    nombre: str
    fecha_nacimiento: datetime
    model_config = ConfigDict(from_attributes=True)

class JugadorCreate(BaseModel):
    nombre: str
    fecha_nacimiento: datetime

class PartidaCreada(BaseModel):
    jugador_creador: str
    fecha_nac: datetime
    minimo: int
    maximo: int

class Partida(BaseModel):
    id_partida: int
    minimo: int
    maximo: int
    estado: str
    cantidad_jugadores: int
    turno_actual: int
    jugadores: List[Jugador] = []
    model_config = ConfigDict(from_attributes=True)
