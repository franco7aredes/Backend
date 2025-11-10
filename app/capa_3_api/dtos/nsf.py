from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from typing import Any, Literal, Optional, Dict

AccionNSF = Literal["jugar_set", "jugar_evento", "agregar_a_set", "jugar_nsf"]

class ActivarNSFPedido(BaseModel):
    id_jugador: int
    tipo_accion: AccionNSF
    payload: Dict[str, Any]
    cliente_ts: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class ActivarNSFRespuesta(BaseModel):
    window_id: str
    deadline_ms: int

    model_config = ConfigDict(from_attributes=True)

class JugarNSFPedido(BaseModel):
    id_jugador: int
    carta_id: int
    ventana_id: str
    cliente_ts: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class JugarNSFRespuesta(BaseModel):
    count: int
    deadline_ms: int

    model_config = ConfigDict(from_attributes=True)
