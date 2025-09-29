from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.databases import get_db
from app.db.models.cartas_models import Carta, PosicionCarta
from app.db.models.jugadores_models import Jugador as JugadorModel
from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida
from app.websockets.ApiWS import manager

mazo_router = APIRouter()


@mazo_router.put("/partida/{partida_id}/reponer", status_code=status.HTTP_200_OK)
async def reponer_mazo(partida_id: int, data: dict, db: Session = Depends(get_db)):
    MAX_CARTAS_EN_MANO = 6

    jugador_id_raw = data.get("jugador_id")
    try:
        jugador_id: int = int(jugador_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="jugador_id inválido")

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

    # cartas actuales en mano
    cartas_mano = db.query(Carta).filter_by(
        id_jugador=jugador_id,
        id_partida=partida_id,
        posicion=PosicionCarta.mano
    ).count()
    cartas_reponer = MAX_CARTAS_EN_MANO - cartas_mano

    if cartas_reponer == 0:
        return {"mensaje": "El jugador ya tiene el maximo de cartas en la mano"}

    # obtener cartas del mazo disponibles
    cartas_disponibles = db.query(Carta).filter_by(
        id_partida=partida_id,
        posicion=PosicionCarta.mazo,
        id_jugador=None
    ).limit(cartas_reponer).all()

    if not cartas_disponibles:
        # mazo agotado: marcar partida finalizada y notificar via WS (jugador y sala)
        try:
            if getattr(partida, 'estado', None) != EstadoPartida.Finalizada:
                partida.estado = EstadoPartida.Finalizada
                db.add(partida)
                db.commit()
        except Exception:
            db.rollback()

        try:
            # Primero texto plano al WS privado (para tests que esperan el primer frame como 'fin_de_mazo')
            await manager.send_text(jugador_id, "fin_de_mazo")
            # Luego JSON al privado y a la sala de la partida para el frontend
            await manager.send_message({"evento": "fin_de_mazo", "partida_id": partida_id}, jugador_id)
            await manager.broadcast_to_partida(partida_id, {"evento": "fin_de_mazo", "partida_id": partida_id})
        except Exception:
            pass

        raise HTTPException(status_code=404, detail="No hay cartas disponibles en el mazo")

    # mover cartas a la mano del jugador
    for carta in cartas_disponibles:
        carta.id_jugador = jugador_id
        carta.posicion = PosicionCarta.mano
        db.add(carta)
    db.commit()

    # verificar si quedó el mazo en cero
    restantes = db.query(Carta).filter_by(id_partida=partida_id, posicion=PosicionCarta.mazo, id_jugador=None).count()
    if restantes == 0:
        try:
            if getattr(partida, 'estado', None) != EstadoPartida.Finalizada:
                partida.estado = EstadoPartida.Finalizada
                db.add(partida)
                db.commit()
        except Exception:
            db.rollback()
        try:
            # Primero texto plano al WS privado (para tests)
            await manager.send_text(jugador_id, "fin_de_mazo")
            # Luego JSON al privado y a la sala (frontend)
            await manager.send_message({"evento": "fin_de_mazo", "partida_id": partida_id}, jugador_id)
            await manager.broadcast_to_partida(partida_id, {"evento": "fin_de_mazo", "partida_id": partida_id})
        except Exception:
            pass

    return {
        "mensaje": f"Se repusieron {len(cartas_disponibles)} cartas",
        "cartas": [{"id": c.id_carta, "posicion": c.posicion.value} for c in cartas_disponibles]
    }


@mazo_router.patch("/partida/{partida_id}/descartar", status_code=status.HTTP_200_OK)
def descartar_carta_por_jugador(partida_id: int, data: dict, db: Session = Depends(get_db)):
    jugador_id_raw = data.get("jugador_id")
    try:
        jugador_id: int = int(jugador_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="jugador_id inválido")
    carta = db.query(Carta).filter_by(id_jugador=jugador_id, id_partida=partida_id).first()
    if not carta:
        raise HTTPException(status_code=404, detail="No se encontró carta para descartar en esta partida")
    # mover a descarte
    carta.id_jugador = None
    carta.posicion = PosicionCarta.descarte
    db.add(carta)
    db.commit()
    db.refresh(carta)
    return {"mensaje": f"Carta {carta.id_carta} descartada por jugador {jugador_id} en partida {partida_id}"}


@mazo_router.get("/partida/{partida_id}/mano/{jugador_id}", status_code=status.HTTP_200_OK)
def obtener_mano_jugador(partida_id: int, jugador_id: int, db: Session = Depends(get_db)):
    """Devuelve la cantidad de cartas en mano del jugador en la partida."""
    count = db.query(Carta).filter_by(id_partida=partida_id, id_jugador=jugador_id, posicion=PosicionCarta.mano).count()
    return {"cantidad": count}
