
from fastapi import WebSocket
from sqlalchemy.orm import Session
from app.models.partida import Partida
from app.models.carta import Carta
from app.models.jugador import Jugador
from app.database import get_db
import random

async def repartir_cartas_a_jugadores(db: Session, partida_id: int, manager, num_cartas: int):
    # 1. Obtener la partida y sus jugadores
    partida = db.query(Partida).filter(Partida.id == partida_id).first()
    if not partida:
        return {"error": "Partida no encontrada"}

    jugadores = db.query(Jugador).filter(Jugador.id_partida == partida_id).all()
    if not jugadores:
        return {"error": "Jugadores no encontrados"}
    # 2. Crear las cartas del mazo de la partida
    mazo_cartas = []
    for i in range(1,62):
        carta = {
            id_carta=i
            id_partida=
        }
        mazo_cartas.append(carta)

    random.shuffle(mazo_cartas)  # Barajar el mazo

    # 3. Repartir cartas a cada jugador
    for jugador in jugadores:
        cartas_repartidas = mazo_cartas[:num_cartas]
        mazo_cartas = mazo_cartas[num_cartas:]
         
    for carta in cartas_repartidas:
        carta.id_jugador = jugador.id_jugador
        carta.posicion = 'mano'
                                                                                                            
    db.commit()

    # 4. Notificar a cada jugador a través de WebSocket
    for jugador in jugadores:
        cartas_jugador = db.query(Carta).filter(
            Carta.id_jugador == jugador.id_jugador,
            Carta.posicion == 'mano'
        ).all()
                                                          
    # Construir el mensaje con las cartas del jugador
        mensaje = {
            "evento": "cartas_repartidas",
            "cartas": [carta.to_dict() for carta in cartas_jugador]
        }
        await manager.send_message(mensaje, jugador.id_jugador)
