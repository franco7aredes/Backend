from datetime import datetime, date
import random
from typing import Dict, Any, List, Optional, cast

from app.capa_0_definicion_bd.models.partidas_modelos import Partida as PartidaModelo, EstadoPartida
from app.capa_0_definicion_bd.models.jugadores_modelos import Jugador as JugadorModelo
from app.capa_0_definicion_bd.models.secretos_modelos import SecretoDB, EstadoSecreto, TipoSecreto
from typing import Protocol, runtime_checkable
from .errores import PartidaNoEncontrada, PartidaYaEnJuego, MinimoJugadoresNoAlcanzado, MaximoJugadoresAlcanzado
from app.capa_0_definicion_bd.models.cartas_modelos import (
    Carta as CartaModelo,
    PosicionCarta,
    TipoCarta,
)
from .resultados import (
    ReponerResultado,
    TurnoResultado,
    CrearPartidaResultado,
    RepartirCartasResultado,
    IniciarYPrepararResultado,
    DescartarResultado,
    CantidadManoResultado,
    UnirsePartidaResultado,
    IniciarPartidaResultado,
    RepartirSecretosResultado,
    ObtenerSecretosResultado,
    ObtenerDraftResultado
)
from .convertidores import partida_a_dict, jugador_a_dict


@runtime_checkable
class _RepoPartidaProto(Protocol):
    async def crear(self, partida: PartidaModelo) -> PartidaModelo: ...
    async def obtener(self, partida_id: int) -> Optional[PartidaModelo]: ...
    async def listar_en_espera(self) -> List[PartidaModelo]: ...
    async def guardar(self, partida: PartidaModelo) -> None: ...


@runtime_checkable
class _RepoJugadorProto(Protocol):
    async def listar_por_partida(self, partida_id: int) -> List[JugadorModelo]: ...
    async def crear(self, jugador: JugadorModelo) -> JugadorModelo: ...
    async def obtener(self, jugador_id: int) -> Optional[JugadorModelo]: ...


@runtime_checkable
class _RepoCartaProto(Protocol):
    async def crear_muchas(self, cartas: List[CartaModelo]) -> None: ...
    async def contar_en_mano(self, partida_id: int, jugador_id: int) -> int: ...
    async def obtener_mazo_disponible(self, partida_id: int, limite: int) -> List[CartaModelo]: ...
    async def obtener_draft(self, partida_id: int) -> List[CartaModelo]: ...


@runtime_checkable
class _RepoSecretoProto(Protocol):
    async def crear_muchos(self, secretos: List[SecretoDB]) -> None: ...
    async def obtener_secretos(self, partida_id: int, jugador_id: int) -> List[SecretoDB]: ...

