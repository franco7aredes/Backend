# Aca defino modelos de datos para partidas

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List

"""
Nota: estas clases en endpoints hacen que se verifiquen solos
los tipos.
El formato de fechas es el de ISO 8601 (YYYY-MM-DDThh:mm:ss),
el preferido en la mayoria de las app web
"""
class Jugador(BaseModel): # Deberiamos pasar esto a un archivo schemas/jugador.py ? 
    id_jugador: int
    nombre: str
    fecha_nacimiento: datetime
    # Falta el turno ?
    # Falta avatar ? 
    model_config = ConfigDict(from_attributes=True)

    
class JugadorCreate(BaseModel):
    nombre:str
    fecha_nacimiento:datetime
    
    
class PartidaCreada(BaseModel):
    jugador_creador: str
    fecha_nac: datetime
    minimo: int
    maximo: int

      
class Partida(BaseModel):
    # Esquema de los datos de partida que se envian a los usuarios
    id_partida: int
    minimo: int
    maximo: int
    estado: str
    cantidad_jugadores: int
    turno_actual: int
    jugadores: List[Jugador] = []
    model_config = ConfigDict(from_attributes=True)

