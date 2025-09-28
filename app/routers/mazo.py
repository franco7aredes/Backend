from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.models.cartas_models import Carta, PosicionCarta
from app.db.databases import get_db

mazo_router = APIRouter()



@mazo_router.put("/partida/{partida_id}/reponer", status_code=status.HTTP_200_OK)
def reponer_mazo(partida_id: int, data: dict, db: Session = Depends(get_db)):
    MAX_CARTAS_EN_MANO = 6

    jugador_id = data.get("jugador_id")

    # validar que exista el jugador
    jugador = db.query(Carta).filter_by(id_jugador=jugador_id).first()
    if not jugador:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")

    # validar que exista la partida
    partida = db.query(Carta).filter_by(id_partida=partida_id).first()
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    
    cartas_mano = db.query(Carta).filter_by(id_jugador=jugador_id,  id_partida=partida_id, posicion=PosicionCarta.mano).count()
    cartas_reponer = MAX_CARTAS_EN_MANO - cartas_mano

    if cartas_reponer == 0:
        return {"mensaje": "El jugador ya tiene el maximo de cartas en la mano"}
    
    cartas_disponibles = db.query(Carta).filter_by(id_partida=partida_id, posicion=PosicionCarta.mazo, id_jugador=None).limit(cartas_reponer).all()

    if not cartas_disponibles:
        raise HTTPException(status_code=404, detail="No hay cartas disponibles en el mazo")

    for carta in cartas_disponibles:
        carta.id_jugador = jugador_id
        carta.posicion = PosicionCarta.mano
        db.add(carta)
    
    db.commit()

    return {
        "mensaje": f"Se repusieron {len(cartas_disponibles)} cartas",
        "cartas": [{"id": c.id_carta, "posicion": c.posicion.value} for c in cartas_disponibles]
    }