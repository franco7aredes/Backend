from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.capa_0_definicion_bd.models.secretos_modelos import SecretoDB, EstadoSecreto, TipoSecreto

class RepositorioSecretoSQLAlchemy:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def crear_muchos(self, secretos: List[SecretoDB]) -> None:
        # Inserta o actualiza muchos secretos y hace flush
        self.db.add_all(secretos)
        await self.db.flush()
