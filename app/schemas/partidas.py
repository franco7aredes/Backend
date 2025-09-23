# Aca defino modelos de datos para partidas
from pydantic import BaseModel
from datetime import datetime

Class PartidaCreada(BaseModel):
    jugador_creador: str
    fecha_nac: datetime
    minimo: int
    maximo: int
   
Class Jugador(BaseModel):
    nombre: str
    fecha_nac: datetime

Class Partida(BaseModel):
    # Esquema de los datos de partida que se envian a los usuarios
    ID: int
    minimo: int
    maximo: int
    cantidad: int
