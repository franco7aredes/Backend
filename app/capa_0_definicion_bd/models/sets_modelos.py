from sqlalchemy import Column, Integer, ForeignKey, String, UniqueConstraint, and_
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.schema import PrimaryKeyConstraint, ForeignKeyConstraint
from app.capa_0_definicion_bd.base_datos_sqlalchemy import Base


class Set(Base):
    __tablename__ = 'sets'
    
    # Claves
    id_set = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    id_partida = Column(Integer, ForeignKey("partidas.id_partida"), nullable=False)
    id_jugador = Column(Integer, ForeignKey("jugadores.id_jugador"), nullable=False)
    # Nombre para identificar el Set, si bien las cartas ya tienen nombre, este es un nombre "de conjunto"
    nombre = Column(String(50), nullable=False)

    __table_args__ = (
        # Hace única la dupla (id_set, id_partida) para soportar la FK compuesta desde cartas
        UniqueConstraint("id_set", "id_partida", name="uq_sets_idset_partida"),
    )

    partida = relationship("Partida", back_populates="sets")

    jugador = relationship("Jugador", back_populates="sets")

    # ...existing code...
    cartas = relationship(
        "Carta",
        back_populates="set",
        primaryjoin="and_(Set.id_set == Carta.id_set, Set.id_partida == Carta.id_partida)",
        foreign_keys="[Carta.id_set, Carta.id_partida]",
        overlaps="partida, cartas",  # comparte id_partida con Set.partida y cartas con Carta.set
    )