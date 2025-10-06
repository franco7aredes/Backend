# Aca defino modelos que use en el juego

from pydantic import BaseModel, ConfigDict
from typing import Optional
from app.capa_0_definicion_bd.models.cartas_models import PosicionCarta


class Carta(BaseModel):
    id_carta: int
    id_partida: int
    id_jugador: Optional[int] = None # Valor por defecto None
    posicion: PosicionCarta
    # Pydantic v2 config (Para evitar los warnings)
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
    )
