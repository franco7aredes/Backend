from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
import asyncio
from sqlalchemy.orm import Session
from app.schemas.partidas import PartidaCreada, Jugador as JugadorSchema, Partida as PartidaSchema, JugadorCreate
from app.db.databases import get_db
from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida
from app.db.models.jugadores_models import Jugador as JugadorModel
from app.websockets.ApiWS import manager


import app.core.constantes as C

from app.routers.obtener_cartas import repartir_cartas_a_jugadores
from app.core.async_utils import _notify_players_async


partida_router = APIRouter()

@partida_router.get("/partidas", response_model=List[PartidaSchema])
async def listar_partidas(db: Session = Depends(get_db)):
    partidas_db = db.query(PartidaModel).filter(
        PartidaModel.estado == EstadoPartida.en_espera).all()
    partidas = [
        PartidaSchema(
            id_partida=p.id_partida,
            minimo=p.minimo,
            maximo=p.maximo,
            estado=p.estado.value if hasattr(p.estado, 'value') else p.estado,
            cantidad_jugadores=p.cantidad_jugadores,
            turno_actual=p.turno_actual,
            jugadores=[]
        )
        for p in partidas_db
    ]
    return partidas

@partida_router.post(path="/partidas", status_code=status.HTTP_201_CREATED)
async def crear_partida(partida: PartidaCreada, db: Session = Depends(get_db)):
    fecha_nac = partida.fecha_nac.date() 
    nueva_partida = PartidaModel(
        estado=EstadoPartida.en_espera,
        id_jugador_creador=0,
        cantidad_jugadores=1,
        turno_actual=1,
        minimo=partida.minimo,
        maximo=partida.maximo)

    db.add(nueva_partida)
    db.commit()
    db.refresh(nueva_partida)

    jugador = JugadorModel(
        id_partida=nueva_partida.id_partida,
        nombre=partida.jugador_creador,
        fecha_nacimiento=fecha_nac,
        orden_turno=1,
        id_avatar=1)

    db.add(jugador)
    db.commit()
    db.refresh(jugador)

    nueva_partida.id_jugador_creador=jugador.id_jugador
    db.commit()

    # Broadcast por WebSocket para que el frontend se actualice
    await manager.broadcast("nueva_partida")
    
    return {
        "mensaje": "partida creada con exito",
        "id_partida": nueva_partida.id_partida,
        "id_jugador_creador": jugador.id_jugador
    }


@partida_router.patch("/partidas/{partida_id}/iniciar", response_model=None , status_code=status.HTTP_200_OK)
def iniciar_partida(partida_id:int, data: dict, db: Session = Depends(get_db)):
    partida = db.query(PartidaModel).filter(PartidaModel.id_partida == partida_id).first()

    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    
    if partida.estado == EstadoPartida.en_espera:
        partida.estado = EstadoPartida.en_juego  
        # si quiero cambiar a un estado q me llega por usuario deberia usar
        # el dict q me llega leerlo y modificar el estado.
    elif partida.estado == EstadoPartida.en_juego:
        raise HTTPException(status_code=400, detail="La partida ya esta en juego")
    
    db.commit()
    db.refresh(partida)

    # Aca voy a meter la logica de obtener cartas, y enviarlas a cada jugador
    datos_reparto = repartir_cartas_a_jugadores(db, partida.id_partida, C.CARTAS_POR_MANO)
    # esto de arriba es un Dict[str, Any]
    
    repartidas = datos_reparto.get("repartidas", {})
    mazo = datos_reparto.get("mazo", [])

    todas_las_cartas = mazo.copy()
    for jugador_id in repartidas:
        todas_las_cartas.extend(repartidas[jugador_id])
        # se tienen que agregar las cartas a la sesion
        db.add_all(todas_las_cartas)

        # se tiene que hacer el commit ahora
        try:
            db.commit()
            print(f"Cartas repartidas y guardadas para la partida {partida.id_partida}: {len(todas_las_cartas)}")

            # Se tienen que notificar a cada jugador
            if repartidas:
                _notify_players_async(repartidas)


        except Exception as e:
            db.rollback()
            print(f"Error al guardar cartas: {e}")
            # Ver que hacer si falla el commit

    
    return {"mensaje": "La partida comenzo", "estado": partida.estado}


@partida_router.put("/partidas/{partida_id}/unirse", status_code= status.HTTP_201_CREATED)
def unirse_a_partida(partida_id: int, jugador: JugadorCreate, db: Session = Depends(get_db)):
    partida = db.query(PartidaModel).filter(PartidaModel.id_partida == partida_id).first()
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")

    # Validar máximo de jugadores
    if partida.cantidad_jugadores >= partida.maximo:
        raise HTTPException(status_code=400, detail="La partida ya tiene el máximo de jugadores")

    nuevo_jugador = JugadorModel(
        id_partida=partida.id_partida,
        nombre=jugador.nombre,
        fecha_nacimiento=jugador.fecha_nacimiento,
        orden_turno=0,
        id_avatar=1  # ejemplo, puedes cambiar
    )

    db.add(nuevo_jugador)
    partida.cantidad_jugadores +=1
    db.commit()
    db.refresh(nuevo_jugador)
    db.refresh(partida)
    
    return {
        "mensaje":"jugador agregado",
        "jugador_id":nuevo_jugador.id_jugador
    }

# Aca se le pega cuando se quiera terminar turno, y se maneja la logica adentro
@partida_router.patch("/partidas/{partida_id}/terminar_turno", response_model=None, status_code=status.HTTP_200_OK)
def terminar_turno(partida_id: int, id_enviada: int, db: Session = Depends(get_db)):
    partida = db.query(PartidaModel).filter(PartidaModel.id_partida == partida_id).first()

    jugador = db.query(JugadorModel).filter(JugadorModel.id_jugador == id_enviada).first()

    # Verifico que el que me mando la solicitud es el que me mando el turno
    if jugador.orden_turno != partida.turno_actual:
        raise HTTPException(status_code=400, detail="No sos el que tiene el turno, crack")

    cantidad_jugadores= partida.cantidad_jugadores
    if partida.turno_actual == cantidad_jugadores:
        partida.turno_actual = 1
    else:
        partida.turno_actual += 1

    db.commit()
    db.refresh(partida)

    # Ahora, tengo que notificar a los usuarios de la partida sobre el cambio de turno

    jugadores_en_partida = db.query(JugadorModel).filter(JugadorModel.id_partida == partida_id).all()

    mensaje = {"turno_nuevo" : partida.turno_actual}
    
    for j in jugadores_en_partida:
        await manager.send_message(mensaje, j.id_jugador)


