from typing import List, cast, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from app.capa_3_api.dtos.partidas import (
    PartidaCrear,
    Jugador as JugadorDTO,
    Partida as PartidaDTO,
    JugadorCrear,
)
from app.capa_3_api.dtos.juego import SecretoDTO, JugarEventoDTO
from app.capa_3_api.websockets.ApiWS import administrador
import app.capa_2_logica.constantes as C
from app.capa_3_api.utilidades_asincronas import _notificar_jugadores_async
# Alias de compatibilidad para tests existentes que parchan este nombre
_notify_players_async = _notificar_jugadores_async
from app.capa_3_api.mapeadores import (
    mapear_partidas_a_dto,
    mapear_partida_a_dto,
    mapear_jugadores_a_dto,
    mapear_secretos_a_dto,
    mapear_cartas_a_dto
)

# Nuevo: servicio de juego (capa 2) con repos async 
from app.capa_2_logica.servicio_juego import ServicioJuego
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import *
partida_router = APIRouter()

# Helper para acceder tanto dicts como objetos con atributos (p.ej., clase J de los tests)
def _jval(j, key: str):
    return j[key] if isinstance(j, dict) else getattr(j, key)

@partida_router.get("/partidas", response_model=List[PartidaDTO])
async def listar_partidas(service: ServicioJuego = Depends(obtener_servicio_juego)):
    try:
        partidas_db = await service.listar_en_espera()
        return mapear_partidas_a_dto(partidas_db)
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@partida_router.get("/partidas/{partida_id}", response_model=PartidaDTO)
async def obtener_partida(partida_id: int, service: ServicioJuego = Depends(obtener_servicio_juego)):
    try:
        partida = await service.obtener_por_id(partida_id)
        if not partida:
            raise HTTPException(status_code=404, detail="Partida no encontrada")
        return mapear_partida_a_dto(partida)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@partida_router.get("/partidas/{partida_id}/jugadores", response_model=List[JugadorDTO])
async def listar_jugadores_partida(partida_id: int, service: ServicioJuego = Depends(obtener_servicio_juego)):
    try:
        partida = await service.obtener_por_id(partida_id)
        if not partida:
            raise HTTPException(status_code=404, detail="Partida no encontrada")
        jugadores = await service.listar_jugadores(partida_id)
        return mapear_jugadores_a_dto(jugadores)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")



