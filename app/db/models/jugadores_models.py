from sqlalchemy import Column, ForeignKey, Integer, String, Date
from app.db.databases import Base

class Jugador(Base):
    __tablename__ = "jugadores"

    id_jugador = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    orden_turno = Column(Integer, nullable=False)
    id_avatar = Column(Integer, nullable=False)
    id_partida = Column(Integer, ForeignKey("partidas.id_partida"), nullable=True)  # nullable=True para evitar el ciclo duro
    
    #CHARLARLO CON LOS CHICOS