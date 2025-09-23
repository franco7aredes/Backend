# Aca defino modelos de datos para partidas
from pydantic import BaseModel
from datetime import datetime

"""
Nota: estas clases en endpoints hacen que se verifiquen solos
los tipos.
El formato de fechas es el de ISO 8601 (YYYY-MM-DDThh:mm:ss),
el preferido en la mayoria de las app web
"""
class PartidaCreada(BaseModel):
    jugador_creador: str
    fecha_nac: datetime
    minimo: int
    maximo: int
   
class Jugador(BaseModel):
    nombre: str
    fecha_nac: datetime

class Partida(BaseModel):
    # Esquema de los datos de partida que se envian a los usuarios
    ID: int
    minimo: int
    maximo: int
    cantidad: int