@partida_router.post(path="/partidas", status_code=status.HTTP_201_CREATED)
async def crear_partida(partida: PartidaCrear, service: ServicioJuego = Depends(obtener_servicio_juego)):
    try:
        # Usamos el servicio (async + repos async) para crear partida y jugador
        res = await service.crear_partida(
            jugador_creador=partida.jugador_creador,
            fecha_nac=partida.fecha_nac,
            minimo=partida.minimo,
            maximo=partida.maximo,
        )
        nueva_partida, jugador = res.partida, res.jugador

        # Difusión por WebSocket para que el frontend se actualice
        await administrador.difundir("nueva_partida")

        return {
            "mensaje": "partida creada con exito",
            "id_partida": nueva_partida.id_partida,
            "id_jugador_creador": jugador.id_jugador,
            "estado": nueva_partida.estado.value if hasattr(nueva_partida.estado, 'value') else nueva_partida.estado,
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@partida_router.patch("/partidas/{partida_id}/iniciar", response_model=None , status_code=status.HTTP_200_OK)
async def iniciar_partida(partida_id:int, data: dict, service: ServicioJuego = Depends(obtener_servicio_juego)):
    try:
        resultado = await service.iniciar_y_preparar_partida(partida_id, C.CARTAS_POR_MANO)
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except MinimoJugadoresNoAlcanzado:
        raise HTTPException(status_code=400, detail="La partida no tiene la cantidad mínima de jugadores para iniciar")
    except PartidaYaEnJuego:
        raise HTTPException(status_code=400, detail="La partida ya esta en juego")
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    # Notificaciones mínimas (capa 3)
    # Soportamos tanto dataclass (nuevo) como dict (tests que mockean)
    repartidas = getattr(resultado, "repartidas", None)

    if repartidas is None and isinstance(resultado, dict):
        repartidas = resultado.get("repartidas", {})
    if repartidas:
        await _notify_players_async(repartidas)

    # Ahora mando los secretos
    secretos_repartidos = getattr(resultado, "secretos", None)
    if secretos_repartidos is None and isinstance(resultado, dict):
        secretos_repartidos = resultado.get("secretos", {})
    if secretos_repartidos:
        for jugador_id, secretos in secretos_repartidos.items():
            secretos_data =[s.model_dump() for s in mapear_secretos_a_dto(secretos)]
            mensaje = {"evento": "partida_iniciada", "data": {"secretos": secretos_data}}
            await administrador.enviar_mensaje(mensaje, jugador_id)

    await administrador.difundir_a_partida(partida_id, {"evento": "partida_iniciada", "partida_id": partida_id, "estado": "En Juego"})

    return {"mensaje": "La partida comenzo", "estado": "En Juego"}


@partida_router.put("/partidas/{partida_id}/unirse", status_code= status.HTTP_201_CREATED)
async def unirse_a_partida(partida_id: int, jugador: JugadorCrear, service: ServicioJuego = Depends(obtener_servicio_juego)):
    try:
        res_unirse = await service.unirse_a_partida(
            partida_id=partida_id,
            nombre=jugador.nombre,
            fecha_nacimiento=jugador.fecha_nacimiento,
            id_avatar=jugador.id_avatar,
        )
        # Compatibilidad: puede ser dataclass o tuple
        if hasattr(res_unirse, "partida"):
            partida, nuevo_jugador = res_unirse.partida, res_unirse.jugador
        else:
            partida, nuevo_jugador = res_unirse  # type: ignore[misc]
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except MaximoJugadoresAlcanzado:
        raise HTTPException(status_code=400, detail="La partida ya tiene el máximo de jugadores")
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    # obtener jugadores para notificar
    jugadores_en_partida = await service.listar_jugadores(partida_id)
    jugadores_info = [
        {
            "id_jugador": _jval(j, "id_jugador"),
            "nombre": _jval(j, "nombre"),
            "id_avatar": _jval(j, "id_avatar"),
            "orden_turno": _jval(j, "orden_turno"),
        }
        for j in jugadores_en_partida
    ]
    mensaje_lista = {
        "evento": "jugadores_actualizados",
        "partida_id": partida_id,
        "jugadores": jugadores_info
    }
    mensaje_uno = {
        "evento": "jugador_unido",
        "partida_id": partida_id,
        "jugador": {"id_jugador": nuevo_jugador.id_jugador, "nombre": nuevo_jugador.nombre, "id_avatar": nuevo_jugador.id_avatar}
    }
    for j in jugadores_en_partida:
        await administrador.enviar_mensaje(mensaje_lista, cast(int, _jval(j, "id_jugador")))
    await administrador.difundir_a_partida(partida_id, mensaje_uno)
    
    return {
        "mensaje":"jugador agregado",
        "jugador_id":nuevo_jugador.id_jugador,
        "id_partida": partida.id_partida,
        "id_jugador_creador": partida.id_jugador_creador,
        "estado": partida.estado.value if hasattr(partida.estado, 'value') else partida.estado
    }


# Aca se le pega cuando se quiera terminar turno, y se maneja la logica adentro
@partida_router.patch("/partidas/{partida_id}/terminar_turno", response_model=None, status_code=status.HTTP_200_OK)
async def terminar_turno(partida_id: int, id_enviada: int, service: ServicioJuego = Depends(obtener_servicio_juego)):
    try:
        turno = await service.terminar_turno(partida_id, id_enviada)
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except PermissionError:
        raise HTTPException(status_code=400, detail="No sos el que tiene el turno, crack")
    except ValueError as e:
        if str(e) == "partida_no_en_juego":
            raise HTTPException(status_code=400, detail="La partida no está en juego")
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    jugadores_en_partida = await service.listar_jugadores(partida_id)
    mensaje = {"turno_nuevo": turno.turno_nuevo}
    for j in jugadores_en_partida:
        await administrador.enviar_mensaje(mensaje, cast(int, _jval(j, "id_jugador")))
    return mensaje

@partida_router.delete("/partidas/{partida_id}/abandonar", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def abandonar_partida(partida_id: int, id_jugador: int, service: ServicioJuego = Depends(obtener_servicio_juego)):
    try:
        res = await service.abandonar_partida(partida_id, id_jugador)
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except JugadorNoEncontrado:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    except JugadorNoEnPartida:
        raise HTTPException(status_code=400, detail="El jugador no pertenece a la partida")
    except PartidaEnJuegoNoAbandonable:
        raise HTTPException(status_code=400, detail="No se puede abandonar una partida ya comenzada")
    except CreadorNoPuedeAbandonarPartida:
        raise HTTPException(status_code=400, detail="El creador no puede abandonar la partida")
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    # Broadcast al resto de los jugadores de la partida
    try:
        await administrador.difundir_a_partida(
            partida_id,
            {
                "evento": "jugador_abandono",
                "partida_id": res.partida_id,
                "jugador_id": res.jugador_id,
                "cantidad_jugadores": res.cantidad_jugadores,
            },
        )
    except Exception:
        # no romper el endpoint por fallas de notificación
        pass

    # Por lo general el delete no retorna nada, por eso se usa 204 para indicar éxito
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@partida_router.post("/partidas/{partida_id}/eventos", status_code=status.HTTP_200_OK)
async def jugar_evento(partida_id: int, datos: JugarEventoDTO, service: ServicioJuego = Depends(obtener_servicio_juego)):
    try:
        resultado = await service.preparar_evento(
            partida_id=partida_id,
            jugador_id=datos.id_jugador,
            carta_id=datos.id_carta,
            carta_descarte=datos.id_carta_descarte,
            secreto_id=datos.id_secreto,
            jugador_objetivo_id=datos.id_jugador_objetivo,
            set_id=datos.id_set
        )
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except JugadorNoEncontrado:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    except JugadorNoEnPartida:
        raise HTTPException(status_code=400, detail="El jugador no pertenece a la partida")
    except CartaNoEsEvento:
        raise HTTPException(status_code=400, detail="La carta no es un evento")
    except EventoNoImplementado as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    mensaje = {
        "evento": "evento_jugado",
        "partida_id": partida_id,
        "jugador_id": datos.id_jugador,
        "tipo_evento": resultado.tipo_evento,
        "mensaje": resultado.mensaje,
        "fin_de_mazo": resultado.fin_de_mazo if resultado.fin_de_mazo is not None else None,
        "carta_evento_descartada": resultado.carta_evento_descartada.id_carta if resultado.carta_evento_descartada else None,
        "asesino_ganador": resultado.asesino_ganador if resultado.asesino_ganador is not None else None
    }
    try:
        await administrador.difundir_a_partida(partida_id, mensaje)
    except Exception:
        pass  

    return {
        "mensaje": "Evento jugado con éxito",
        "tipo_evento": resultado.tipo_evento,
        "detalle": resultado.mensaje,
        "cartas_descartadas": [c.id_carta for c in resultado.cartas_descartadas or []],
        "cartas_agregadas": [c.id_carta for c in resultado.cartas_agregadas or []],
        "cartas_repuestas": [c.id_carta for c in resultado.cartas_repuestas or []],
        "secreto_oculto": resultado.secreto_oculto.id_secreto if resultado.secreto_oculto else None,
        "fin_de_mazo": resultado.fin_de_mazo if resultado.fin_de_mazo is not None else None,
        "carta_evento_descartada": resultado.carta_evento_descartada.id_carta if resultado.carta_evento_descartada else None
    }