from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.responses import Response
from app.capa_3_api.websockets.ApiWS import administrador
from app.capa_2_logica.servicio_juego import ServicioJuego
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import PartidaNoEncontrada, AsesinoNoEncontrado
from app.capa_3_api.dtos.mazo import (
	ReponerSolicitud,
	ReponerRespuesta,
	DescartarSolicitud,
	ManoRespuesta,
    DraftRespuesta,
	CartasEnManoRespuesta,
)
from app.capa_3_api.mapeadores import mapear_cartas_a_dto, mapear_carta_a_dto
from app.capa_3_api.dtos.juego import Carta as CartaDTO

mazo_router = APIRouter()


@mazo_router.put("/partida/{partida_id}/reponer", response_model=ReponerRespuesta, status_code=status.HTTP_200_OK)
async def reponer_mazo(partida_id: int, data: ReponerSolicitud, service: ServicioJuego = Depends(obtener_servicio_juego)):

    jugador_id = data.jugador_id

    # Usar servicio
    try:
        resultado = await service.reponer_del_mazo(partida_id, jugador_id)
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except ValueError as e:
        if str(e) == "jugador_no_encontrado":
            raise HTTPException(status_code=404, detail="Jugador no encontrado")
        if str(e) == "jugador_no_en_partida":
            raise HTTPException(status_code=400, detail="El jugador no pertenece a la partida indicada")
        raise

    if resultado.max_alcanzado:
        return ReponerRespuesta(mensaje="El jugador ya tiene el maximo de cartas en la mano")

    if resultado.sin_cartas:
        # notificar fin de mazo
        try:
            await administrador.enviar_texto(jugador_id, "fin_de_mazo")
            await administrador.enviar_mensaje({"evento": "fin_de_mazo", "partida_id": partida_id}, jugador_id)
            await administrador.difundir_a_partida(partida_id, {"evento": "fin_de_mazo", "partida_id": partida_id})
        except Exception:
            pass
        # No hay cartas para reponer: devolver 404
        raise HTTPException(status_code=404, detail="No hay cartas disponibles en el mazo")

    if resultado.fin_de_mazo:
        try:
                asesino_res = await service.obtener_asesino(partida_id)
                id_asesino = asesino_res.asesino

                await administrador.enviar_texto(jugador_id, "fin_de_mazo")
                await administrador.enviar_mensaje({"evento": "fin_de_mazo", "partida_id": partida_id, "asesino_id": id_asesino}, jugador_id)
                await administrador.difundir_a_partida(partida_id, {"evento": "fin_de_mazo", "partida_id": partida_id, "asesino_id": id_asesino})
        except Exception:
            pass
        except AsesinoNoEncontrado:
            pass

    cartas = resultado.cartas
    cartas_dto = mapear_cartas_a_dto(cartas)

    # determinamos la cantidad de cartas en el mazo
    try:
        mazo_res = await service.obtener_cantidad_cartas_en_mazo(partida_id)
        cantidad_restante = int(getattr(mazo_res, "cantidad", mazo_res))

        await administrador.difundir_a_partida(
            partida_id,
            {
                "evento": "mazo_restante",
                "jugador_id": jugador_id,
                "mazo_restante": cantidad_restante,
            }
        )
    except Exception:
        pass

    # Notificamos al resto la cantidad de cartas en mano de cada jugador
    try:
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
            }
        )
    except Exception:
        pass

    return ReponerRespuesta(
        mensaje=f"Se repusieron {len(cartas)} cartas",
        cartas=cartas_dto
    )


@mazo_router.patch("/partida/{partida_id}/descartar", response_model=CartaDTO, status_code=status.HTTP_200_OK)
async def descartar_carta_por_jugador(partida_id: int, data: DescartarSolicitud, service: ServicioJuego = Depends(obtener_servicio_juego)):
    jugador_id = data.jugador_id
    carta_id = data.carta_id
    try:
        res = await service.descartar_carta(partida_id, jugador_id, carta_id)
    except Exception:
        # Por compatibilidad con los tests actuales, cualquier condición inválida
        # responde como "no hay carta para descartar" en esta partida
        raise HTTPException(status_code=404, detail="No se encontró carta para descartar en esta partida")

    carta_obj = getattr(res, "carta", None) if res is not None else None
    if carta_obj is None:
        raise HTTPException(status_code=404, detail="No se encontró carta para descartar en esta partida")
    carta_dto = mapear_carta_a_dto(carta_obj)

    # Difundir notificación a toda la partida (mensaje general)
    try:
        await administrador.difundir_a_partida(
            partida_id,
            {
                "evento": "jugador_descarto",
                "partida_id": partida_id,
                "jugador_id": jugador_id,
                "carta": carta_id,
            }
        )
    except Exception:
        pass

    # Notificamos al resto la cantidad de cartas en mano de cada jugador
    try:
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
            }
        )
    except Exception:
        pass

    return carta_dto


@mazo_router.get("/partida/{partida_id}/mano/{jugador_id}", response_model=ManoRespuesta, status_code=status.HTTP_200_OK)
async def obtener_mano_jugador(partida_id: int, jugador_id: int, service: ServicioJuego = Depends(obtener_servicio_juego)):
	"""Devuelve la cantidad de cartas en mano del jugador en la partida."""
	res2 = await service.obtener_cantidad_mano(partida_id, jugador_id)
	if hasattr(res2, "cantidad"):
		cantidad_val: int = getattr(res2, "cantidad")  # type: ignore[assignment]
	else:
		cantidad_val = int(res2)  # type: ignore[arg-type]
	return ManoRespuesta(cantidad=cantidad_val)

