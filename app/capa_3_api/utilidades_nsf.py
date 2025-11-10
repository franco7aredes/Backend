import asyncio
import time
from typing import Dict, Any
from .nsf_tipos import VentanaNSFActiva
from .websockets.ApiWS import administrador

async def gestionar_fin_ventana(
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

async def activar_ventana_nsf(
    tipo_accion: str, 
    id_jugador: int, 
    partida_id: int,
    ventanas_dict: Dict[int, VentanaNSFActiva],
    payload: Dict[str, Any]
) -> VentanaNSFActiva:

    # creamos la ventana

    ventana_id = uuid.uuid4().hex
    tiempo = await tiempo_en_ms(5.0)

    ventana = VentanaNSFActiva(
        partida_id=partida_id,
        ventana_id=ventana_id,
        actor_id=id_jugador,
        tipo_accion=tipo_accion,
        payload=payload,
        contador=0,
        tiempo_ms=tiempo,
    )
    _VENTANAS[partida_id] = ventana

    # orquestamos la tarea
    ventana.tarea = asyncio.create_task(
        gestionar_fin_ventana(ventana, _VENTANAS)
    )

    return ventana

async def refrescar_ventana_nsf(ventana: VentanaNSFActiva) -> None:

        # orquestamos la tarea
    ventana.contador += 1
    ventana.tiempo_ms = await tiempo_en_ms(5.0) # renuevo el timer

    # reprogramo la resolucion de la ventana
    if ventana.tarea and not ventana.tarea.done():
        ventana.tarea.cancel()
        try:
            await asyncio.sleep(0) # permito que se procese la cancelacion
        except Exception:
            pass

    ventana.tarea = asyncio.create_task(
        gestionar_fin_ventana(ventana, _VENTANAS)
    )


