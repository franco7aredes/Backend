from datetime import datetime

from app.db.models.partidas_models import Partida as PartidaModelo, EstadoPartida
from app.db.models.jugadores_models import Jugador as JugadorModelo
from app.capa_1_acceso_datos.repositorios.partida_contrato import IRepositorioPartida


class ServicioJuego:
    """Servicio de reglas de negocio del juego.

    Expone casos de uso y no conoce detalles de SQLAlchemy ni de FastAPI.
    """

    def __init__(self, partidas: IRepositorioPartida):
        self.partidas = partidas

    async def crear_partida(self, jugador_creador: str, fecha_nac: datetime, minimo: int, maximo: int) -> tuple[PartidaModelo, JugadorModelo]:
        """Crea una partida y su jugador inicial.

        - Inicializa la partida en espera
        - Inserta el jugador creador
        - Actualiza el id_jugador_creador en la partida
        """
        nueva_partida = PartidaModelo(
            estado=EstadoPartida.en_espera,
            id_jugador_creador=0,
            cantidad_jugadores=1,
            turno_actual=1,
            minimo=minimo,
            maximo=maximo,
        )
        partida = await self.partidas.crear(nueva_partida)

        jugador = JugadorModelo(
            id_partida=partida.id_partida,
            nombre=jugador_creador,
            fecha_nacimiento=fecha_nac.date(),
            orden_turno=1,
            id_avatar=1,
        )

        # Usamos la misma sesión del repo (el commit lo maneja la dependencia de DB)
        self.partidas.db.add(jugador)  # type: ignore[attr-defined]
        await self.partidas.db.flush()  # type: ignore[attr-defined]
        await self.partidas.db.refresh(jugador)  # type: ignore[attr-defined]

        partida.id_jugador_creador = jugador.id_jugador
        await self.partidas.guardar(partida)
        return partida, jugador
