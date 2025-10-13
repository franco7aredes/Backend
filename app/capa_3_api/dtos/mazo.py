from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from app.capa_3_api.dtos.juego import Carta as CartaDTO


class ReponerSolicitud(BaseModel):
    jugador_id: int


class ReponerRespuesta(BaseModel):
    mensaje: str
    cartas: Optional[List[CartaDTO]] = None
    mazo_restante: int
    model_config = ConfigDict(from_attributes=True)


class DescartarSolicitud(BaseModel):
    jugador_id: int
    carta_id: int


class DescartarRespuesta(BaseModel):
    mensaje: str
    carta: Optional[CartaDTO] = None


class ManoRespuesta(BaseModel):
    cantidad: int


class CartasEnManoRespuesta(BaseModel):
    cantidad: int
    cartas: List[CartaDTO]
    model_config = ConfigDict(from_attributes=True)