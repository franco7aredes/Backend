from fastapi import APIRouter, Depends, HTTPException, status, Response

from app.capa_3_api.websockets.ApiWS import administrador
from app.capa_2_logica.servicio_juego import ServicioJuego
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_3_api.dtos.nsf import (
    ActivarNSFPedido,
    ActivarNSFRespuesta,
    JugarNSFPedido,
    JugarNSFRespuesta,
)

nsf_router = APIRouter()
