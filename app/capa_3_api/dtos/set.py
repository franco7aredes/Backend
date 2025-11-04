from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List

class SeleccionarDestinoSolicitud(BaseModel):
    id_jugador: int
    id_seleccionado: int
    posicion_secreto: Optional[int] = Field(None, ge=1)