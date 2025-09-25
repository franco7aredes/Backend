from sqlalchemy import Column, Integer, ForeignKey, Enum, create_engine
from sqlalchemy.orm import relationship
from databases import Base
import enum


class PosicionCarta(enum.Enum):
    mazo = "mazo"          # Mazo normal
    mano = "mano"          # Mano del jugador
    descarte = "descarte"  # Mazo de descarte

class Carta(Base):
    __tablename__ = "cartas"

    id_carta = Column(Integer, primary_key=True, autoincrement=True)
    id_partida = Column(Integer, ForeignKey("partidas.id_partida"), nullable=False)
    id_jugador = Column(Integer, ForeignKey("jugadores.id_jugador"), nullable=True)  # Puede no tener dueño

    posicion = Column(Enum(PosicionCarta), nullable=False, default=PosicionCarta.mazo)

    # Relaciones
    jugador = relationship("Jugador", back_populates="cartas")
    partida = relationship("Partida", back_populates="cartas")


