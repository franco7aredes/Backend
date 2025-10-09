from pydantic import BaseModel, ConfigDict
from typing import Optional
from app.capa_0_definicion_bd.models.cartas_modelos import PosicionCarta
from app.capa_0_definicion_bd.models.secretos_modelos import EstadoSecreto, TipoSecreto


class Carta(BaseModel):
    id_carta: int
    id_partida: int
    id_jugador: Optional[int] = None
    posicion: PosicionCarta
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
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

