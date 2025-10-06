from sqlalchemy import Column, ForeignKey, Integer, Enum, event
import enum
from app.db.databases import Base
from sqlalchemy.orm import relationship


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

    secretos = relationship("SecretoDB", back_populates="partida", cascade="all, delete")
    
