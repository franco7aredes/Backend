from pydantic import BaseModel, ConfigDict
from typing import Optional, List

from app.capa_0_definicion_bd.models.cartas_modelos import PosicionCarta
from app.capa_0_definicion_bd.models.secretos_modelos import EstadoSecreto, TipoSecreto

from app.capa_0_definicion_bd.models.cartas_modelos import PosicionCarta, TipoCarta


class Carta(BaseModel):
    id_carta: int
    id_partida: int
    id_jugador: Optional[int] = None
    posicion: PosicionCarta
    nombre: str
    tipo: TipoCarta
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        # Esto me va a permitir ignorar campos ocultos, que solo maneja el back
        extra="ignore",
    )


class SecretoDTO(BaseModel):
    id_secreto: int
    id_partida: int
    id_jugador: int
    tipo: TipoSecreto
    estado: EstadoSecreto
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
    )


class ObtenerSecretoRespuesta(BaseModel):
    mensaje: str
    secretos: List[SecretoDTO]
    model_config = ConfigDict(from_attributes=True)

class JugarSetRequest(BaseModel):
    id_jugador: int
    cartas_id: List[int]

    model_config = ConfigDict(
        from_attributes=True
    )

class SetDTO(BaseModel):
    id_set: int
    id_partida: int
    id_jugador: int
    nombre: str

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
    )

class JugarSetRespuesta(BaseModel):
    mensaje: str
    set: SetDTO

    model_config = ConfigDict(from_attributes=True)