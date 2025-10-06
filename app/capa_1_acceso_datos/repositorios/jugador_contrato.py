from abc import ABC, abstractmethod
from typing import List, Optional

from app.capa_0_definicion_bd.models.jugadores_models import Jugador as JugadorModelo


class IRepositorioJugador(ABC):
    @abstractmethod
    async def listar_por_partida(self, partida_id: int) -> List[JugadorModelo]: ...

    @abstractmethod
    async def crear(self, jugador: JugadorModelo) -> JugadorModelo: ...

    @abstractmethod
    async def obtener(self, jugador_id: int) -> Optional[JugadorModelo]: ...
