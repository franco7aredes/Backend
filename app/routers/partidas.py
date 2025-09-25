# Defino los endpoints de partidas


from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.schemas.partidas import PartidaCreada, Jugador, Partida
from app.db.databases import get_db
from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida

partida_router = APIRouter()

@partida_router.get("/partidas", response_model=List[Partida])
def listar_partidas(db: Session = Depends(get_db)):
    # Listar solo partidas en espera
    partidas_db = db.query(PartidaModel).filter(PartidaModel.estado == EstadoPartida.en_espera).all()
    # Transformar a esquema Pydantic (Definido en partida_models.py)
    partidas = [
        Partida(
            ID=p.id_partida,
            minimo=p.minimo,
            maximo=p.maximo,
            cantidad=p.cantidad_jugadores
        )
        for p in partidas_db
    ]
    return partidas

"""" codigo de prueba 
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.databases import get_db

from app.db.models.jugadores_models import Jugador
# Importar el manager de WebSocket
from app.websockets.ApiWS import manager
import asyncio

@partida_router.post(path="/partidas", status_code=status.HTTP_201_CREATED)
async def crear_partida(partida: PartidaCreada, db: Session = Depends(get_db)):
    # Buscar o crear el jugador creador
    jugador = db.query(Jugador).filter_by(nombre=partida.jugador_creador, fecha_nacimiento=partida.fecha_nac.date()).first()
    if not jugador:
        jugador = Jugador(
            nombre=partida.jugador_creador,
            fecha_nacimiento=partida.fecha_nac.date(),
            orden_turno=1,
            id_avatar=1,
            id_partida=None
        )
        db.add(jugador)
        db.commit()
        db.refresh(jugador)

    # Crear la partida
    nueva_partida = PartidaModel(
        estado=EstadoPartida.en_espera,
        id_jugador_creador=jugador.id_jugador,
        cantidad_jugadores=1,
        turno_actual=1,
        minimo=partida.minimo,
        maximo=partida.maximo
    )
    db.add(nueva_partida)
    db.commit()
    db.refresh(nueva_partida)

    # Notificar a los clientes WebSocket que hay una nueva partida
    await manager.broadcast("nueva_partida")

    return {
        "ID": nueva_partida.id_partida,
        "minimo": nueva_partida.minimo,
        "maximo": nueva_partida.maximo,
        "cantidad": nueva_partida.cantidad_jugadores
    }
"""
