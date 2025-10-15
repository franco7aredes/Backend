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

    async def obtener_secretos(self, partida_id: int, jugador_id: int) -> List[SecretoDB]:
        """ Obtengo los secretos del jugador """
        stmt = (
            select(SecretoDB)
            .where((SecretoDB.id_partida == partida_id) & (SecretoDB.id_jugador == jugador_id))
            )
        
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def obtener_secreto_asesino(self, partida_id: int) -> SecretoDB:
        """" Obtengo el secreto del asesino """
        stmt = (
            select(SecretoDB)
            .where((SecretoDB.id_partida == partida_id) & (SecretoDB.tipo == TipoSecreto.asesino))
            )
        res = await self.db.execute(stmt)
        return res.scalars().first()
      
    async def contar_secretos_jugador(self, partida_id: int, jugador_id: int) -> int:
        """Cuenta cuántos secretos tiene un jugador en una partida."""
        stmt = (
            select(func.count())
            .select_from(SecretoDB)
            .where(
                (SecretoDB.id_partida == partida_id)
                & (SecretoDB.id_jugador == jugador_id)
            )
        )
        res = await self.db.execute(stmt)
        return int(res.scalar() or 0)

