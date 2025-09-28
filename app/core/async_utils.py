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

# Esta funcion es la que se usa para notificar a todos los usuarios, de las cartas
def  _dispatch_async_notification(cartas_repartidas: Dict[int, List[Any]]):
    # Esta funcion es llamada por un listener de SQLAlchemy.
    # Delega la tarea de notificacion a FASTApi

    try:
        loop = asyncio.get_running_loop()

        # agenda la corrutina en el event loop de forma segura
        # esto evita bloquear el hilo actual del listener
        loop.call_soon_threadsafe(
            lambda: asyncio.create_task(_notify_players_async(cartas_repartidas))
        )

    except RuntimeError:
        print("AVISO: no se encontro un evento loop activo. No se envio la noti")
        pass
