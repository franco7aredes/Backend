from sqlalchemy import Column, Integer, ForeignKey, Enum, String, ForeignKeyConstraint, and_
from sqlalchemy.orm import relationship
from app.capa_0_definicion_bd.base_datos_sqlalchemy import Base
import enum
# Importar Set para que su tabla esté en el MetaData antes de definir Carta
from app.capa_0_definicion_bd.models.sets_modelos import Set  # noqa: F401

class PosicionCarta(enum.Enum):
    mazo = "mazo"  # Mazo normal
    mano = "mano"  # Mano del jugador
    descarte = "descarte"  # Mazo de descarte
    draft = "draft" # Draft
    set = "set" # Carta ubicada dentro de un set



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
    id_set = Column(Integer, nullable=True)  # FK al Set. Nullable si la carta no está en un set.
    posicion = Column(Enum(PosicionCarta), nullable=False, default=PosicionCarta.mazo)
    nombre = Column(String(50), nullable=False)
    tipo = Column(Enum(TipoCarta), nullable=False)
    # esto es dato interno, nunca se debe pasar al front
    orden_en_descarte = Column(Integer, nullable=True)

    __table_args__ = (
        # Clave Foránea Compuesta: (id_set, id_partida) referencias sets(id_set, id_partida)
        ForeignKeyConstraint(
            ['id_set', 'id_partida'],
            ['sets.id_set', 'sets.id_partida'],
            name='fk_carta_set_compuesta',
        ),
    )

    # Relaciones
    partida = relationship("Partida", back_populates="cartas")

    jugador = relationship("Jugador", back_populates="cartas")
    
    set = relationship(
        "Set",
        back_populates="cartas",
        primaryjoin="and_(Carta.id_set == Set.id_set, Carta.id_partida == Set.id_partida)",
        foreign_keys="[Carta.id_set, Carta.id_partida]",
        overlaps="partida, cartas",  # comparte id_partida con Carta.partida y cartas con Set.cartas
    )

