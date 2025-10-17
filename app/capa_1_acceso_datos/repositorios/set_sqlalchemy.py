from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.capa_0_definicion_bd.models.sets_modelos import Set as SetModelo


class RepositorioSetsSQLAlchemy:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def crear_set(self, set: SetModelo) -> SetModelo:
        self.db.add(set)
        await self.db.flush()
        await self.db.refresh(set)
        return set