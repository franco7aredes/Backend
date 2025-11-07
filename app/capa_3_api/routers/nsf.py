from __future__ import annotations
import asyncio
import uuid
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status, Response

from app.capa_2_logica.servicio_juego import ServicioJuego
from app.capa_2_logica.fabrica import obtener_servicio_juego

from app.capa_3_api.websockets.ApiWS import administrador
from app.capa_3_api.dtos.nsf import (
    ActivarNSFPedido,
    ActivarNSFRespuesta,
    JugarNSFPedido,
    JugarNSFRespuesta,
)

from app.capa_3_api.nsf_tipos import VentanaNSFActiva, tiempo_en_ms
from app.capa_3_api.utilidades_nsf import resolver_ventana


nsf_router = APIRouter()


# El estado en memoria (no puedo colocarlo en otro lado)
_VENTANAS: Dict[int, VentanaNSFActiva] = {}

@nsf_router.post(
    "/partidas/{partida_id}/nsf/activar",
    response_model=ActivarNSFRespuesta,
    status_code=status.HTTP_201_CREATED,
)
async def activar_nsf(
    partida_id: int,
    datos: ActivarNSFPedido,
    service: ServicioJuego = Depends(obtener_servicio_juego),
):
    """
    Endpoint para iniciar una ventana de oportunidad de NSF.
    Gestiona la creacion de la ventana y la tarea de resolucion.
    """

    # primero valido el estado de la API
    if partida_id in _VENTANAS:
        raise HTTPException(status_code=409, detail="nsf_en_curso")
    
    # veo la logica de reglas
    es_cancelable = await service.es_accion_cancelable_en_contexto(
        partida_id=partida_id,
        tipo_accion=datos.tipo_accion,
        payload=datos.payload,
        id_jugador_accion=datos.id_jugador
    )

    if not es_cancelable:
        # ver si hace falta algo mas si no es cancelable
        return Response(status_code=204)
    
    # creamos la ventana

    ventana_id = uuid.uuid4().hex
    tiempo = tiempo_en_ms(5.0)

    ventana = VentanaNSFActiva(
        partida_id=partida_id,
        ventana_id=ventana_id,
        actor_id=datos.id_jugador,
        tipo_accion=datos.tipo_accion,
        payload=datos.payload,
        contador=0,
        tiempo_ms=tiempo,
    )
    _VENTANAS[partida_id] = ventana

    # orquestamos la tarea
    ventana.tarea = asyncio.create_task(
        resolver_ventana(ventana, _VENTANAS)
    )

    # Difundo a los jugadores
    try:
        await administrador.difundir_a_partida(
            partida_id,
            {
                "evento": "canplaynsf",
                "partida_id": partida_id,
                "window_id": ventana_id,
                "tipo_accion": datos.tipo_accion,
                "actor_id": datos.id_jugador,
                "deadline": tiempo,
            },
        )
    except Exception:
        pass  #No fallar si falla la difusion
    
    return ActivarNSFRespuesta(window_id=ventana_id, deadline_ms=tiempo)

@nsf_router.post(
    "/partidas/{partida_id}/nsf/jugar",
    response_model=JugarNSFRespuesta,
    status_code=status.HTTP_200_OK,
)
async def jugar_nsf(
    partida_id: int,
    datos: JugarNSFPedido,
    service: ServicioJuego = Depends(obtener_servicio_juego),
):
    """
    Endpoint para jugar un NSF
    Valida el estado de la ventana, delega el descarte,
    y reprograma la tarea de resolucion.
    """

    # primero, validacion de estado

    ventana = _VENTANAS.get(partida_id)
    if not ventana or ventana.ventana_id != datos.ventana_id:
        raise HTTPException(status_code=404, detail="ventana_no_encontrada")

    ahora_ms = int(time.time() * 1000)

    if ahora_ms > ventana.tiempo_ms:
        raise HTTPException(status_code=410, detail="ventana_expirada")

    # regla, el iniciador no puede cancelar
    if ventana.contador == 0 and datos.id_jugador == ventana.actor_id:
        raise HTTPException(status_code=400, detail="iniciador_no_puede_primer_nsf")

    try:
        res = await service.descartar_carta(partida_id, datos.id_jugador, datos.carta_id)
        if not getattr(res, "carta", None):
            # mejorar sobre estos errores
            raise HTTPException(status_code=404, detail="carta_no_encontrada")
    except Exception:
            raise HTTPException(status_code=404, detail="carta_no_encontrada")

    try:
        await administrador.difundir_a_partida(
            partida_id,
            {
                "evento": "jugador_descarto",
                "partida_id": partida_id,
                "jugador_id": datos.id_jugador,
                "carta": datos.carta_id,
            },
        )

        # les tengo que notificar sobre las manos
        manos_res = await service.obtener_cantidad_manos(partida_id)
        manos_list = [
            {"id_jugador": jid, "cantidad": cant}
            for jid, cant in manos_res.cartas_por_jugador.items()
        ]
        await administrador.difundir_a_partida(
            partida_id,
            {
                "evento": "manos_actualizadas",
                "partida_id": partida_id,
                "manos": manos_list,
            },
        )
    except Exception:
        pass

    # orquestamos la tarea
    ventana.contador += 1
    ventana.tiempo_ms = tiempo_en_ms(5.0) # renuevo el timer

    # reprogramo la resolucion de la ventana
    if ventana.tarea and not ventana.tarea.done():
        ventana.tarea.cancel()
        try:
            await asyncio.sleep(0) # permito que se procese la cancelacion
        except Exception:
            pass
   
    ventana.tarea = asyncio.create_task(
        resolver_ventana(ventana, _VENTANAS)
    )

    # difundo lo que acaba de pasar
    try:
        await administrador.difundir_a_partida(
            partida_id,
            {
                "evento": "nsfplayed",
                "partida_id": partida_id,
                "window_id": ventana.ventana_id,
                "jugador_id": datos.id_jugador,
                "actor_id": ventana.actor_id,
                "count": ventana.contador,
                "deadline": ventana.tiempo_ms,
            },
        )
    except Exception:
        pass

    return JugarNSFRespuesta(count=ventana.contador, deadline_ms=ventana.tiempo_ms)
        
