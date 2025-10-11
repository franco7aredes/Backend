import asyncio
from typing import Dict, List, Any
from .websockets.ApiWS import administrador
from app.capa_3_api.mapeadores import mapear_cartas_a_dto


async def _notificar_jugadores_async(cartas_repartidas: Dict[int, List[Any]]):
    for jugador_id, cartas in cartas_repartidas.items():
        cartas_data = [c.dict() for c in mapear_cartas_a_dto(cartas)]
        mensaje = {"evento": "partida_iniciada", "data": {"mano": cartas_data}}
        await administrador.enviar_mensaje(mensaje, jugador_id)
