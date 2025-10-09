import enum
from sqlalchemy import Column, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.capa_0_definicion_bd.base_datos_sqlalchemy import Base


class EstadoSecreto(enum.Enum):
	oculto = "oculto"
	revelado = "revelado"


class TipoSecreto(enum.Enum):
	asesino = "asesino"
	complice = "complice"
	otro = "otro"


class SecretoDB(Base):
	__tablename__ = "secretos"

	id_secreto = Column(Integer, primary_key=True, autoincrement=False)
	id_partida = Column(Integer, ForeignKey("partidas.id_partida"), primary_key=True, nullable=False)
	id_jugador = Column(Integer, ForeignKey("jugadores.id_jugador"), nullable=False)
	tipo = Column(Enum(TipoSecreto), nullable=False)
	estado = Column(Enum(EstadoSecreto), nullable=False, default=EstadoSecreto.oculto)

	# Relaciones simples (sin back_populates para no exigir atributos en el otro lado)
	partida = relationship("Partida", back_populates="secretos")
	jugador = relationship("Jugador", back_populates="secretos")
