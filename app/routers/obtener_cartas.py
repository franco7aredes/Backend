
from fastapi import WebSocket
from sqlalchemy.orm import Session
import random
from typing import List, Dict, Any

def repartir_cartas_a_jugadores(db: Session, partida_id: int, num_cartas: int) -> Dict[str, Any]:

    from app.db.models.partidas_models import Partida, EstadoPartida
    from app.db.models.cartas_models import Carta, PosicionCarta
    from app.db.models.jugadores_models import Jugador
    from app.db.databases import get_db
    # 1. Obtener la partida y sus jugadores
    partida = db.query(Partida).filter(Partida.id_partida == partida_id).first()
    if not partida:
        return []

    jugadores = db.query(Jugador).filter(Jugador.id_partida == partida_id).all()
    if not jugadores:
        return []
    # 2. Crear las cartas del mazo de la partida
    mazo_cartas = []
    for i in range(1,62):
        carta = Carta(
            id_carta=i,
            id_partida=partida_id,
            posicion=PosicionCarta.mazo,
            id_jugador=None
        )
        mazo_cartas.append(carta)

    random.shuffle(mazo_cartas)  # Barajar el mazo

    cartas_por_jugador : Dict[int, List[Carta]] = {}
    # 3. Repartir cartas a cada jugador
    idx_carta = 0
    for jugador in jugadores:
        cartas_por_jugador[jugador.id_jugador] = []
        for _ in range(num_cartas):
            if idx_carta < len(mazo_cartas):
                carta = mazo_cartas[idx_carta]

                carta.id_jugador = jugador.id_jugador
                carta.posicion = PosicionCarta.mano

                cartas_por_jugador[jugador.id_jugador].append(carta)
                idx_carta+= 1
            
            else:
                break
    cartas_restantes_mazo = mazo_cartas[idx_carta:]

    return {
        "repartidas": cartas_por_jugador,
        "mazo": cartas_restantes_mazo
    }
                                                                                                            

