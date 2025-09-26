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


@partida_router.get("/partidas/{partida_id}", response_model=PartidaSchema)
def obtener_partida(partida_id: int, db: Session = Depends(get_db)):
    partida = db.query(PartidaModel).filter(PartidaModel.id_partida == partida_id).first()
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    return partida

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

    return {"mensaje":"La partida comenzo","estado": partida.estado}


@partida_router.post("/partidas/{partida_id}/unirse", status_code= status.HTTP_201_CREATED)
def unirse_a_partida(partida_id: int,jugador: JugadorCreate , db: Session = Depends(get_db)):
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
