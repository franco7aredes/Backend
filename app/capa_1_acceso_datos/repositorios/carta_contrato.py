from abc import ABC, abstractmethod
from typing import List

from app.capa_0_definicion_bd.models.cartas_models import Carta as CartaModelo


class IRepositorioCarta(ABC):
    @abstractmethod
    async def crear_muchas(self, cartas: List[CartaModelo]) -> None: ...

    @abstractmethod
    async def contar_en_mano(self, partida_id: int, jugador_id: int) -> int: ...

    @abstractmethod
    async def obtener_mazo_disponible(self, partida_id: int, limite: int) -> List[CartaModelo]: ...
