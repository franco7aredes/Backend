from fastapi import APIRouter, status, Depends, HTTPException

from app.capa_3_api.websockets.ApiWS import administrador
from app.capa_2_logica.servicio_juego import ServicioJuego
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import PartidaNoEncontrada
from app.capa_3_api.dtos.juego import JugarSetRequest, JugarsetRespuesta
from app.capa_3_api.mapeadores import mapear_set_a_dto

set_router = APIRouter()

@set_router.post("/partidas/{partida_id}/sets", response_model=JugarsetRespuesta, status_code=status.HTTP_201_CREATED)
async def jugar_set_(partida_id: int, datos: JugarSetRequest, service: ServicioJuego = Depends(obtener_servicio_juego)):
    try:
        resultado = await service.Preparar_set(partida_id, datos.id_jugador, datos.cartas_id)
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    
    # Notificar a todos los jugadores de la partida
    try:
        await administrador.difundir_a_partida(
            partida_id,
            {"evento": "set_jugado", "partida_id": partida_id, "id_jugador": datos.id_jugador, "cartas": datos.cartas_id}
        )
    except Exception:
        pass
    
    set = resultado.set
    set_dto=mapear_set_a_dto(set)
    return JugarsetRespuesta(
        mensaje="Set jugado correctamente",
        set=set_dto
    )