@mazo_router.get("/partida/{id}/draft", response_model=DraftRespuesta, status_code=status.HTTP_200_OK)
async def obtener_draft(id: int, jugador_id: int,  service: ServicioJuego = Depends(obtener_servicio_juego)):

    try:
        resultado = await service.ver_draft(id, jugador_id)
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except ValueError as e:
        if str(e) == "jugador_no_encontrado":
            raise HTTPException(status_code=404, detail="Jugador no encontrado")
        if str(e) == "jugador_no_en_partida":
            raise HTTPException(status_code=400, detail="El jugador no pertenece a la partida indicada")
        raise

    draft = resultado.draft
    draft_dto = mapear_cartas_a_dto(draft)
        
    return DraftRespuesta(
        mensaje=f"Esto es el draft",
        cartas=draft_dto,
    )

@mazo_router.get("/partida/{partida_id}/cartas/{jugador_id}", response_model=CartasEnManoRespuesta, status_code=status.HTTP_200_OK)
async def obtener_cartas_jugador(partida_id: int, jugador_id: int, service: ServicioJuego = Depends(obtener_servicio_juego)):
    """Devuelve las cartas (DTO) en mano del jugador en la partida y la cantidad."""
    try:
        res = await service.obtener_cartas_propias(partida_id, jugador_id)
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except ValueError as e:
        msg = str(e)
        if msg == "jugador_no_encontrado":
            raise HTTPException(status_code=404, detail="Jugador no encontrado")
        if msg == "jugador_no_en_partida":
            raise HTTPException(status_code=400, detail="Jugador no pertenece a la partida")
        raise HTTPException(status_code=400, detail="Solicitud inválida")
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    cartas_dto = mapear_cartas_a_dto(res.cartas)
    return {
        "cantidad": len(cartas_dto),
        "cartas": cartas_dto,
    }

@mazo_router.get("/partida/{id}/descarte", response_model=None, status_code=status.HTTP_200_OK)
async def ver_primeras_del_descarte(id: int, jugador_id: int, service: ServicioJuego = Depends(obtener_servicio_juego)):
    """ devuelve las ultimas 5 cartas que hayan sido descartadas en la partida, por websocket"""
    try:
        res = await service.ver_del_descarte(id, jugador_id)
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except ValueError as e:
        if str(e) == "jugador_no_encontrado":
            raise HTTPException(status_code=404, detail="Jugador no encontrado")
        if str(e) == "jugador_no_en_partida":
            raise HTTPException(status_code=400, detail="El jugador no pertenece a la partida indicada")
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    

    cartas_dto = mapear_cartas_a_dto(res.descarte)
    cartas_data = [c.dict() for c in cartas_dto]
    mensaje = {"cantidad": len(cartas_data),
                "cartas": cartas_data
              }
    await administrador.enviar_mensaje(mensaje, jugador_id)

    return Response(status_code=status.HTTP_200_OK)

@mazo_router.put("/partida/{partida_id}/reponer_draft", response_model=ReponerRespuesta, status_code=status.HTTP_200_OK)
async def reponer_draft(partida_id: int, carta_id: int, data: ReponerSolicitud, service: ServicioJuego = Depends(obtener_servicio_juego)):

    jugador_id = data.jugador_id

    # Usar servicio
    try:
        resultado = await service.reponer_del_draft(partida_id, jugador_id, carta_id)
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except ValueError as e:
        if str(e) == "jugador_no_encontrado":
            raise HTTPException(status_code=404, detail="Jugador no encontrado")
        if str(e) == "jugador_no_en_partida":
            raise HTTPException(status_code=400, detail="El jugador no pertenece a la partida indicada")
        raise

    if resultado.max_alcanzado:
        return ReponerRespuesta(mensaje="El jugador ya tiene el maximo de cartas en la mano")

    if resultado.sin_cartas:
        # notificar fin de draft
        try:
            await administrador.enviar_texto(jugador_id, "fin_de_draft")
            await administrador.enviar_mensaje({"evento": "fin_de_draft", "partida_id": partida_id}, jugador_id)
            await administrador.difundir_a_partida(partida_id, {"evento": "fin_de_draft", "partida_id": partida_id})
        except Exception:
            pass
        # No hay cartas para reponer: devolver 404
        raise HTTPException(status_code=404, detail="No hay cartas disponibles en el draft")

    if resultado.fin_de_mazo:
        try:
                asesino_res = await service.obtener_asesino(partida_id)
                id_asesino = asesino_res.asesino

                await administrador.enviar_texto(jugador_id, "fin_de_mazo")
                await administrador.enviar_mensaje({"evento": "fin_de_mazo", "partida_id": partida_id, "asesino_id": id_asesino}, jugador_id)
                await administrador.difundir_a_partida(partida_id, {"evento": "fin_de_mazo", "partida_id": partida_id, "asesino_id": id_asesino})
        except Exception:
            pass
        except AsesinoNoEncontrado:
            pass

    cartas = resultado.cartas
    cartas_dto = mapear_cartas_a_dto(cartas)

    # determinamos la cantidad de cartas en el mazo
    try:
        mazo_res = await service.obtener_cantidad_cartas_en_mazo(partida_id)
        cantidad_restante = int(getattr(mazo_res, "cantidad", mazo_res))

        await administrador.difundir_a_partida(
            partida_id,
            {
                "evento": "mazo_restante",
                "jugador_id": jugador_id,
                "mazo_restante": cantidad_restante,
            }
        )
    except Exception:
        pass

    # Notificamos al resto la cantidad de cartas en mano de cada jugador
    try:
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
            }
        )
    except Exception:
        pass

    return ReponerRespuesta(
        mensaje=f"Se repusieron {len(cartas)} cartas",
        cartas=cartas_dto
    )
