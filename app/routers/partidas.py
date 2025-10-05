from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.partidas import PartidaCreada, Jugador as JugadorSchema, Partida as PartidaSchema, JugadorCreate
from app.websockets.ApiWS import manager
import app.core.constantes as C
from app.core.async_utils import _notify_players_async

# Nuevo: servicio de juego (capa 2) con repos async 
from app.capa_2_logica.servicio_juego import ServicioJuego
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import PartidaNoEncontrada, PartidaYaEnJuego, MinimoJugadoresNoAlcanzado, MaximoJugadoresAlcanzado

partida_router = APIRouter()

@partida_router.get("/partidas", response_model=List[PartidaSchema])
async def listar_partidas(service: ServicioJuego = Depends(obtener_servicio_juego)):
    partidas_db = await service.listar_en_espera()
    return [
        PartidaSchema(
            id_partida=p.id_partida,
            minimo=p.minimo,
            maximo=p.maximo,
            id_jugador_creador=p.id_jugador_creador,
            estado=p.estado.value if hasattr(p.estado, 'value') else p.estado,
            cantidad_jugadores=p.cantidad_jugadores,
            turno_actual=p.turno_actual,
            jugadores=[],
        )
        for p in partidas_db
    ]


@partida_router.get("/partidas/{partida_id}", response_model=PartidaSchema)
async def obtener_partida(partida_id: int, service: ServicioJuego = Depends(obtener_servicio_juego)):
    partida = await service.obtener_por_id(partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    # Construimos el esquema incluyendo campos principales
    return PartidaSchema(
        id_partida=partida.id_partida,
        minimo=partida.minimo,
        maximo=partida.maximo,
        id_jugador_creador=partida.id_jugador_creador,
        estado=partida.estado.value if hasattr(partida.estado, 'value') else partida.estado,
        cantidad_jugadores=partida.cantidad_jugadores,
        turno_actual=partida.turno_actual,
        jugadores=[]
    )

@partida_router.get("/partidas/{partida_id}/jugadores", response_model=List[JugadorSchema])
async def listar_jugadores_partida(partida_id: int, service: ServicioJuego = Depends(obtener_servicio_juego)):
    partida = await service.obtener_por_id(partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    jugadores = await service.listar_jugadores(partida_id)
    return [
        JugadorSchema(
            id_jugador=j.id_jugador,
            nombre=j.nombre,
            fecha_nacimiento=j.fecha_nacimiento,
            id_avatar=j.id_avatar,
            orden_turno=j.orden_turno,
        )
        for j in jugadores
    ]


@partida_router.post(path="/partidas", status_code=status.HTTP_201_CREATED)
async def crear_partida(partida: PartidaCreada, service: ServicioJuego = Depends(obtener_servicio_juego)):
    # Usamos el servicio (async + repos async) para crear partida y jugador
    nueva_partida, jugador = await service.crear_partida(
        jugador_creador=partida.jugador_creador,
        fecha_nac=partida.fecha_nac,
        minimo=partida.minimo,
        maximo=partida.maximo,
    )

    # Broadcast por WebSocket para que el frontend se actualice
    await manager.broadcast("nueva_partida")

    return {
        "mensaje": "partida creada con exito",
        "id_partida": nueva_partida.id_partida,
        "id_jugador_creador": jugador.id_jugador,
        "estado": nueva_partida.estado.value if hasattr(nueva_partida.estado, 'value') else nueva_partida.estado,
    }


@partida_router.patch("/partidas/{partida_id}/iniciar", response_model=None , status_code=status.HTTP_200_OK)
async def iniciar_partida(partida_id:int, data: dict, service: ServicioJuego = Depends(obtener_servicio_juego)):
    # Cambiamos estado vía servicio (async + validaciones)
    try:
        partida = await service.iniciar_partida(partida_id)
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except MinimoJugadoresNoAlcanzado:
        raise HTTPException(status_code=400, detail="La partida no tiene la cantidad mínima de jugadores para iniciar")
    except PartidaYaEnJuego:
        raise HTTPException(status_code=400, detail="La partida ya esta en juego")


    # Repartir cartas vía servicio (persiste con repos async)
    datos_reparto = await service.repartir_cartas(partida.id_partida, C.CARTAS_POR_MANO)
    # esto de arriba es un Dict[str, Any]
    
    repartidas = datos_reparto.get("repartidas", {})
    mazo = datos_reparto.get("mazo", [])

    # Notificar a cada jugador (por canal individual)
    if repartidas:
        await _notify_players_async(repartidas)



    #Logica de calcular turnos

    # Asignar turnos usando el servicio (persistencia async)
    await service.asignar_turnos(partida_id)
    
    # Notificar por sala a todos los tableros conectados
    await manager.broadcast_to_partida(partida_id, {"evento": "partida_iniciada", "partida_id": partida_id, "estado": "En Juego"})

    return {"mensaje": "La partida comenzo", "estado": "En Juego"}


@partida_router.put("/partidas/{partida_id}/unirse", status_code= status.HTTP_201_CREATED)
async def unirse_a_partida(partida_id: int, jugador: JugadorCreate, service: ServicioJuego = Depends(obtener_servicio_juego)):
    try:
        partida, nuevo_jugador = await service.unirse_a_partida(
            partida_id=partida_id,
            nombre=jugador.nombre,
            fecha_nacimiento=jugador.fecha_nacimiento,
            id_avatar=jugador.id_avatar,
        )
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except MaximoJugadoresAlcanzado:
        raise HTTPException(status_code=400, detail="La partida ya tiene el máximo de jugadores")

    # obtener jugadores para notificar
    jugadores_en_partida = await service.listar_jugadores(partida_id)
    jugadores_info = [{"id_jugador": j.id_jugador, "nombre": j.nombre, "id_avatar": j.id_avatar, "orden_turno": j.orden_turno} for j in jugadores_en_partida]

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
        await manager.send_message(mensaje_lista, j.id_jugador)
    await manager.broadcast_to_partida(partida_id, mensaje_uno)
    
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
        turno_nuevo = await service.terminar_turno(partida_id, id_enviada)
    except PartidaNoEncontrada:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    except PermissionError:
        raise HTTPException(status_code=400, detail="No sos el que tiene el turno, crack")
    except ValueError as e:
        if str(e) == "partida_no_en_juego":
            raise HTTPException(status_code=400, detail="La partida no está en juego")
        raise HTTPException(status_code=404, detail="Jugador no encontrado")

    jugadores_en_partida = await service.listar_jugadores(partida_id)
    mensaje = {"turno_nuevo": turno_nuevo}
    for j in jugadores_en_partida:
        await manager.send_message(mensaje, j.id_jugador)
    return mensaje


 
