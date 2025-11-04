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
        # Los ordenamos por id para tener un orden consistente.
        stmt = (
            select(SecretoDB)
            .where((SecretoDB.id_partida == partida_id) & (SecretoDB.id_jugador == jugador_id))
            ).order_by(SecretoDB.id_secreto)
        
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

    async def obtener_secretos_revelados(self, partida_id: int) -> List[SecretoDB]:
        """obtiene los secretos revelados de una partida"""
        stmt = (
            select(SecretoDB)
            .where((SecretoDB.id_partida == partida_id) & (SecretoDB.estado == EstadoSecreto.revelado))
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def guardar(self, secreto: SecretoDB) -> None:
        """guarda un secreto nuevo. Esta funcion tambien
        permite actualizar el secreto si lo modificaste"""
        self.db.add(secreto)
        await self.db.flush()
    
    async def obtener_secreto(self, partida_id: int, jugador_id: int, secreto_id: int) -> SecretoDB:
        stmt = (
            select(SecretoDB)
            .where((SecretoDB.id_partida == partida_id) & (SecretoDB.id_jugador == jugador_id) & (SecretoDB.id_secreto == secreto_id))
            )
        
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()