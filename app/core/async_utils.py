import asyncio
from typing import Dict, List, Any, Coroutine
from app.websockets.ApiWS import manager
from app.schemas.juego import Carta as CartaSchema

async def _notify_players_async(cartas_repartidas: Dict[int, List[Any]]):
    # Esta funcion asincrona les envia las cartas por websocket
    # a los jugadores

    for jugador_id, cartas in cartas_repartidas.items():
    # Convierto los datos de SQLAlchemyt a pydantic/dict

        cartas_data = [CartaSchema.from_orm(c).dict() for c in cartas]

        mensaje = {
            "evento" : "partida_iniciada",
            "data" : {
                "mano": cartas_data
            }
        }
    
        # Operacion asincrona
        await manager.send_message(mensaje, jugador_id)

