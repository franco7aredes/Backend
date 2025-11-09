from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional

from app.capa_0_definicion_bd.models.cartas_modelos import Carta as CartaModelo
from app.capa_0_definicion_bd.models.partidas_modelos import Partida as PartidaModelo
from app.capa_0_definicion_bd.models.jugadores_modelos import Jugador as JugadorModelo
from app.capa_0_definicion_bd.models.secretos_modelos import SecretoDB
from app.capa_0_definicion_bd.models.sets_modelos import Set as SetModelo


@dataclass(slots=True)
class ReponerResultado:
    cartas: List[CartaModelo]
    fin_de_mazo: bool
    max_alcanzado: bool
    sin_cartas: bool


@dataclass(slots=True)
class TurnoResultado:
    turno_nuevo: int


@dataclass(slots=True)
class CrearPartidaResultado:
    partida: PartidaModelo
    jugador: JugadorModelo


@dataclass(slots=True)
class RepartirCartasResultado:
    repartidas: Dict[int, List[CartaModelo]]
    mazo: List[CartaModelo]


@dataclass(slots=True)
class IniciarYPrepararResultado:
    partida: PartidaModelo
    repartidas: Dict[int, List[CartaModelo]]
    mazo: List[CartaModelo]
    jugadores: List[JugadorModelo]
    secretos: Dict[int, List[SecretoDB]]


@dataclass(slots=True)
class DescartarResultado:
    carta: CartaModelo | None


@dataclass(slots=True)
class CantidadManoResultado:
    cantidad: int


@dataclass(slots=True)
class CantidadMazoResultado:
    cantidad: int


@dataclass(slots=True)
class UnirsePartidaResultado:
    partida: PartidaModelo
    jugador: JugadorModelo


@dataclass(slots=True)
class IniciarPartidaResultado:
    partida: PartidaModelo

@dataclass(slots=True)
class RepartirSecretosResultado:
    secretos_repartidos: Dict[int, List[SecretoDB]]

@dataclass(slots=True)
class ObtenerSecretosResultado:
    secretos: List[SecretoDB]

@dataclass(slots=True)
class ObtenerDraftResultado:
    draft: List[CartaModelo]
      
@dataclass(slots=True)      
class ObtenerCartasResultado:
    cartas: List[CartaModelo]

@dataclass(slots=True)
class VerDescarteResultado:
    descarte: List[CartaModelo]
      
@dataclass(slots=True)      
class CantidadManosResultado:
    cartas_por_jugador: Dict[int, int]

@dataclass(slots=True)
class AsesinoResultado:
    asesino: int

@dataclass(slots=True)
class CantidadSecretosResultado:
    secretos_por_jugador: Dict[int, int]

@dataclass(slots=True)
class JugarSetResultado:
    set: SetModelo

@dataclass(slots=True)
class RobarSetResultado:
    set: SetModelo

@dataclass(slots=True)
class RevelarSecretoResultado:
    secreto: SecretoDB

@dataclass(slots=True)
class OcultarSecretoResultado:
    secreto: SecretoDB

@dataclass(slots=True)
class AbandonarPartidaResultado:
    partida_id: int
    jugador_id: int
    cantidad_jugadores: int

@dataclass(slots=True)
class NotsoFastResultado:
    carta: List[CartaModelo]

@dataclass(slots=True)
class EventoResultado:
    tipo_evento: Optional[str] = None  
    cartas_descartadas: Optional[List[CartaModelo]] = None
    cartas_agregadas: Optional[List[CartaModelo]] = None
    set_robado: Optional[SetModelo] = None
    secreto_oculto: Optional[SecretoDB] = None
    mensaje: Optional[str] = None 
    fin_de_mazo: Optional[bool] = None
    carta_evento_descartada: Optional[CartaModelo] = None
    asesino_ganador: Optional[int] = None

@dataclass(slots=True)
class AplicarEfectoSetResultado:
      secreto_afectado: SecretoDB
      posicion_secreto: int


@dataclass(slots=True)
class FinPorDesgraciaResultado:
      jugador_asesino_id: Optional[int] | None

