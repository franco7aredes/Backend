# Defino los endpoints de partidas

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.partidas import PartidaCreada, Jugador as JugadorSchema, Partida as PartidaSchema

from app.db.databases import get_db,SessionLocal
from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida
from app.db.models.jugadores_models import Jugador as JugadorModel

from sqlalchemy.orm import Session

partida_router= APIRouter()
"""
endpoints usados para probar cosas (adaptar y usar luego los que son)
@partida_router.get(path="/partidas")
async def listar_partidas() -> List[PartidaSchema]:
    # Aca se define la logica para listar partidas no empezadas,
    # y enviar al usuario. Dejo lo siguiente como ejemplo, pero
    # hay que reemplazar

    partidas_db = db.query(PartidaModel).filter(PartidaModel.estado == EstadoPartida.en_espera).all()

    return partidas_db

@partida_router.post(path="/partidas", status_code=status.HTTP_201_CREATED)
async def crear_partida(partida: PartidaCreada):
    db = SessionLocal()

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

    partida_id = nueva_partida.id_partida
    creador_id = jugador.id_jugador

    db.close()
    
    return {
    "mensaje": "partida creada con exito",
    "id_partida": partida_id,
    "id_jugador_creador": creador_id
    }

"""
@partida_router.get("/{partida_id}", response_model=PartidaSchema)
def obtener_partida(partida_id: int, db: Session = Depends(get_db)):
    partida = db.query(PartidaModel).filter(PartidaModel.id_partida == partida_id).first()
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    return partida