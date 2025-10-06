from abc import ABC, abstractmethod
from typing import Optional, List

from app.capa_0_definicion_bd.models.partidas_models import Partida as PartidaModelo


class IRepositorioPartida(ABC):
    @abstractmethod
    async def crear(self, partida: PartidaModelo) -> PartidaModelo: ...

    @abstractmethod
    async def obtener(self, partida_id: int) -> Optional[PartidaModelo]: ...

    @abstractmethod
    async def listar_en_espera(self) -> List[PartidaModelo]: ...

    @abstractmethod
    async def guardar(self, partida: PartidaModelo) -> None: ...
