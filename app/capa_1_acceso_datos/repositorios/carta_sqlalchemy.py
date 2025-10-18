from ast import stmt
from typing import List, Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.capa_0_definicion_bd.models.cartas_modelos import Carta as CartaModelo, PosicionCarta


class RepositorioCartaSQLAlchemy:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def crear_muchas(self, cartas: List[CartaModelo]) -> None:
        # Validar integridad mínima acorde al modelo: nombre y tipo no deben ser nulos
        for c in cartas:
            if getattr(c, "nombre", None) is None or getattr(c, "tipo", None) is None:
                raise ValueError("Carta invalida: 'nombre' y 'tipo' son obligatorios")
        self.db.add_all(cartas)
        await self.db.flush()

    async def guardar_muchas(self, cartas: List[CartaModelo]) -> None:
        """Inserta o actualiza muchas cartas y hace flush."""
        for c in cartas:
            if getattr(c, "nombre", None) is None or getattr(c, "tipo", None) is None:
                raise ValueError("Carta invalida: 'nombre' y 'tipo' son obligatorios")
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

    async def contar_en_mazo(self, partida_id: int) -> int:
        """Cuenta cuántas cartas quedan en el mazo de la partida."""
        stmt = (
            select(func.count())
            .select_from(CartaModelo)
            .where(
                (CartaModelo.id_partida == partida_id)
                & (CartaModelo.posicion == PosicionCarta.mazo)
                & (CartaModelo.id_jugador.is_(None))
            )
        )
        res = await self.db.execute(stmt)
        return int(res.scalar() or 0)

    async def guardar(self, carta: CartaModelo) -> None:
        if getattr(carta, "nombre", None) is None or getattr(carta, "tipo", None) is None:
            raise ValueError("Carta invalida: 'nombre' y 'tipo' son obligatorios")
        self.db.add(carta)
        await self.db.flush()

    async def obtener_draft(self, partida_id: int) -> List[CartaModelo]:
        stmt = (
            select(CartaModelo)
            .where((CartaModelo.id_partida == partida_id) & (CartaModelo.posicion == PosicionCarta.draft))
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
    
    async def obtener_cartas_en_mano(self, partida_id: int, jugador_id: int) -> list[CartaModelo]:
        """Obtiene las cartas en mano del jugador en la partida."""
        stmt = (
            select(CartaModelo)
            .where(
                (CartaModelo.id_partida == partida_id)
                & (CartaModelo.id_jugador == jugador_id)
                & (CartaModelo.posicion == PosicionCarta.mano)
            )
            .order_by(CartaModelo.id_carta.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
        
    async def obtener_carta(self, partida_id: int, jugador_id: int, carta_id: int) -> CartaModelo:
        """ obtengo una carta en particular"""
        stmt = (
            select(CartaModelo)
            .where((CartaModelo.id_partida == partida_id) & (CartaModelo.id_carta == carta_id) & (CartaModelo.id_jugador == jugador_id))
        )

        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def obtener_cantidad_descartadas(self, partida_id: int) -> int:
        """ obtengo cuantas cartas hay en el mazo de descarte """
        stmt = (
            select(func.count())
            .select_from(CartaModelo)
            .where(
                (CartaModelo.id_partida == partida_id)
                & (CartaModelo.posicion == PosicionCarta.descarte)
            )
        )
        res = await self.db.execute(stmt)
        return int(res.scalar() or 0)

    async def obtener_draft_disponible(self, partida_id: int, carta_id: int) -> List[CartaModelo]:
        stmt = (
            select(CartaModelo)
            .where(
                (CartaModelo.id_partida == partida_id)
                & (CartaModelo.posicion == PosicionCarta.draft)
                & (CartaModelo.id_jugador.is_(None))
                & (CartaModelo.id_carta == carta_id)
            )
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
    
    async def mover_primera_carta_mazo_a_draft(self, partida_id: int) -> Optional[CartaModelo]:
        """Toma la primera carta del mazo y la mueve al draft. Devuelve la carta movida o None si no hay mazo."""
        mazo = await self.obtener_mazo_disponible(partida_id, 1)
        if not mazo:
            return None
        carta = mazo[0]
        
        carta.posicion = PosicionCarta.draft
        # Ya deberia estar sin jugador, pero por las dudas
        carta.id_jugador = None
        self.db.add(carta)
        await self.db.flush()
        return carta
    
    async def obtener_primeras_de_descarte(self, partida_id: int) -> List[CartaModelo]:
        """ obtengo las ultimas cartas que fueron descartadas """
        stmt = (
            select(CartaModelo)
            .where(
                (CartaModelo.id_partida == partida_id)
                & (CartaModelo.posicion == PosicionCarta.descarte)
            )
            .order_by(desc(CartaModelo.orden_en_descarte))
            .limit(5)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
