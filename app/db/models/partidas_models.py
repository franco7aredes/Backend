from sqlalchemy import Column, ForeignKey, Integer, Enum, event
import enum
from app.db.databases import Base
from sqlalchemy.orm import relationship

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
    
@event.listens_for(Partida.estado, 'set')
def repartir_cartas(target, value, oldvalue, initiator):

    cambio_valido = (oldvalue == 'En espera') and (value == 'En Juego')

    partida_valida = target.id_partida is not None

    if cambio_valido and partida_valida:
        session = object_session(target)
        if session is None:
            print("Advertencia: La partida no esta en una sesion activa")
            return value
        
        # aca se usa la funcion de obtener cartas

        #se tienen que agregar las cartas a la sesion
    
    return value
