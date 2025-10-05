from datetime import datetime

from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida
from app.db.models.jugadores_models import Jugador as JugadorModel
from app.layer_1_data_access.repositories.partida_abstract import IPartidaRepository


class JuegoService:
    def __init__(self, partidas: IPartidaRepository):
        self.partidas = partidas

    async def crear_partida(self, jugador_creador: str, fecha_nac: datetime, minimo: int, maximo: int) -> tuple[PartidaModel, JugadorModel]:
        nueva_partida = PartidaModel(
            estado=EstadoPartida.en_espera,
            id_jugador_creador=0,
            cantidad_jugadores=1,
            turno_actual=1,
            minimo=minimo,
            maximo=maximo,
        )
        partida = await self.partidas.crear(nueva_partida)

        jugador = JugadorModel(
            id_partida=partida.id_partida,
            nombre=jugador_creador,
            fecha_nacimiento=fecha_nac.date(),
            orden_turno=1,
            id_avatar=1,
        )

        # Usamos la misma sesión del repo (commit es manejado por get_async_db)
        # Guardamos jugador vía la sesión del repo
        self.partidas.db.add(jugador)  # type: ignore[attr-defined]
        await self.partidas.db.flush()  # type: ignore[attr-defined]
        await self.partidas.db.refresh(jugador)  # type: ignore[attr-defined]

        partida.id_jugador_creador = jugador.id_jugador
        await self.partidas.guardar(partida)
        return partida, jugador
