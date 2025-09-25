from sqlalchemy import Column, ForeignKey, Integer, Enum
import enum
from app.db.databases import Base

class EstadoPartida(enum.Enum):
    en_espera = "En espera"
    en_juego = "En Juego"
    Finalizada = "Finalizada"

class Partida(Base):
    __tablename__ = "partidas"

    id_partida =Column(Integer, primary_key=True, autoincrement=True)
    estado=Column(Enum(EstadoPartida), nullable=False)
    id_jugador_creador=Column(Integer, ForeignKey("jugadores.id_jugador"), nullable=False)
    cantidad_jugadores= Column(Integer, nullable=False)
    turno_actual = Column(Integer, nullable=False)
    minimo = Column(Integer, nullable=False)
    maximo = Column(Integer, nullable=False)

