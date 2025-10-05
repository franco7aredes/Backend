from datetime import datetime

from app.db.models.partidas_models import Partida as PartidaModelo, EstadoPartida
from app.db.models.jugadores_models import Jugador as JugadorModelo
from app.capa_1_acceso_datos.repositorios.partida_contrato import IRepositorioPartida
from app.capa_1_acceso_datos.repositorios.jugador_contrato import IRepositorioJugador
from app.capa_1_acceso_datos.repositorios.carta_contrato import IRepositorioCarta
from .errores import PartidaNoEncontrada, PartidaYaEnJuego, MinimoJugadoresNoAlcanzado


class ServicioJuego:
    """Servicio de reglas de negocio del juego.

    Expone casos de uso y no conoce detalles de SQLAlchemy ni de FastAPI.
    """

    def __init__(self, partidas: IRepositorioPartida, jugadores: IRepositorioJugador | None = None, cartas: IRepositorioCarta | None = None):
        self.partidas = partidas
        self.jugadores = jugadores
        self.cartas = cartas

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

    async def iniciar_partida(self, partida_id: int) -> PartidaModelo:
        """Cambia la partida a 'en_juego' validando reglas de inicio.
        """
        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()
        if partida.estado == EstadoPartida.en_juego:
            raise PartidaYaEnJuego()
        # Validar mínimo de jugadores
        if partida.cantidad_jugadores < partida.minimo:
            raise MinimoJugadoresNoAlcanzado()

        partida.estado = EstadoPartida.en_juego
        await self.partidas.guardar(partida)
        return partida

    async def listar_en_espera(self) -> list[PartidaModelo]:
        """Lista partidas en estado 'en_espera'."""
        return await self.partidas.listar_en_espera()

    async def obtener_por_id(self, partida_id: int) -> PartidaModelo | None:
        """Obtiene una partida por su id o None si no existe."""
        return await self.partidas.obtener(partida_id)
