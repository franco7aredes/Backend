from fastapi import APIRouter, status, Depends, HTTPException

from app.capa_3_api.websockets.ApiWS import administrador
from app.capa_2_logica.servicio_juego import ServicioJuego
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import PartidaNoEncontrada
from app.capa_3_api.dtos.juego import (
    ObtenerSecretoRespuesta,
    SecretoDTO,
)
from app.capa_3_api.mapeadores import mapear_secretos_a_dto

secreto_router = APIRouter()


@secreto_router.get("/partidas/{partida_id}/secretos", response_model=ObtenerSecretoRespuesta, status_code=status.HTTP_200_OK)
async def obtener_secreto(partida_id: int, jugador_id: int, service: ServicioJuego = Depends(obtener_servicio_juego)):


    # uso el servicio
    try:
        resultado = await service.obtener_secretos_propios(partida_id, jugador_id)
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except ValueError as e:
        if str(e) == "jugador_no_encontrado":
            raise HTTPException(status_code=404, detail="Jugador no encontrado")
        if str(e) == "jugador_no_en_partida":
            raise HTTPException(status_code=400, detail="El jugador no pertenece a la partida indicada")
        raise

    secretos = resultado.secretos
    secretos_dto = mapear_secretos_a_dto(secretos)

    return ObtenerSecretoRespuesta(
        mensaje=f"Tienes {len(secretos)} secretos",
        secretos=secretos_dto,
    )

@secreto_router.get("/partidas/{partida_id}/secretos/cantidades", status_code=status.HTTP_200_OK, response_model=None)
async def obtener_cantidades_secretos(partida_id: int, service: ServicioJuego = Depends(obtener_servicio_juego)):
    """
    Devuelve solo [{id_jugador, cantidad}] y emite broadcast 'secretos_actualizados'.
    """
    try:
        res = await service.obtener_cantidad_secretos(partida_id)
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    secretos_lista = [
        {"id_jugador": jid, "cantidad": cant}
        for jid, cant in res.secretos_por_jugador.items()
    ]
    # Notificar a todos los jugadores de la partida
    try:
        await administrador.difundir_a_partida(
            partida_id,
            {"evento": "secretos_actualizados", "partida_id": partida_id, "secretos": secretos_lista},
        )
    except Exception:
        pass

    return secretos_lista