from sqlalchemy import Column, ForeignKey, Integer, Enum, event
import enum
from app.db.databases import Base
from app.db.models.obtener_cartas import repartir_cartas_a_jugadores
from sqlalchemy.orm import relationship

from app.core.async_utils import _dispatch_async_notification

from sqlalchemy.orm import object_session # necesito esto para tests

import app.core.constantes as C

class EstadoPartida(enum.Enum):
    en_espera = "En espera"
    en_juego = "En Juego"
    Finalizada = "Finalizada"

class Partida(Base):
    __tablename__ = "partidas"

    id_partida = Column(Integer, primary_key=True, autoincrement=True)
    minimo = Column(Integer, nullable=False)
    maximo = Column(Integer, nullable=False)
    estado = Column(Enum(EstadoPartida), nullable=False)
    cantidad_jugadores = Column(Integer, nullable=False)
    id_jugador_creador = Column(Integer, ForeignKey("jugadores.id_jugador"), nullable=False)
    turno_actual = Column(Integer, nullable=False)

    jugadores = relationship(
        "Jugador", 
        back_populates="partida", 
        foreign_keys="[Jugador.id_partida]",
        cascade="all, delete"
        )
      
    cartas = relationship("Carta", back_populates="partida", cascade="all, delete")
    
# esto es un listener, actua de forma similar a un trigger de base de datos
@event.listens_for(Partida.estado, 'set')
def repartir_cartas(target, value, oldvalue, initiator):

    cambio_valido = (oldvalue == 'En espera') and (value == 'En Juego')

    partida_valida = target.id_partida is not None

    cant_jugadores = target.cantidad_jugadores

    if cambio_valido and partida_valida and cant_jugadores >= target.minimo:
        session = object_session(target)
        if session is None:
            print("Advertencia: La partida no esta en una sesion activa")
            return value
        
        # aca se usa la funcion de obtener cartas
        datos_reparto = repartir_cartas_a_jugadores(session, target.id_partida, C.CARTAS_POR_MANO)

        # las primeras estan separadas por jugador
        repartidas = datos_reparto.get("repartidas",{})
        mazo = datos_reparto.get("mazo", [])

        todas_las_cartas = mazo.copy()

        for jugador_id in repartidas:
            todas_las_cartas.extend(repartidas[jugador_id])
        #se tienen que agregar las cartas a la sesion
        session.add_all(todas_las_cartas)

        # se tiene que hacer el commit ahora
        try:
            session.commit()
            print(f"Cartas repartidas y guardadas para la partida {target.id_partida}: {len(todas_las_cartas)}")
            
            # Se tienen que notificar a cada jugador (se delega a una
            # funcion asincrona)
            if repartidas:
                _dispatch_async_notification(repartidas)
    

        except Exception as e:
            session.rollback()
            print(f"Error al guardar cartas: {e}")
            # Ver que hacer si falla el commit
    
    return value
