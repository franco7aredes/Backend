from fastapi import APIRouter, status, Depends, HTTPException, Body

from app.capa_3_api.websockets.ApiWS import administrador
from app.capa_2_logica.servicio_juego import ServicioJuego
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import *
from app.capa_3_api.dtos.juego import JugarSetRequest, JugarSetRespuesta, AgregarCartaASetRequest 
from app.capa_3_api.dtos.juego import JugarSetRequest, JugarSetRespuesta, SeleccionarDestinoSolicitud, AplicarEfectoSetSolicitud, AgregarCartaASetRequest
from app.capa_3_api.mapeadores import mapear_set_a_dto
from app.capa_0_definicion_bd.models.secretos_modelos import TipoSecreto

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

@set_router.post("/partidas/{partida_id}/sets/elegir_jugador", status_code=status.HTTP_200_OK)
async def seleccionar_destino(
    partida_id: int,
    set_id: int,
    datos: SeleccionarDestinoSolicitud,
    service: ServicioJuego = Depends(obtener_servicio_juego)
):
    jugador_id = datos.id_jugador
    id_seleccionado = datos.id_seleccionado
    posicion_secreto = datos.posicion_secreto
    try:
        await service.verificar_seleccionar_jugador_set(partida_id, jugador_id, set_id, id_seleccionado, posicion_secreto)
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
    except NoPuedeAplicarseEfectosAsiMismo:
        raise HTTPException(status_code=400, detail="No puede seleccionarse a si mismo para aplicar los efectos de su propio set")
    except SetNoCorrespondeAlJugadorSeleccionado:
        raise HTTPException(status_code=400, detail="El set no corresponde al jugador seleccionado")
    except SecretoNoEncontrado:
        raise HTTPException(status_code=400, detail="El jugador seleccionado no tiene un secreto en la posición indicada")
    except SetNoSoportaSeleccionDeJugador:
        raise HTTPException(status_code=400, detail="El set no soporta la selección de un jugador como destino")
    except PosicionSecretoNoProporcionada:
        raise HTTPException(status_code=400, detail="No se proporcionó la posición del secreto")
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    
    # Difundir a la partida quién fue elegido como destino del set
    try:
        await administrador.difundir_a_partida(
            partida_id,
            {
                "evento": "set_jugador_seleccionado",
                "partida_id": partida_id,
                "set_id": set_id,
                "jugador_id": jugador_id,
                "id_seleccionado": id_seleccionado,
                "secreto_posicion": posicion_secreto
            }
        )
    except Exception:
        pass

    # Mensaje personal al jugador seleccionado
    try:
        await administrador.enviar_mensaje(
            {
                "evento": "fuiste_seleccionado_por_set",
                "partida_id": partida_id,
                "set_id": set_id,
                "origen": jugador_id,
                "secreto_posicion": posicion_secreto
            },
            id_seleccionado
        )
    except Exception:
        # no bloquear si falla el envío privado
        pass

    return {
        "mensaje": "Destino seleccionado correctamente",
        "set_id": set_id,
        "jugador_id": jugador_id,
        "id_seleccionado": id_seleccionado,
        "secreto_posicion": posicion_secreto
    }

