from fastapi import APIRouter, status, Depends, HTTPException

from app.capa_3_api.websockets.ApiWS import administrador
from app.capa_2_logica.servicio_juego import ServicioJuego
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import (
    PartidaNoEncontrada,
    JugadorNoEncontrado,
    JugadorNoEnPartida,
    SetNoEncontrado,
    SetNoEnPartida,
    NoPuedeRobarSuPropioSet,
)
from app.capa_3_api.dtos.juego import JugarSetRequest, JugarSetRespuesta
from app.capa_3_api.mapeadores import mapear_set_a_dto

set_router = APIRouter()

@set_router.post("/partidas/{partida_id}/sets", response_model=JugarSetRespuesta, status_code=status.HTTP_201_CREATED)
async def jugar_set(partida_id: int, datos: JugarSetRequest, service: ServicioJuego = Depends(obtener_servicio_juego)):
    try:
        resultado = await service.preparar_set(partida_id, datos.id_jugador, datos.cartas_id)
        set = resultado.set
        set_dto = mapear_set_a_dto(set)

    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
     # Notificar a todos los jugadores de la partida
    try:
        await administrador.difundir_a_partida(
            partida_id,
            {
                "evento": "set_jugado",
                "partida_id": partida_id,
                "id_jugador": datos.id_jugador,
                "cartas": datos.cartas_id,
                "set": set_dto.model_dump()
            }
        )
    except Exception:
        pass

    return JugarSetRespuesta(
        mensaje="Set jugado correctamente",
        set=set_dto
    )



@set_router.patch("/partida/{partida_id}/set/{set_id}/robar", response_model=JugarSetRespuesta, status_code=status.HTTP_200_OK)
async def robar_set(
    partida_id: int,
    set_id: int,
    jugador_id: int,
    service: ServicioJuego = Depends(obtener_servicio_juego)
):
    try:
        resultado = await service.robar_set(partida_id, jugador_id, set_id)
        set_dto = mapear_set_a_dto(resultado.set)
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except JugadorNoEncontrado:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    except JugadorNoEnPartida:
        raise HTTPException(status_code=400, detail="El jugador no pertenece a la partida indicada")
    except SetNoEncontrado:
        raise HTTPException(status_code=404, detail="Set no encontrado")
    except SetNoEnPartida:
        raise HTTPException(status_code=400, detail="El set no pertenece a la partida indicada")
    except NoPuedeRobarSuPropioSet:
        raise HTTPException(status_code=400, detail="No se puede robar el propio set")
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    # Notificar a todos los jugadores de la partida
    try:
        await administrador.difundir_a_partida(
            partida_id,
            {
                "evento": "set_robado",
                "partida_id": partida_id,
                "id_jugador": jugador_id,
                "set": set_dto.model_dump()
            }
        )
    except Exception:
        pass

    return JugarSetRespuesta(
        mensaje="Set robado correctamente",
        set=set_dto
    )