class ServicioJuego:
    """Servicio de reglas de negocio del juego.

    Expone casos de uso y no conoce detalles de SQLAlchemy ni de FastAPI.
    """

    def __init__(self, partidas: _RepoPartidaProto, jugadores: _RepoJugadorProto | None = None, cartas: _RepoCartaProto | None = None, secretos: _RepoSecretoProto | None = None):
        self.partidas = partidas
        self.jugadores = jugadores
        self.cartas = cartas
        self.secretos = secretos

    async def crear_partida(self, jugador_creador: str, fecha_nac: datetime, minimo: int, maximo: int) -> CrearPartidaResultado:
        """Crea una partida y su jugador inicial (retorna CrearPartidaResultado).

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

        # Crear el jugador usando el repo correspondiente; sin repo, no tocamos la BD desde la capa 2
        if not self.jugadores:
            raise RuntimeError("Repositorio de jugadores no disponible")
        jugador = await self.jugadores.crear(jugador)

        partida.id_jugador_creador = jugador.id_jugador
        await self.partidas.guardar(partida)
        return CrearPartidaResultado(partida=partida, jugador=jugador)

    async def iniciar_partida(self, partida_id: int) -> IniciarPartidaResultado:
        """Cambia la partida a 'en_juego' validando reglas de inicio (retorna IniciarPartidaResultado)."""
        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()
        p = cast(Any, partida)
        if p.estado == EstadoPartida.en_juego:
            raise PartidaYaEnJuego()
        # Validar mínimo de jugadores
        if p.cantidad_jugadores < p.minimo:
            raise MinimoJugadoresNoAlcanzado()

        p.estado = EstadoPartida.en_juego
        await self.partidas.guardar(p)
        return IniciarPartidaResultado(partida=p)

    async def iniciar_y_preparar_partida(self, partida_id: int, cartas_por_mano: int) -> IniciarYPrepararResultado:
        """Orquestación de inicio: iniciar, repartir cartas y asignar turnos (retorna IniciarYPrepararResultado)."""
        # 1) Iniciar (valida existencia, estado y mínimo)
        iniciar_res = await self.iniciar_partida(partida_id)
        partida = iniciar_res.partida

        # 2) Repartir cartas
        datos_reparto = await self.repartir_cartas(cast(Any, partida).id_partida, cartas_por_mano)

        # tambien se reparten secretos

        secretos_repartidos = await self.repartir_secretos(partida_id)
        # 3) Asignar turnos
        jugadores_ordenados = await self.asignar_turnos(partida_id)

        return IniciarYPrepararResultado(
            partida=partida,
            repartidas=datos_reparto.repartidas,
            mazo=datos_reparto.mazo,
            jugadores=jugadores_ordenados or [],
            secretos=secretos_repartidos.secretos_repartidos,
        )

    async def listar_en_espera(self) -> list[dict]:
        """Lista partidas en estado 'en_espera' (sin exponer ORM)."""
        partidas = await self.partidas.listar_en_espera()
        return [partida_a_dict(p) for p in partidas]

    async def obtener_por_id(self, partida_id: int) -> dict | None:
        """Obtiene una partida por su id o None si no existe (dict)."""
        p = await self.partidas.obtener(partida_id)
        return partida_a_dict(p) if p else None

    async def repartir_cartas(self, partida_id: int, num_cartas: int) -> RepartirCartasResultado:
        """Crea el mazo (1..61), reparte `num_cartas` por jugador y persiste (retorna RepartirCartasResultado)."""
        if not self.jugadores or not self.cartas:
            # Si no tenemos repositorios, no podemos operar
            return RepartirCartasResultado(repartidas={}, mazo=[])

        partida = await self.partidas.obtener(partida_id)
        if not partida:
            return RepartirCartasResultado(repartidas={}, mazo=[])

        jugadores = await self.jugadores.listar_por_partida(partida_id)
        if not jugadores:
            return RepartirCartasResultado(repartidas={}, mazo=[])

        definicion: list[tuple[TipoCarta, str, int]] = [
            # Detectives (25)
            (TipoCarta.detective, "Harley Quin Wildcard", 4),
            (TipoCarta.detective, "Adriane Oliver", 3),
            (TipoCarta.detective, "Miss Marple", 3),
            (TipoCarta.detective, "Parker Pyne", 3),
            (TipoCarta.detective, "Tommy Beresford", 2),
            (TipoCarta.detective, "Lady Eileen \"Bundle\" Brent", 3),
            (TipoCarta.detective, "Tuppence Beresford", 2),
            (TipoCarta.detective, "Hercule Poirot", 3),
            (TipoCarta.detective, "Mr Satterthwaite", 2),
            # Instant (10)
            (TipoCarta.instant, "Not so fast", 10),
            # Devious (4)
            (TipoCarta.devious, "Blackmailed", 1),
            (TipoCarta.devious, "Social Faux Pas", 3),
            # Events (22)
            (TipoCarta.event, "Delay the murderer's espace!", 3),
            (TipoCarta.event, "Point your suspicions", 3),
            (TipoCarta.event, "Dead card folly", 3),
            (TipoCarta.event, "Another Victim", 2),
            (TipoCarta.event, "Look into the ashes", 3),
            (TipoCarta.event, "Card trade", 3),
            (TipoCarta.event, "And then there was one more...", 2),
            (TipoCarta.event, "Early train to paddington", 2),
            (TipoCarta.event, "Cards off the table", 1),
        ]

        mazo_cartas: List[CartaModelo] = []
        next_id = 1
        for tipo, nombre, cantidad in definicion:
            for _ in range(cantidad):
                mazo_cartas.append(
                    CartaModelo(
                        id_carta=next_id,
                        id_partida=partida_id,
                        posicion=PosicionCarta.mazo,
                        id_jugador=None,
                        nombre=nombre,
                        tipo=tipo,
                    )
                )
                next_id += 1

        # Barajar el mazo global para el reparto aleatorio
        random.shuffle(mazo_cartas)

        repartidas: Dict[int, List[CartaModelo]] = {}
        jugador_ids = [cast(Any, j).id_jugador for j in jugadores]
        for jid in jugador_ids:
            repartidas[jid] = []

        # Regla: cada jugador debe recibir obligatoriamente una carta "Not so fast" (instant)
        instants = [c for c in mazo_cartas if cast(Any, c).tipo == TipoCarta.instant]
        # Asignar una por jugador
        for jid in jugador_ids:
            if not instants:
                break  # por seguridad, aunque por definición hay 10
            carta = instants.pop()
            # remover del mazo principal
            mazo_cartas.remove(carta)
            cc = cast(Any, carta)
            cc.id_jugador = jid
            cc.posicion = PosicionCarta.mano
            repartidas[jid].append(carta)

        # Repartir el resto hasta completar num_cartas por jugador
        idx = 0
        total = len(mazo_cartas)
        for jid in jugador_ids:
            while len(repartidas[jid]) < num_cartas and idx < total:
                carta = mazo_cartas[idx]
                cc = cast(Any, carta)
                cc.id_jugador = jid
                cc.posicion = PosicionCarta.mano
                repartidas[jid].append(carta)
                idx += 1

        cartas_restantes_mazo = mazo_cartas[idx:]

        # aca voy a sacar las 3 de draft
        cartas_draft = cartas_restantes_mazo[:3]
        for carta in cartas_draft:
            carta.posicion = PosicionCarta.draft


        # Persistir todas las cartas
        todas: List[CartaModelo] = []
        for lst in repartidas.values():
            todas.extend(lst)
        todas.extend(cartas_restantes_mazo)

        if todas:
            await self.cartas.crear_muchas(todas)

        # Devolver estructura
        return RepartirCartasResultado(repartidas=repartidas, mazo=cartas_restantes_mazo)

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
            key=lambda j: diferencia_en_dias(cast(Any, j).fecha_nacimiento if isinstance(cast(Any, j).fecha_nacimiento, date) else cast(Any, j).fecha_nacimiento),
        )

        for i, jugador in enumerate(jugadores_ordenados, start=1):
            cast(Any, jugador).orden_turno = i

        # Persistimos los cambios de orden; delegamos en repos
        if self.jugadores and hasattr(self.jugadores, "guardar_muchos"):
            await self.jugadores.guardar_muchos(jugadores_ordenados)  # type: ignore[attr-defined]

        return jugadores_ordenados

    async def listar_jugadores(self, partida_id: int) -> List[dict]:
        """Devuelve los jugadores de una partida como dicts (sin exponer ORM)."""
        if not self.jugadores:
            return []
        jugadores = await self.jugadores.listar_por_partida(partida_id)
        return [jugador_a_dict(j) for j in jugadores]

    async def unirse_a_partida(self, partida_id: int, nombre: str, fecha_nacimiento: datetime, id_avatar: int | None = 1) -> UnirsePartidaResultado:
        """Agrega un jugador a la partida validando máximo y devuelve UnirsePartidaResultado."""
        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()
        p = cast(Any, partida)
        if p.cantidad_jugadores >= p.maximo:
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

        p.cantidad_jugadores += 1
        await self.partidas.guardar(p)
        return UnirsePartidaResultado(partida=p, jugador=jugador)

    async def terminar_turno(self, partida_id: int, id_enviada: int) -> TurnoResultado:
        """Avanza el turno si el jugador que llama corresponde (retorna TurnoResultado)."""
        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()
        p = cast(Any, partida)
        if p.estado != EstadoPartida.en_juego:
            raise ValueError("partida_no_en_juego")

        # Necesitamos el jugador para validar orden_turno actual
        if not self.jugadores:
            raise RuntimeError("Repositorio de jugadores no disponible")
        jugador = await self.jugadores.obtener(id_enviada)
        if not jugador:
            raise ValueError("jugador_no_encontrado")

        if cast(Any, jugador).orden_turno != p.turno_actual:
            raise PermissionError("turno_invalido")

        cantidad = p.cantidad_jugadores
        p.turno_actual = 1 if p.turno_actual == cantidad else p.turno_actual + 1
        await self.partidas.guardar(p)
        # Confirmar cambios mediado por repo
        if hasattr(self.partidas, "confirmar"):
            await self.partidas.confirmar()  # type: ignore[attr-defined]
        return TurnoResultado(turno_nuevo=int(p.turno_actual))

    async def reponer_del_mazo(self, partida_id: int, jugador_id: int, max_cartas_en_mano: int = 6) -> ReponerResultado:
        """Mueve cartas del mazo a la mano del jugador (retorna ReponerResultado: cartas, fin_de_mazo, max_alcanzado, sin_cartas)."""
        if not self.jugadores or not self.cartas:
            return ReponerResultado(cartas=[], fin_de_mazo=False, max_alcanzado=False, sin_cartas=True)

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
            return ReponerResultado(cartas=[], fin_de_mazo=False, max_alcanzado=True, sin_cartas=False)

        disponibles = await self.cartas.obtener_mazo_disponible(partida_id, a_reponer)
        if not disponibles:
            # mazo vacío -> marcar partida finalizada y COMMIT inmediato (el endpoint retornará 404)
            cast(Any, partida).estado = EstadoPartida.Finalizada
            await self.partidas.guardar(cast(Any, partida))
            if hasattr(self.partidas, "confirmar"):
                await self.partidas.confirmar()  # type: ignore[attr-defined]
            return ReponerResultado(cartas=[], fin_de_mazo=True, max_alcanzado=False, sin_cartas=True)

        # mover a mano
        for c in disponibles:
            cc = cast(Any, c)
            cc.id_jugador = jugador_id
            cc.posicion = PosicionCarta.mano
        # Persistir cambios en cartas a través del repositorio (si existe el método)
        if hasattr(self.cartas, "guardar_muchas"):
            await self.cartas.guardar_muchas(disponibles)  # type: ignore[attr-defined]

        # verificar si quedó el mazo en cero
        fin_de_mazo = False
        if hasattr(self.cartas, "contar_en_mazo"):
            restantes = await self.cartas.contar_en_mazo(partida_id)  # type: ignore[attr-defined]
            if restantes == 0:
                cast(Any, partida).estado = EstadoPartida.Finalizada
                await self.partidas.guardar(cast(Any, partida))
                if hasattr(self.partidas, "confirmar"):
                    await self.partidas.confirmar()  # type: ignore[attr-defined]
                fin_de_mazo = True
        # si no hay método contar_en_mazo, omitimos este chequeo para mantener aislado el test
        if fin_de_mazo:
            cast(Any, partida).estado = EstadoPartida.Finalizada
            await self.partidas.guardar(cast(Any, partida))
            if hasattr(self.partidas, "confirmar"):
                await self.partidas.confirmar()  # type: ignore[attr-defined]

        return ReponerResultado(cartas=disponibles, fin_de_mazo=fin_de_mazo, max_alcanzado=False, sin_cartas=False)

    async def descartar_carta(self, partida_id: int, jugador_id: int) -> DescartarResultado:
        """Descarta una carta de la mano del jugador y retorna DescartarResultado con la carta (o None si no hay)."""
        if not self.cartas:
            return DescartarResultado(carta=None)
        # buscar la primera carta del jugador en la partida mediante repo; sin repo/método, no accedemos a BD
        if hasattr(self.cartas, "obtener_primera_en_mano"):
            carta = await self.cartas.obtener_primera_en_mano(partida_id, jugador_id)  # type: ignore[attr-defined]
        else:
            return DescartarResultado(carta=None)
        if not carta:
            return DescartarResultado(carta=None)
        cc2 = cast(Any, carta)
        cc2.id_jugador = None
        cc2.posicion = PosicionCarta.descarte
        if hasattr(self.cartas, "guardar"):
            await self.cartas.guardar(cc2)  # type: ignore[attr-defined]
        # Si el repo no provee "guardar", no realizamos accesos directos a BD desde la capa 2
        return DescartarResultado(carta=carta)

    async def obtener_cantidad_mano(self, partida_id: int, jugador_id: int) -> CantidadManoResultado:
        """Devuelve la cantidad de cartas en mano del jugador para una partida (retorna CantidadManoResultado)."""
        if not self.cartas:
            return CantidadManoResultado(cantidad=0)
        cantidad = await self.cartas.contar_en_mano(partida_id, jugador_id)
        return CantidadManoResultado(cantidad=cantidad)

    async def repartir_secretos(self, partida_id: int) -> RepartirSecretosResultado:
        """ Crea los secretos de acuerdo a la cantidad de jugadores, reparte 3 a cada
        uno, y persiste (retorna RetartirSecretosResultado)"""

        if not self.jugadores or not self.cartas:
            return RepartirSecretosResultado(secretos_repartidos={})
        
        partida = await self.partidas.obtener(partida_id)
        if not partida:
            return RepartirSecretosResultado(secretos_repartidos={})

        jugadores = await self.jugadores.listar_por_partida(partida_id)
        if not jugadores:
            return RepartirSecretosResultado(secretos_repartidos={})

        mazo_secretos: List[SecretoDB] = []
        cantidad = partida.cantidad_jugadores * 3 + 1
        for i in range (1, cantidad):
            secreto = SecretoDB(
                id_secreto = i,
                id_partida = partida_id,
                id_jugador = 0,     # Necesito pasarle algo, despues lo asigno a todos
                tipo = TipoSecreto.otro,
            )
            if (i == 1):
                secreto.tipo = TipoSecreto.asesino
            if (i == 15): # Cuando hay 5 jugadores o mas, tiene que haber complice
                secreto.tipo = TipoSecreto.complice
            mazo_secretos.append(secreto)

        random.shuffle(mazo_secretos)

        repartidos: Dict[int, List[SecretoDB]] = {}
        idx = 0
        for jugador in jugadores:
            jj = cast(Any, jugador)
            repartidos[jj.id_jugador] = []
            for _ in range(3):
                if idx >= len(mazo_secretos):
                    break
                secreto = mazo_secretos[idx]
                ss = cast(Any, secreto)
                ss.id_jugador = jj.id_jugador
                repartidos[jj.id_jugador].append(secreto)
                idx += 1

        # ahora tengo que hacer la persistencia
        todos: List[SecretoDB] = []
        for lst in repartidos.values():
            todos.extend(lst)

        if todos:
            await self.secretos.crear_muchos(todos)

        return RepartirSecretosResultado(secretos_repartidos=repartidos)

    async def obtener_secretos_propios(self, partida_id: int, jugador_id: int) -> ObtenerSecretosResultado:

        """ obtengo los secretos del jugador que me interesa """
        
        jugador = await self.jugadores.obtener(jugador_id)
        if not jugador:
            raise ValueError("jugador_no_encontrado")

        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()

        if getattr(jugador,"id_partida", None) != partida_id:
            raise ValueError("jugador_no_en_partida")

        sucios = await self.secretos.obtener_secretos(partida_id, jugador_id)

        return ObtenerSecretosResultado(secretos=sucios)

    async def ver_draft(self, partida_id: int, jugador_id: int) -> ObtenerDraftResultado:


        jugador = await self.jugadores.obtener(jugador_id)
        if not jugador:
            raise ValueError("jugador_no_encontrado")
        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()

        if getattr(jugador,"id_partida", None) != partida_id:
            raise ValueError("jugador_no_en_partida")

        drafts = await self.cartas.obtener_draft(partida_id)

        return ObtenerDraftResultado(draft=drafts)
