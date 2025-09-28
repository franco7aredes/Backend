from fastapi import APIRouter, status, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.databases import get_db
from app.db.models.cartas_models import Carta

mazo_router = APIRouter()


@mazo_router.patch("/partida/{partida_id}/descartar", status_code=status.HTTP_200_OK)
def descartar_carta_por_jugador(partida_id: int, data: dict, db: Session = Depends(get_db)):
    jugador_id = data.get("jugador_id")
    carta = db.query(Carta).filter_by(id_jugador=jugador_id, id_partida=partida_id).first()
    if not carta:
        raise HTTPException(status_code=404, detail="No se encontró carta" \
        " para descartar en esta partida")
    # id_jugador es nullable, por lo que se puede asignar None.
    carta.id_jugador = None
    from app.db.models.cartas_models import PosicionCarta
    carta.posicion = PosicionCarta.descarte
    db.add(carta)
    db.commit()
    db.refresh(carta)
    return {"mensaje": f"Carta {carta.id_carta} descartada por jugador {jugador_id} en partida {partida_id}"}