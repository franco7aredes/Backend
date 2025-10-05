from datetime import datetime, date
import random
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func

from app.db.models.partidas_models import Partida as PartidaModelo, EstadoPartida
from app.db.models.jugadores_models import Jugador as JugadorModelo
from app.capa_1_acceso_datos.repositorios.partida_contrato import IRepositorioPartida
from app.capa_1_acceso_datos.repositorios.jugador_contrato import IRepositorioJugador
from app.capa_1_acceso_datos.repositorios.carta_contrato import IRepositorioCarta
from .errores import PartidaNoEncontrada, PartidaYaEnJuego, MinimoJugadoresNoAlcanzado, MaximoJugadoresAlcanzado


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

    async def repartir_cartas(self, partida_id: int, num_cartas: int) -> Dict[str, Any]:
        """Crea el mazo de la partida y reparte `num_cartas` por jugador.

        Devuelve una estructura con las cartas repartidas por jugador y las cartas restantes en el mazo.
        Persiste los cambios usando el repositorio de cartas.
        """
        if not self.jugadores or not self.cartas:
            # Si no tenemos repositorios, no podemos operar
            return {"repartidas": {}, "mazo": []}

        partida = await self.partidas.obtener(partida_id)
        if not partida:
            return {"repartidas": {}, "mazo": []}

        jugadores = await self.jugadores.listar_por_partida(partida_id)
        if not jugadores:
            return {"repartidas": {}, "mazo": []}

        # 1..61 cartas por partida
        from app.db.models.cartas_models import Carta as CartaModelo, PosicionCarta

        mazo_cartas: List[CartaModelo] = []
        for i in range(1, 62):
            carta = CartaModelo(
                id_carta=i,
                id_partida=partida_id,
                posicion=PosicionCarta.mazo,
                id_jugador=None,
            )
            mazo_cartas.append(carta)

        random.shuffle(mazo_cartas)

        repartidas: Dict[int, List[CartaModelo]] = {}
        idx = 0
        for jugador in jugadores:
            repartidas[jugador.id_jugador] = []
            for _ in range(num_cartas):
                if idx >= len(mazo_cartas):
                    break
                carta = mazo_cartas[idx]
                carta.id_jugador = jugador.id_jugador
                carta.posicion = PosicionCarta.mano
                repartidas[jugador.id_jugador].append(carta)
                idx += 1

        cartas_restantes_mazo = mazo_cartas[idx:]

        # Persistir todas las cartas
        todas: List[CartaModelo] = []
        for lst in repartidas.values():
            todas.extend(lst)
        todas.extend(cartas_restantes_mazo)

        if todas:
            await self.cartas.crear_muchas(todas)

        # Devolver estructura como la función previa
        return {
            "repartidas": repartidas,
            "mazo": cartas_restantes_mazo,
        }

    async def asignar_turnos(self, partida_id: int, fecha_referencia: date = date(1980, 9, 15)) -> List[JugadorModelo]:
        """Ordena a los jugadores por proximidad a `fecha_referencia` y actualiza `orden_turno`.

        Devuelve la lista de jugadores ya con su turno asignado.
        """
        if not self.jugadores:
            return []

        jugadores = await self.jugadores.listar_por_partida(partida_id)
        if not jugadores:
            return []

        def diferencia_en_dias(fn: date) -> int:
            return abs((fn - fecha_referencia).days)

        jugadores_ordenados = sorted(
            jugadores,
            key=lambda j: diferencia_en_dias(j.fecha_nacimiento if isinstance(j.fecha_nacimiento, date) else j.fecha_nacimiento),
        )

        for i, jugador in enumerate(jugadores_ordenados, start=1):
            jugador.orden_turno = i

        # Persistimos los cambios de orden; usamos la sesión del repo de partidas
        if hasattr(self.partidas, "db"):
            self.partidas.db.add_all(jugadores_ordenados)  # type: ignore[attr-defined]
            await self.partidas.db.flush()  # type: ignore[attr-defined]

        return jugadores_ordenados

    async def listar_jugadores(self, partida_id: int) -> List[JugadorModelo]:
        """Devuelve los jugadores de una partida."""
        if not self.jugadores:
            return []
        return await self.jugadores.listar_por_partida(partida_id)

    async def unirse_a_partida(self, partida_id: int, nombre: str, fecha_nacimiento: datetime, id_avatar: int | None = 1) -> tuple[PartidaModelo, JugadorModelo]:
        """Agrega un jugador a la partida validando máximo y devuelve (partida, jugador)."""
        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()
        if partida.cantidad_jugadores >= partida.maximo:
            raise MaximoJugadoresAlcanzado()

        if not self.jugadores:
            raise RuntimeError("Repositorio de jugadores no disponible")

        jugador = JugadorModelo(
            id_partida=partida.id_partida,
            nombre=nombre,
            fecha_nacimiento=fecha_nacimiento.date(),
            orden_turno=0,
            id_avatar=id_avatar or 1,
        )
        jugador = await self.jugadores.crear(jugador)

        partida.cantidad_jugadores += 1
        await self.partidas.guardar(partida)
        return partida, jugador

    async def terminar_turno(self, partida_id: int, id_enviada: int) -> int:
        """Avanza el turno si el jugador que llama corresponde; devuelve el nuevo turno."""
        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()
        if partida.estado != EstadoPartida.en_juego:
            raise ValueError("partida_no_en_juego")

        # Necesitamos el jugador para validar orden_turno actual
        if not self.jugadores:
            raise RuntimeError("Repositorio de jugadores no disponible")
        jugador = await self.jugadores.obtener(id_enviada)
        if not jugador:
            raise ValueError("jugador_no_encontrado")

        if jugador.orden_turno != partida.turno_actual:
            raise PermissionError("turno_invalido")

        cantidad = partida.cantidad_jugadores
        partida.turno_actual = 1 if partida.turno_actual == cantidad else partida.turno_actual + 1
        await self.partidas.guardar(partida)
        return partida.turno_actual

    async def reponer_del_mazo(self, partida_id: int, jugador_id: int, max_cartas_en_mano: int = 6) -> Dict[str, Any]:
        """Mueve cartas del mazo a la mano del jugador.

        Retorna dict con:
        - cartas: lista de cartas movidas
        - fin_de_mazo: bool si el mazo quedó en 0
        - max_alcanzado: bool si ya tenía el máximo
        - sin_cartas: bool si no había cartas para reponer (mazo vacío)
        """
        if not self.jugadores or not self.cartas:
            return {"cartas": [], "fin_de_mazo": False, "max_alcanzado": False, "sin_cartas": True}

        jugador = await self.jugadores.obtener(jugador_id)
        if not jugador:
            raise ValueError("jugador_no_encontrado")

        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()

        if getattr(jugador, "id_partida", None) != partida_id:
            raise ValueError("jugador_no_en_partida")

        en_mano = await self.cartas.contar_en_mano(partida_id, jugador_id)
        a_reponer = max_cartas_en_mano - en_mano
        if a_reponer <= 0:
            return {"cartas": [], "fin_de_mazo": False, "max_alcanzado": True, "sin_cartas": False}

        disponibles = await self.cartas.obtener_mazo_disponible(partida_id, a_reponer)
        if not disponibles:
            # mazo vacío -> marcar partida finalizada y COMMIT inmediato (el endpoint retornará 404)
            partida.estado = EstadoPartida.Finalizada
            await self.partidas.guardar(partida)
            if hasattr(self.partidas, "db"):
                await self.partidas.db.commit()  # type: ignore[attr-defined]
            return {"cartas": [], "fin_de_mazo": True, "max_alcanzado": False, "sin_cartas": True}

        # mover a mano
        from app.db.models.cartas_models import PosicionCarta, Carta as CartaModelo
        for c in disponibles:
            c.id_jugador = jugador_id
            c.posicion = PosicionCarta.mano
        # flush cambios
        if hasattr(self.cartas, "db"):
            self.cartas.db.add_all(disponibles)  # type: ignore[attr-defined]
            await self.cartas.db.flush()  # type: ignore[attr-defined]

        # verificar si quedó el mazo en cero
        fin_de_mazo = False
        if hasattr(self.cartas, "db"):
            stmt = (
                select(func.count())
                .select_from(CartaModelo)
                .where((CartaModelo.id_partida == partida_id) & (CartaModelo.posicion == PosicionCarta.mazo) & (CartaModelo.id_jugador.is_(None)))
            )
            res = await self.cartas.db.execute(stmt)  # type: ignore[attr-defined]
            restantes = int(res.scalar() or 0)
            if restantes == 0:
                partida.estado = EstadoPartida.Finalizada
                await self.partidas.guardar(partida)
                if hasattr(self.partidas, "db"):
                    await self.partidas.db.commit()  # type: ignore[attr-defined]
                fin_de_mazo = True

        return {"cartas": disponibles, "fin_de_mazo": fin_de_mazo, "max_alcanzado": False, "sin_cartas": False}

    async def descartar_carta(self, partida_id: int, jugador_id: int) -> Optional[int]:
        """Descarta una carta de la mano del jugador. Retorna id de la carta descartada o None si no hay.
        """
        if not self.cartas:
            return None
        from app.db.models.cartas_models import Carta as CartaModelo, PosicionCarta
        if not hasattr(self.cartas, "db"):
            return None
        # buscar la primera carta del jugador en la partida
        stmt = (
            select(CartaModelo)
            .where((CartaModelo.id_partida == partida_id) & (CartaModelo.id_jugador == jugador_id))
            .limit(1)
        )
        res = await self.cartas.db.execute(stmt)  # type: ignore[attr-defined]
        carta = res.scalars().first()
        if not carta:
            return None
        carta.id_jugador = None
        carta.posicion = PosicionCarta.descarte
        self.cartas.db.add(carta)  # type: ignore[attr-defined]
        await self.cartas.db.flush()  # type: ignore[attr-defined]
        return int(carta.id_carta)

    async def obtener_cantidad_mano(self, partida_id: int, jugador_id: int) -> int:
        """Devuelve la cantidad de cartas en mano del jugador para una partida."""
        if not self.cartas:
            return 0
        return await self.cartas.contar_en_mano(partida_id, jugador_id)
