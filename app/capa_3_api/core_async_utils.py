import asyncio
from typing import Dict, List, Any
from .websockets.ApiWS import manager
from app.capa_3_api.dtos.juego import Carta as CartaSchema


async def _notify_players_async(cartas_repartidas: Dict[int, List[Any]]):
    for jugador_id, cartas in cartas_repartidas.items():
        cartas_data = [CartaSchema.from_orm(c).dict() for c in cartas]
        mensaje = {"evento": "partida_iniciada", "data": {"mano": cartas_data}}
        await manager.send_message(mensaje, jugador_id)
