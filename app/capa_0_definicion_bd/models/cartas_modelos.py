from sqlalchemy import Column, Integer, ForeignKey, Enum, String
from sqlalchemy.orm import relationship
from app.capa_0_definicion_bd.base_datos_sqlalchemy import Base
import enum


class PosicionCarta(enum.Enum):
	mazo = "mazo"  # Mazo normal
	mano = "mano"  # Mano del jugador
	descarte = "descarte"  # Mazo de descarte


class TipoCarta(enum.Enum):
	detective = "detective"
	instant = "instant"
	event = "event"
	devious = "devious"


class Carta(Base):
	__tablename__ = "cartas"

	id_carta = Column(Integer, primary_key=True, autoincrement=False)
	id_partida = Column(Integer, ForeignKey("partidas.id_partida"), primary_key=True, nullable=False)
	id_jugador = Column(Integer, ForeignKey("jugadores.id_jugador"), nullable=True)
	posicion = Column(Enum(PosicionCarta), nullable=False, default=PosicionCarta.mazo)
	nombre = Column(String(50), nullable=False)
	tipo = Column(Enum(TipoCarta), nullable=False)
    # esto es dato interno, nunca se debe pasar al front
    orden_en_descarte = Column(Integer, nullable=True)

	# Relaciones
	partida = relationship("Partida", back_populates="cartas")
	jugador = relationship("Jugador", back_populates="cartas")
