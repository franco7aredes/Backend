from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.partidas import PartidaCreada, Jugador as JugadorSchema, Partida as PartidaSchema
from app.db.databases import get_db
from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida
from app.db.models.jugadores_models import Jugador as JugadorModel

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
        id_jugador_creador=0,  # Se puede actualizar luego
        cantidad_jugadores=1,
        turno_actual=1,
        minimo=partida.minimo,
        maximo=partida.maximo
    )
    db.add(nueva_partida)
    db.commit()
    db.refresh(nueva_partida)

    jugador = JugadorModel(
        id_partida=nueva_partida.id_partida,
        nombre=partida.jugador_creador,
        fecha_nacimiento=fecha_nac,
        orden_turno=1,
        id_avatar=1
    )
    db.add(jugador)
    db.commit()
    db.refresh(jugador)
    nueva_partida.id_jugador_creador = jugador.id_jugador
    db.commit()
    db.refresh(nueva_partida)
    return {
        "mensaje": "partida creada con exito"
    }