# Es un post porque puede tener efectos secundarios y no es idempotente
@set_router.post("/partidas/{partida_id}/sets/{set_id}/aplicar_efecto", status_code=status.HTTP_200_OK)
async def aplicar_efecto_set(
    partida_id: int,
    set_id: int,
    datos: AplicarEfectoSetSolicitud,
    service: ServicioJuego = Depends(obtener_servicio_juego)
):
    jugador_id = datos.jugador_id
    secreto_id = datos.secreto_id
    try:
        resultado = await service.aplicar_efectos_set(partida_id, jugador_id, set_id, secreto_id)
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
    except SecretoNoEncontrado:
        raise HTTPException(status_code=404, detail="Secreto no encontrado")
    except SecretoNoDisponible:
        raise HTTPException(status_code=400, detail="El secreto no está disponible para esta acción")
    except AsesinoRevelado:
        # El servicio ya marcó la partida como finalizada. Difundimos evento especial y respondemos distinto.
        try:
            await administrador.difundir_a_partida(
                partida_id,
                {
                    "evento": "asesino_revelado",
                    "partida_id": partida_id,
                    "set_id": set_id,
                    "jugador_id": jugador_id,
                    "secreto_id": secreto_id,
                    "secreto_tipo": getattr(getattr(resultado.secreto_afectado, "tipo", None), "name", None),
                    "mensaje": "Se reveló el asesino. La partida finaliza.",
                }
            )
        except Exception:
            pass
        return {
            "mensaje": "Se reveló el asesino. La partida finaliza.",
            "set_id": set_id,
            "jugador_id": jugador_id,
            "secreto_id": secreto_id,
            "secreto_tipo": getattr(getattr(resultado.secreto_afectado, "tipo", None), "name", None)
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    try:
        await administrador.difundir_a_partida(
            partida_id,
            {
                "evento": "efecto_set_aplicado",
                "partida_id": partida_id,
                "set_id": set_id,
                "jugador_id": jugador_id,
                "secreto_id": secreto_id,
                "posicion_secreto": resultado.posicion_secreto,
                "secreto_estado": getattr(getattr(resultado.secreto_afectado, "estado", None), "name", None),
                "secreto_tipo": getattr(getattr(resultado.secreto_afectado, "tipo", None), "name", None)
            }
        )
    except Exception:
        pass

    return {
        "mensaje": "Efecto del set aplicado correctamente",
        "set_id": set_id,
        "jugador_id": jugador_id,
        "secreto_id": secreto_id,
        "posicion_secreto": resultado.posicion_secreto,
        "secreto_estado": getattr(getattr(resultado.secreto_afectado, "estado", None), "name", None),
        "secreto_tipo": getattr(getattr(resultado.secreto_afectado, "tipo", None), "name", None)
    }


@set_router.patch("/partidas/{partida_id}/sets/{set_id}/agregar_carta", response_model=JugarSetRespuesta, status_code=status.HTTP_200_OK)
async def agregar_carta_a_set(
    partida_id: int,
    set_id: int,
    datos: AgregarCartaASetRequest,
    service: ServicioJuego = Depends(obtener_servicio_juego)
):
    try:
        resultado = await service.agregar_carta_a_set_propio(partida_id, datos.id_jugador, datos.carta_id, set_id)
        set_dto = mapear_set_a_dto(resultado.set)
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except JugadorNoEncontrado:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    except JugadorNoEnPartida:
        raise HTTPException(status_code=400, detail="El jugador no pertenece a la partida indicada")
    except SetNoEncontrado:
        raise HTTPException(status_code=404, detail="Set no encontrado")
    except SetNoCorrespondeAlJugadorSeleccionado:
        raise HTTPException(status_code=400, detail="El set no corresponde al jugador seleccionado")
    except CartaNoEncontrada:
        raise HTTPException(status_code=404, detail="Carta no encontrada")
    except CartaNoEnMano:
        raise HTTPException(status_code=400, detail="La carta no está en la mano del jugador")
    except TipoCartaNoCompatibleConSet:
        raise HTTPException(status_code=400, detail="Solo se pueden agregar cartas de tipo detective al set")
    except CartaNoCompatibleConSet:
        raise HTTPException(status_code=400, detail="La carta no es compatible con el set")
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    # Notificar a todos los jugadores de la partida (no bloqueante)
    try:
        await administrador.difundir_a_partida(
            partida_id,
            {
                "evento": "carta_agregada_a_set",
                "partida_id": partida_id,
                "id_jugador": datos.id_jugador,
                "set_id": set_id,
                "carta_id": datos.carta_id,
                "set": set_dto.model_dump()
            }
        )
    except Exception:
        pass

    return JugarSetRespuesta(
        mensaje="Carta agregada al set correctamente",
        set=set_dto
    )