# Defino los endpoints de partidas

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.schemas.partidas import PartidaCreada, Jugador as JugadorSchema, Partida as PartidaSchema
from app.db.databases import SessionLocal, get_db
from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida
from app.db.models.jugadores_models import Jugador as JugadorModel
from datetime import datetime


partida_router= APIRouter()


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
    
    return {
        "mensaje": "partida creada con exito",
        "id_partida": nueva_partida.id_partida,
        "id_jugador_creador": jugador.id_jugador
    }
