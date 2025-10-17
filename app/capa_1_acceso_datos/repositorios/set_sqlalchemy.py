from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.capa_0_definicion_bd.models.cartas_modelos import Carta as CartaModelo
from app.capa_0_definicion_bd.models.sets_modelos import Set as SetModelo


class RepositorioSetsSQLAlchemy:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def crear_set(self, set: SetModelo) -> SetModelo:
        self.db.add(set)
        await self.db.flush()
        await self.db.refresh(set)
        return set
    
    async def obtener_set_por_id(self, set_id: int) -> Optional[SetModelo]:
        stmt = select(SetModelo).where(SetModelo.id_set == set_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
    
    async def guardar_set(self, set: SetModelo) -> None:
        self.db.add(set)
        await self.db.flush()

    async def obtener_cartas_del_set(self, set_id: int) -> List[CartaModelo]:
        stmt = (
            select(SetModelo)
            .where(SetModelo.id_set == set_id)
            .options(selectinload(SetModelo.cartas))
        )
        res = await self.db.execute(stmt)
        set_obj = res.scalar_one_or_none()
        if set_obj:
            return set_obj.cartas
        return []