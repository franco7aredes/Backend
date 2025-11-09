from sqlalchemy import Column, ForeignKey, Integer, String, Date
from app.capa_0_definicion_bd.base_datos_sqlalchemy import Base
from sqlalchemy.orm import relationship
from app.capa_0_definicion_bd.models.secretos_modelos import EstadoSecreto


class Jugador(Base):
    __tablename__ = "jugadores"

    id_jugador = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    orden_turno = Column(Integer, nullable=False)
    id_avatar = Column(Integer, nullable=False)
    id_partida = Column(Integer, ForeignKey("partidas.id_partida", use_alter=True), nullable=False)

    partida = relationship("Partida", back_populates="jugadores", foreign_keys=[id_partida])

    cartas = relationship("Carta", back_populates="jugador")

    secretos = relationship("SecretoDB", back_populates="jugador")

    sets = relationship("Set", back_populates="jugador", lazy="selectin")

    @property
    def en_desgracia_social(self) -> bool:
        """
        True si TODOS sus secretos están revelados.
        False si tiene 0 secretos o al menos uno está oculto.
        """

        secretos = getattr(self, "secretos", None) or []
        if not secretos:
            return False  # inicio de partida o sin secretos -> no en desgracia

        if EstadoSecreto is None:
            # considerar revelado si atributo 'estado' == 'revelado' y consideracion para tests
            return all(getattr(s, "estado", None) in (getattr(s, "REVELADO", "revelado"), "revelado") for s in secretos)

        return all(getattr(s, "estado", None) == EstadoSecreto.revelado for s in secretos)
