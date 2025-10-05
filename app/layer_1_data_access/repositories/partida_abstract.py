from abc import ABC, abstractmethod
from typing import Optional, List

from app.db.models.partidas_models import Partida as PartidaModel


class IPartidaRepository(ABC):
    @abstractmethod
    async def crear(self, partida: PartidaModel) -> PartidaModel: ...

    @abstractmethod
    async def obtener(self, partida_id: int) -> Optional[PartidaModel]: ...

    @abstractmethod
    async def listar_en_espera(self) -> List[PartidaModel]: ...

    @abstractmethod
    async def guardar(self, partida: PartidaModel) -> None: ...
