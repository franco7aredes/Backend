from typing import List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.cartas_models import Carta as CartaModelo, PosicionCarta
from .carta_contrato import IRepositorioCarta


class RepositorioCartaSQLAlchemy(IRepositorioCarta):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def crear_muchas(self, cartas: List[CartaModelo]) -> None:
        self.db.add_all(cartas)
        await self.db.flush()

    async def contar_en_mano(self, partida_id: int, jugador_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(CartaModelo)
            .where(
                (CartaModelo.id_partida == partida_id)
                & (CartaModelo.id_jugador == jugador_id)
                & (CartaModelo.posicion == PosicionCarta.mano)
            )
        )
        res = await self.db.execute(stmt)
        return int(res.scalar() or 0)

    async def obtener_mazo_disponible(self, partida_id: int, limite: int) -> List[CartaModelo]:
        stmt = (
            select(CartaModelo)
            .where(
                (CartaModelo.id_partida == partida_id)
                & (CartaModelo.posicion == PosicionCarta.mazo)
                & (CartaModelo.id_jugador.is_(None))
            )
            .limit(limite)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
