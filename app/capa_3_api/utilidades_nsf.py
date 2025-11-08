import asyncio
import time
from typing import Dict
from .nsf_tipos import VentanaNSFActiva
from .websockets.ApiWS import administrador

async def resolver_ventana(
    ventana: VentanaNSFActiva,
    ventanas_dict: Dict[int, VentanaNSFActiva]
):

    """
    Espera el tiempo de la ventana y la resuelve si sigue siendo valida.
    Esta corutina se ejecuta como una tarea de fondo.
    """

    await asyncio.sleep(max(0, (ventana.tiempo_ms / 1000) - time.time()))

    actual = ventanas_dict.get(ventana.partida_id)
    if not actual or actual.ventana_id != ventana.ventana_id or actual.tiempo_ms != ventana.tiempo_ms:
    # la ventana ya no es valida (la cancelaron o reemplazaron)
        return

    # Determinar resultado y difundir
    resultado = "execute" if (actual.contador % 2 == 0) else "cancel"
    mensaje = {
        "evento" : "nsf_resolved",
        "partida_id" : actual.partida_id,
        "window_id" : actual.ventana_id,
        "outcome" : resultado,
        "tipo_accion" : actual.tipo_accion,
        "actor_id": actual.actor_id,
        "payload": actual.payload,
    }

    try:
        await administrador.difundir_a_partida(actual.partida_id, mensaje)
    finally:
        ventanas_dict.pop(actual.partida_id, None)
