from fastapi import APIRouter, status, Depends, HTTPException

from app.capa_3_api.websockets.ApiWS import administrador
from app.capa_2_logica.servicio_juego import ServicioJuego
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_3_api.dtos.juego import (
    ObtenerSecretoSolicitud,
    ObtenerSecretoRespuesta,
    SecretoDTO,
)
from app.capa_3_api.mapeadores import mapear_secretos_a_dto

secreto_router = APIRouter()


@secreto_router.get("/partidas/{partida_id}/secretos", response_model=ObtenerSecretoRespuesta, status_code=status.HTTP_200_OK)
async def obtener_secreto(partida_id: int, data: ObtenerSecretoSolicitud, service: ServicioJuego = Depends(obtener_servicio_juego)):
