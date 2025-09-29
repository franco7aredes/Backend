from fastapi import APIRouter, status, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.databases import get_db
from app.db.models.cartas_models import Carta, PosicionCarta
from app.websockets.ApiWS import manager
from app.db.models.jugadores_models import Jugador as JugadorModel
from app.db.models.partidas_models import Partida as PartidaModel
from app.db.models.partidas_models import EstadoPartida

mazo_router = APIRouter()


@mazo_router.put("/partida/{partida_id}/reponer", status_code=status.HTTP_200_OK)
async def reponer_mazo(partida_id: int, data: dict, db: Session = Depends(get_db)):
    MAX_CARTAS_EN_MANO = 6

    jugador_id = data.get("jugador_id")

    # validar que exista el jugador
    jugador = db.query(JugadorModel).filter_by(id_jugador=jugador_id).first()
    if not jugador:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")

    # validar que exista la partida
    partida = db.query(PartidaModel).filter_by(id_partida=partida_id).first()
    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")

    # validar que el jugador pertenezca a la partida solicitada
    if getattr(jugador, "id_partida", None) != partida_id:
        raise HTTPException(status_code=400, detail="El jugador no pertenece a la partida indicada")
    
    cartas_mano = db.query(Carta).filter_by(id_jugador=jugador_id,  id_partida=partida_id, posicion=PosicionCarta.mano).count()
    cartas_reponer = MAX_CARTAS_EN_MANO - cartas_mano

    if cartas_reponer == 0:
        return {"mensaje": "El jugador ya tiene el maximo de cartas en la mano"}
    
    cartas_disponibles = db.query(Carta).filter_by(
        id_partida=partida_id,
        posicion=PosicionCarta.mazo,
        id_jugador=None
    ).limit(cartas_reponer).all()

    if not cartas_disponibles:
"""
        # Si el mazo ya está vacío, actualizar estado de la partida y notificar
        partida_db = db.query(PartidaModel).filter(PartidaModel.id_partida == partida_id).first()
        if partida_db is not None:
            try:
                if getattr(partida_db, 'estado', None) != EstadoPartida.Finalizada:
                    partida_db.estado = EstadoPartida.Finalizada  
                    db.add(partida_db)
                    db.commit()
            except Exception:
                db.rollback()

        # Notificar por WebSocket solo a jugadores de esta partida
        jugadores_ids = [jid for (jid,) in db.query(Jugador.id_jugador).filter_by(id_partida=partida_id).all()]
        for jid in jugadores_ids:
            await manager.send_text(jid, "fin_de_mazo")
"""
        partida.estado = EstadoPartida.Finalizada
        db.add(partida)
        db.commit()
        db.refresh(partida)
        # Notificamos a todos los clientes conectados al tablero de esta partida
        mensaje = {"evento": "partida_finalizada", "partida_id": partida_id, "motivo": "mazo_agotado"}
        try:
            await manager.broadcast_to_partida(partida_id, mensaje)
        except Exception:
            # Si no hay listeners o falla el envío, continuamos
            pass

        raise HTTPException(status_code=404, detail="No hay cartas disponibles en el mazo")

    for carta in cartas_disponibles:
        carta.id_jugador = jugador_id  
        carta.posicion = PosicionCarta.mano  
        db.add(carta)
    
    db.commit()

    # Si el mazo quedó vacío luego de reponer, actualizar estado y notificar a los jugadores de la partida
    restantes = db.query(Carta).filter_by(id_partida=partida_id, posicion=PosicionCarta.mazo, id_jugador=None).count()
    if restantes == 0:
        # Actualizar estado de la partida a Finalizada (si no lo está ya)
        partida_db = db.query(PartidaModel).filter(PartidaModel.id_partida == partida_id).first()
        if partida_db is not None:
            try:
                if getattr(partida_db, 'estado', None) != EstadoPartida.Finalizada:
                    partida_db.estado = EstadoPartida.Finalizada
                    db.add(partida_db)
                    db.commit()
            except Exception:
                db.rollback()

        jugadores_ids = [jid for (jid,) in db.query(Jugador.id_jugador).filter_by(id_partida=partida_id).all()]
        for jid in jugadores_ids:
            # Notificación dirigida solo a jugadores de esta partida
            import asyncio
            if asyncio.iscoroutinefunction(manager.send_text):
                await manager.send_text(jid, "fin_de_mazo")
            else:
                # Fallback por si cambia la firma
                await manager.send_text(jid, "fin_de_mazo")

    return {
        "mensaje": f"Se repusieron {len(cartas_disponibles)} cartas",
        "cartas": [{"id": c.id_carta, "posicion": c.posicion.value} for c in cartas_disponibles]
    }

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


@mazo_router.get("/partida/{partida_id}/mano/{jugador_id}", status_code=status.HTTP_200_OK)
def obtener_mano_jugador(partida_id: int, jugador_id: int, db: Session = Depends(get_db)):
    """
    Devuelve la cantidad de cartas en mano del jugador en la partida.
    """
    count = db.query(Carta).filter_by(id_partida=partida_id, id_jugador=jugador_id, posicion=PosicionCarta.mano).count()
    return {"cantidad": count}
