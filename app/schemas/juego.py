# Aca defino modelos que use en el juego

from pydantic import Basemodel
from typing import Optional
from app.db.models.cartas_models import PosicionCarta


class Carta(BaseModel):
    id_carta: int
    id_partida: int
    id_jugador: Optional[int] = None # Valor por defecto None
    posicion: PosicionCarta

    # Configuracion para SQLAlchemy
    class Config:
        # le permite a pydantic leer los datos directamente desde un objeto ORM
        orm_mode = True

        use_enum_values = True
