from datetime import datetime, date
import random
from typing import Dict, Any, List, Optional, cast

from app.capa_0_definicion_bd.models.partidas_modelos import Partida as PartidaModelo, EstadoPartida
from app.capa_0_definicion_bd.models.jugadores_modelos import Jugador as JugadorModelo
from app.capa_0_definicion_bd.models.secretos_modelos import SecretoDB, EstadoSecreto, TipoSecreto
from app.capa_0_definicion_bd.models.sets_modelos import Set as SetModelo
from typing import Protocol, runtime_checkable
from .errores import *
from app.capa_0_definicion_bd.models.cartas_modelos import (
    Carta as CartaModelo,
    PosicionCarta,
    TipoCarta,
)

from .resultados import *
from .convertidores import partida_a_dict, jugador_a_dict
from .constantes import CARTAS_POR_MANO


@runtime_checkable
class _RepoPartidaProto(Protocol):
    async def crear(self, partida: PartidaModelo) -> PartidaModelo: ...
    async def obtener(self, partida_id: int) -> Optional[PartidaModelo]: ...
    async def listar_en_espera(self) -> List[PartidaModelo]: ...
    async def guardar(self, partida: PartidaModelo) -> None: ...
    async def confirmar(self) -> None: ...

@runtime_checkable
class _RepoJugadorProto(Protocol):
    async def listar_por_partida(self, partida_id: int) -> List[JugadorModelo]: ...
    async def crear(self, jugador: JugadorModelo) -> JugadorModelo: ...
    async def obtener(self, jugador_id: int) -> Optional[JugadorModelo]: ...
    async def eliminar(self, jugador_id: int) -> None: ...


@runtime_checkable
class _RepoCartaProto(Protocol):
    async def crear_muchas(self, cartas: List[CartaModelo]) -> None: ...
    async def contar_en_mano(self, partida_id: int, jugador_id: int) -> int: ...
    async def contar_en_mazo(self, partida_id: int) -> int: ...
    async def obtener_mazo_disponible(self, partida_id: int, limite: int) -> List[CartaModelo]: ...
    async def obtener_draft(self, partida_id: int) -> List[CartaModelo]: ...
    async def obtener_cartas_en_mano(self, partida_id: int, jugador_id: int) -> List[CartaModelo]: ...
    async def obtener_cantidad_descartadas(self, partida_id: int) -> int: ...
    async def obtener_primeras_de_descarte(self, partida_id: int) -> List[CartaModelo]: ...
    async def obtener_carta(self, partida_id: int, jugador_id: int, carta_id: int) -> CartaModelo: ...
    async def obtener_draft_disponible(self, partida_id: int, carta_id: int) -> List[CartaModelo]: ...
    async def mover_primera_carta_mazo_a_draft(self, partida_id: int) -> Optional[CartaModelo]: ...
    async def guardar_muchas(self, cartas: List[CartaModelo]) -> None: ...
    async def obtener_primeras_de_mazo(self, partida_id: int) -> List[CartaModelo]: ...
    async def obtener_carta_id(self, partida_id: int, carta_id: int) -> CartaModelo: ... 

@runtime_checkable
class _RepoSecretoProto(Protocol):
    async def crear_muchos(self, secretos: List[SecretoDB]) -> None: ...
    async def obtener_secretos(self, partida_id: int, jugador_id: int) -> List[SecretoDB]: ...
    async def obtener_secreto_asesino(self, partida_id: int) -> SecretoDB: ...
    async def contar_secretos_jugador(self, partida_id: int, jugador_id: int) -> int: ...
    async def obtener_secretos_revelados(self, partida_id: int) -> List[SecretoDB]: ...
    async def guardar(self, secreto: SecretoDB) -> None: ...
    async def obtener_secreto(self, partida_id: int, jugador_id: int, secreto_id: int) -> Optional[SecretoDB]: ...
    async def obtener_secreto_revelado(self, partida_id: int, jugador_id: int, secreto_id: int) -> SecretoDB: ...

@runtime_checkable
class _RepoSetProto(Protocol):
    async def crear_set(self, set: SetModelo) -> SetModelo: ...
    async def obtener_set_por_id(self, set_id: int) -> Optional[SetModelo]: ...
    async def guardar_set(self, set: SetModelo) -> None: ...
    async def obtener_cartas_del_set(self, set_id: int) -> List[CartaModelo]: ...


class ServicioJuego:
    """Servicio de reglas de negocio del juego.

    Expone casos de uso y no conoce detalles de SQLAlchemy ni de FastAPI.
    """

    def __init__(self, partidas: _RepoPartidaProto, jugadores: _RepoJugadorProto | None = None, cartas: _RepoCartaProto | None = None, secretos: _RepoSecretoProto | None = None, sets: _RepoSetProto | None = None):
        self.partidas = partidas
        self.jugadores = jugadores
        self.cartas = cartas
        self.secretos = secretos
        self.sets = sets

    async def crear_partida(self, jugador_creador: str, fecha_nac: datetime, minimo: int, maximo: int, avatar_id: int) -> CrearPartidaResultado:
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
            id_avatar=avatar_id,
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
        if not self.partidas:
            return []
        partidas = await self.partidas.listar_en_espera()
        return [partida_a_dict(p) for p in partidas]

    async def obtener_por_id(self, partida_id: int) -> dict | None:
        """Obtiene una partida por su id o None si no existe (dict)."""
        if not self.partidas:
            return None
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
        # Asignar orden en el mazo
        for i, carta in enumerate(mazo_cartas):
            carta.orden_en_mazo = i + 1 

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
            cc.orden_en_mazo = None  # limpiar orden
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
                cc.orden_en_mazo = None  # limpiar orden
                repartidas[jid].append(carta)
                idx += 1

        cartas_restantes_mazo = mazo_cartas[idx:]

        # aca voy a sacar las 3 de draft
        cartas_draft = cartas_restantes_mazo[:3]
        for carta in cartas_draft:
            carta.posicion = PosicionCarta.draft
            carta.orden_en_mazo = None  # limpiar orden


        # Persistir todas las cartas
        todas: List[CartaModelo] = []
        for lst in repartidas.values():
            todas.extend(lst)
        todas.extend(cartas_restantes_mazo)

        if todas:
            await self.cartas.crear_muchas(todas)

        # Devolver estructura
        return RepartirCartasResultado(repartidas=repartidas, mazo=cartas_restantes_mazo)

    async def asignar_turnos(self, partida_id: int, fecha_referencia: date = date(1890, 9, 15)) -> List[JugadorModelo]:
        """Ordena a los jugadores por proximidad a `fecha_referencia` y actualiza `orden_turno`.

        Devuelve la lista de jugadores ya con su turno asignado.
        """
        if not self.jugadores:
            return []

        jugadores = await self.jugadores.listar_por_partida(partida_id)
        if not jugadores:
            return []

        def diferencia_en_dias(fn: date) -> int:
            """
            Calcula una clave de ordenacion que representa la distancia del cumple a la fecha de
            referencia en un ciclo de 365 dias.
            La clave mas chica tiene mas prioridad
            """
            # creo la fecha de cumple en el mismo año que la de Agatha
            cumple= date(
                fecha_referencia.year,
                fn.month,
                fn.day
            )

            # Calculo las dos posibles distancias: la directa y la circular(del año siguiente, y el previo)
            diff_directa = (cumple - fecha_referencia).days

            cumple_circular = date(
                fecha_referencia.year + 1,
                fn.month,
                fn.day
            )
            diff_circular = (cumple_circular - fecha_referencia).days

            cumple_circular_previo = date(
                fecha_referencia.year - 1,
                fn.month,
                fn.day
            )

            diff_circular_previa = (cumple_circular_previo - fecha_referencia).days

            # Las juntamos, y tomamos el valor absoluto minimo

            distancias = [abs(diff_directa), abs(diff_circular), abs(diff_circular_previa)]

            dist_minima = min(distancias)

            return dist_minima


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

    async def reponer_del_mazo(self, partida_id: int, jugador_id: int, max_cartas_en_mano: int = CARTAS_POR_MANO) -> ReponerResultado:
        """Mueve una carta del mazo regular a la mano del jugador (retorna ReponerResultado: cartas, fin_de_mazo, max_alcanzado, sin_cartas)."""
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

        # Ahora obtenemos una sola carta del mazo, no cambiamos el resto para mantener facilidad de modificacion a futuro.
        disponibles = await self.cartas.obtener_mazo_disponible(partida_id, 1)
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
            cc.orden_en_mazo = None
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

    async def descartar_carta(self, partida_id: int, jugador_id: int, carta_id: int) -> DescartarResultado:
        """Descarta una carta de la mano del jugador y retorna DescartarResultado con la carta (o None si no hay)."""
        if not self.cartas:
            return DescartarResultado(carta=None)
        # buscar la carta del jugador en la partida 
        if hasattr(self.cartas, "obtener_carta"):
            carta = await self.cartas.obtener_carta(partida_id, jugador_id, carta_id)  # type: ignore[attr-defined]
        else:
            return DescartarResultado(carta=None)
        if not carta:
            return DescartarResultado(carta=None)
        # Antes, necesito saber cuantas cartas hay en en el mazo de descarte
        cantidad_descartadas = await self.cartas.obtener_cantidad_descartadas(partida_id)

        cc2 = cast(Any, carta) 
        cc2.id_jugador = None
        cc2.posicion = PosicionCarta.descarte
        cc2.orden_en_descarte = cantidad_descartadas + 1
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

    async def obtener_cantidad_cartas_en_mazo(self, partida_id: int) -> CantidadMazoResultado:
        if not self.cartas:
            return CantidadMazoResultado(cantidad=0)
        cantidad = await self.cartas.contar_en_mazo(partida_id)
        return CantidadMazoResultado(cantidad=cantidad)

    async def repartir_secretos(self, partida_id: int) -> RepartirSecretosResultado:
        """ Crea los secretos de acuerdo a la cantidad de jugadores, reparte 3 a cada
        uno, y persiste (retorna RetartirSecretosResultado)"""

        if not self.jugadores or not self.cartas or not self.secretos:
            return RepartirSecretosResultado(secretos_repartidos={})
        
        partida = await self.partidas.obtener(partida_id)
        if not partida:
            return RepartirSecretosResultado(secretos_repartidos={})

        jugadores = await self.jugadores.listar_por_partida(partida_id)
        if not jugadores:
            return RepartirSecretosResultado(secretos_repartidos={})

        mazo_secretos: List[SecretoDB] = []
        cantidad = partida.cantidad_jugadores * 3 
        for i in range (1, 18):
            secreto = SecretoDB(
                id_secreto = i,
                id_partida = partida_id,
                id_jugador = 0,     # Necesito pasarle algo, despues lo asigno a todos
                tipo = TipoSecreto.otro,
            )
            if (i == 1):
                secreto.tipo = TipoSecreto.asesino
            if (i == 15): 
                secreto.tipo = TipoSecreto.complice
            mazo_secretos.append(secreto)

        asesino = [s for s in mazo_secretos if s.tipo == TipoSecreto.asesino][0]
        complice = [s for s in mazo_secretos if s.tipo == TipoSecreto.complice][0]
        otros = [s for s in mazo_secretos if s.tipo == TipoSecreto.otro]

        secretos_a_repartir: List[SecretoDB] = []
        secretos_a_repartir.append(asesino)

        if partida.cantidad_jugadores >= 5: # Cuando hay 5 jugadores o mas, tiene que haber complice

            secretos_a_repartir.append(complice)

        # Calculo cuantos secretos de los otros tengo que agregar
        necesarios_otros = cantidad - len(secretos_a_repartir)

        random.shuffle(otros)

        # Por seguridad, no tomamos mas secretos de los que hay
        necesarios_otros = min(necesarios_otros, len(otros))

        secretos_a_repartir.extend(otros[:necesarios_otros])

        # Barajeo todos los secretos a repartir

        random.shuffle(secretos_a_repartir)
        
        repartidos: Dict[int, List[SecretoDB]] = {}
        idx = 0
        for jugador in jugadores:
            jj = cast(Any, jugador)
            repartidos[jj.id_jugador] = []
            for _ in range(3):
                if idx >= len(secretos_a_repartir):
                    break
                secreto = secretos_a_repartir[idx]
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
        """Obtiene los secretos del jugador. Si no hay partida, devuelve vacío (compat con tests)."""
        if not getattr(self, "secretos", None):
            return ObtenerSecretosResultado(secretos=[])

        jugador = await self.jugadores.obtener(jugador_id)
        if not jugador:
            raise ValueError("jugador_no_encontrado")

        partida = await self.partidas.obtener(partida_id)
        if not partida:
            # compatibilidad con test_obtener_secretos_propios_cero
            return ObtenerSecretosResultado(secretos=[])

        if getattr(jugador, "id_partida", None) != partida_id:
            raise ValueError("jugador_no_en_partida")

        sucios = await self.secretos.obtener_secretos(partida_id, jugador_id)
        return ObtenerSecretosResultado(secretos=sucios or [])
    
    
    async def obtener_cartas_propias(self, partida_id: int, jugador_id: int) -> ObtenerCartasResultado:
        """Obtiene las cartas en mano del jugador en esta partida."""
        if not self.jugadores or not self.cartas:
            return ObtenerCartasResultado(cartas=[])

        jugador = await self.jugadores.obtener(jugador_id)
        if jugador is None:
            raise ValueError("jugador_no_encontrado")

        partida = await self.partidas.obtener(partida_id)
        if partida is None:
            raise PartidaNoEncontrada()

        if getattr(jugador, "id_partida", None) != partida_id:
            raise ValueError("jugador_no_en_partida")

        cartas = await self.cartas.obtener_cartas_en_mano(partida_id, jugador_id)
        return ObtenerCartasResultado(cartas=cartas)

    async def ver_del_descarte(self, partida_id: int, jugador_id: int) -> VerDescarteResultado:
        """ obtiene las cartas que estan mas arriba del mazo de descarte,
         las 5 (o menos) que esten mas arriba """
         
        if not self.jugadores or not self.cartas:
            return VerDescarteResultado(descarte=[])
         
        jugador = await self.jugadores.obtener(jugador_id)
        if jugador is None:
            raise ValueError("jugador_no_encontrado")

        partida = await self.partidas.obtener(partida_id)
        if partida is None:
            raise PartidaNoEncontrada()

        if getattr(jugador, "id_partida", None) != partida_id:
            raise ValueError("jugador_no_en_partida")

        descartadas = await self.cartas.obtener_primeras_de_descarte(partida_id)

        return VerDescarteResultado(descarte=descartadas)
    

    async def obtener_cantidad_manos(self, partida_id: int) -> CantidadManosResultado:
        """Devuelve la cantidad de cartas en mano de cada jugador para una partida"""
        if not self.cartas or not self.jugadores:
            return CantidadManosResultado(cartas_por_jugador={})
        
        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()
        
        jugadores = await self.jugadores.listar_por_partida(partida_id)
        if not jugadores:
            return CantidadManosResultado(cartas_por_jugador={})
        
        cantidades: Dict[int, int] = {}
        for jugador in jugadores:
            jj = cast(Any, jugador)
            cantidad = await self.cartas.contar_en_mano(partida_id, jj.id_jugador)
            cantidades[jj.id_jugador] = cantidad

        return CantidadManosResultado(cartas_por_jugador=cantidades)


    async def obtener_asesino(self, partida_id: int) -> AsesinoResultado:
        if not self.secretos:
            raise AsesinoNoEncontrado()
        
        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()

        secreto = await self.secretos.obtener_secreto_asesino(partida_id)
        if not secreto:
            raise AsesinoNoEncontrado()
            
        return AsesinoResultado(asesino=secreto.id_jugador)

      
    async def obtener_cantidad_secretos(self, partida_id: int) -> CantidadSecretosResultado:
        """Devuelve la cantidad de secretos en mano de cada jugador para una partida"""
        if not self.secretos or not self.jugadores:
            return CantidadSecretosResultado(secretos_por_jugador={})

        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()
        
        jugadores = await self.jugadores.listar_por_partida(partida_id)
        if not jugadores:
            return CantidadSecretosResultado(secretos_por_jugador={})
        
        cantidades: Dict[int, int] = {}
        for jugador in jugadores:
            jj = cast(Any, jugador)
            cantidad = await self.secretos.contar_secretos_jugador(partida_id, jj.id_jugador)
            cantidades[jj.id_jugador] = cantidad

        return CantidadSecretosResultado(secretos_por_jugador=cantidades)

      

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


    async def preparar_set(self, partida_id: int, jugador_id: int, cartas_id: list[int]) -> JugarSetResultado:
        jugador = await self.jugadores.obtener(jugador_id)
        if not jugador:
            raise ValueError("jugador no encontrado")
        
        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()

        if getattr(jugador, "en_desgracia_social", False):
            raise JugadorEnDesgraciaSocial()

        cartas_en_mano = await self.cartas.obtener_cartas_en_mano(partida_id, jugador_id)
        if not cartas_en_mano:
            raise ValueError("Cartas no encontradas")
        cartas_seleccionadas = [c for c in cartas_en_mano if c.id_carta in cartas_id]

        if len(cartas_seleccionadas) != len(cartas_id):
            raise ValueError("Algunas cartas no estan en la mano del jugador")
        
        if not (2 <= len(cartas_seleccionadas) <= 3):
            raise ValueError("Un set debe tener 2 o 3 cartas")
        
        if any(carta.tipo != TipoCarta.detective for carta in cartas_seleccionadas):
            raise ValueError("Todas las cartas deben ser de tipo detective")
        
        if any(carta.nombre == "Adriane Oliver" for carta in cartas_seleccionadas):
            raise ValueError("La carta Adriane Oliver no puede ser jugada como parte de un set")
        
        nombres = [carta.nombre for carta in cartas_seleccionadas]
        comodines = [n for n in nombres if n == "Harley Quin Wildcard"]
        normales = [n for n in nombres if n != "Harley Quin Wildcard"]

        if len(comodines) > 2:
            raise ValueError("No se permiten más de 2 comodines por set")

        if len(normales) == 0:
            raise ValueError("No se puede formar un set solo con comodines")
        
        # Detectives que requieren 3 cartas
        requiere_3 = {"Miss Marple", "Hercule Poirot"}
        total = len(normales) + len(comodines)
        

        # Caso especial: Beresford
        beresford = {"Tommy Beresford", "Tuppence Beresford"}
        if set(normales).issubset(beresford):
            if total == 2:
                nombre_set = "Beresford"
            else:
                raise ValueError("Los sets de Beresford solo pueden tener 2 cartas")

        # Caso general
        elif all(n == normales[0] for n in normales):
            detective = normales[0]
            if detective in requiere_3 and total == 3:
                nombre_set = detective
            elif detective not in requiere_3 and total == 2:
                nombre_set = detective
            else:
                raise ValueError(f"El detective {detective} requiere {'3' if detective in requiere_3 else '2'} cartas para formar un set")

        else:
            raise ValueError("Las cartas no son compatibles para formar un set")
        
        # Crear el set y asociar cartas
        nuevo_set = SetModelo(
            id_partida=partida_id,
            id_jugador=jugador_id,
            nombre=nombre_set
        )

        set_creado = await self.sets.crear_set(nuevo_set)
        if not set_creado: 
            raise ValueError("Set no creado")

        for carta in cartas_seleccionadas:
            carta.id_set = nuevo_set.id_set
            carta.posicion = PosicionCarta.set

        return JugarSetResultado(set=set_creado)

    async def reponer_del_draft(self, partida_id: int, jugador_id: int, carta_id: int, max_cartas_en_mano: int = CARTAS_POR_MANO) -> ReponerResultado:
        """Mueve una carta del draft a la mano del jugador (retorna ReponerResultado: cartas, fin_de_mazo, max_alcanzado, sin_cartas).
        Al igual que reponer_del_mazo, no modificamos la logica para mantener adaptabilidad a futuro, y poder devolver mas de una carta si fuese necesario."""
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

        disponibles = await self.cartas.obtener_draft_disponible(partida_id, carta_id)
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

        # Reponer el draft con la primera carta del mazo
        if hasattr(self.cartas, "mover_primera_carta_mazo_a_draft"):
            await self.cartas.mover_primera_carta_mazo_a_draft(partida_id)

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

    async def robar_set(self, partida_id: int, jugador_id: int, set_id: int) -> RobarSetResultado:
        """Permite a un jugador robar un set de otro jugador."""
        if not self.sets or not self.cartas:
            raise ValueError("Repositorio de sets o cartas no disponible")

        jugador = await self.jugadores.obtener(jugador_id)
        if not jugador:
            raise JugadorNoEncontrado()

        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()

        if getattr(jugador, "id_partida", None) != partida_id:
            raise JugadorNoEnPartida()

        set_a_robar = await self.sets.obtener_set_por_id(set_id)
        if not set_a_robar:
            raise SetNoEncontrado()

        if getattr(set_a_robar, "id_partida", None) != partida_id:
            raise SetNoEnPartida()

        if getattr(set_a_robar, "id_jugador", None) == jugador_id:
            raise NoPuedeRobarSuPropioSet()

        # Transferir el set al jugador que roba
        setattr(set_a_robar, "id_jugador", jugador_id)
        await self.sets.guardar_set(set_a_robar)

        # Actualizar las cartas asociadas al set (puede devolver vacio para compatibilidad con tests)
        cartas_del_set = await self.sets.obtener_cartas_del_set(set_id) or []
        for carta in cartas_del_set:
            carta.id_jugador = jugador_id
        if hasattr(self.cartas, "guardar_muchas"):
            await self.cartas.guardar_muchas(cartas_del_set)  # type: ignore[attr-defined]

        return RobarSetResultado(set=set_a_robar)

    async def revelar_secreto(self, partida_id: int, jugador_id: int, secreto_id: int) -> RevelarSecretoResultado:
        jugador = await self.jugadores.obtener(jugador_id)
        if not jugador:
            raise JugadorNoEncontrado()

        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()

        if getattr(jugador, "id_partida", None) != partida_id:
            raise JugadorNoEnPartida()
        
        secreto = await self.secretos.obtener_secreto(partida_id, jugador_id, secreto_id)
        if not secreto:
            raise SecretoNoEncontrado()
        
        if getattr(secreto, "estado", None) != EstadoSecreto.oculto:
            raise SecretoNoDisponible()
        
        previo_en_desgracia = getattr(jugador, "en_desgracia_social", False)

        secreto.estado = EstadoSecreto.revelado
        # Ahora actualizo la base de datos
        self.secretos.guardar(secreto)

        # ahora, manejo el caso en que se revela el asesino
        if secreto.tipo == TipoSecreto.asesino:
            partida.estado = EstadoPartida.Finalizada
            await self.partidas.guardar(partida)
            # lo voy a manejar como una excepcion
            raise AsesinoRevelado()
        
        # Recalcula (el secreto ya está modificado en memoria)
        posterior_en_desgracia = getattr(jugador, "en_desgracia_social", False)
        # Si no estaba y ahora todos revelados -> entra en desgracia
        if (not previo_en_desgracia) and posterior_en_desgracia:
            raise JugadorEnDesgraciaSocial()

        return RevelarSecretoResultado(secreto=secreto)


    async def robar_secreto(self, partida_id: int, jugador_id: int, secreto_id: int) -> RobarSecretoResultado:

        jugador = await self.jugadores.obtener(jugador_id)
        if not jugador:
            raise JugadorNoEncontrado()

        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()

        if getattr(jugador, "id_partida", None) != partida_id:
            raise JugadorNoEnPartida()

        secreto = await self.secretos.obtener_secreto_revelado(partida_id, secreto_id)
        if not secreto:
            raise SecretoNoEncontrado()
        
        if getattr(secreto, "estado", None) != EstadoSecreto.revelado:
            raise SecretoNoDisponible()

        previo_en_desgracia = getattr(jugador, "en_desgracia_social", False)

        secreto.estado = EstadoSecreto.oculto
        secreto.id_jugador = jugador_id

        # Ahora actualizo la base de datos
        self.secretos.guardar(secreto)

        posterior_en_desgracia = getattr(jugador, "en_desgracia_social", False)
        # Si estaba en desgracia y ahora ya no (tiene oculto) -> sale
        if previo_en_desgracia and (not posterior_en_desgracia):
            raise JugadorSaleDeDesgraciaSocial()
        
        return RevelarSecretoResultado(secreto=secreto)
    
    async def abandonar_partida(self, partida_id: int, jugador_id: int) -> AbandonarPartidaResultado:
        """Permite a un jugador abandonar la partida."""

        jugador = await self.jugadores.obtener(jugador_id)
        if not jugador:
            raise JugadorNoEncontrado()

        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()

        if getattr(jugador, "id_partida", None) != partida_id:
            raise JugadorNoEnPartida()

        if partida.estado == EstadoPartida.en_juego:
            raise PartidaEnJuegoNoAbandonable()

        if partida.id_jugador_creador != jugador_id:
            # "Eliminamos" al jugador de la Bd partida
            if partida.cantidad_jugadores > 1:
                partida.cantidad_jugadores -= 1
                if hasattr(self.partidas, "confirmar"):
                    await self.partidas.confirmar()
            # Eliminamos efectivamente al jugador en la BD de Jugadores
                await self.jugadores.eliminar(jugador_id)
        else:
            raise CreadorNoPuedeAbandonarPartida()

        return AbandonarPartidaResultado(partida_id=partida_id,
                                          jugador_id=jugador_id,
                                          cantidad_jugadores=partida.cantidad_jugadores)


    async def ocultar_secreto(self, partida_id: int, jugador_id: int, secreto_id: int) -> OcultarSecretoResultado:
        jugador = await self.jugadores.obtener(jugador_id)
        if not jugador:
            raise JugadorNoEncontrado()

        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()

        if getattr(jugador, "id_partida", None) != partida_id:
            raise JugadorNoEnPartida()
        
        secreto = await self.secretos.obtener_secreto(partida_id, jugador_id, secreto_id)
        if not secreto:
            raise SecretoNoEncontrado()
        
        if getattr(secreto, "estado", None) != EstadoSecreto.revelado:
            raise SecretoNoDisponible()
        
        previo_en_desgracia = getattr(jugador, "en_desgracia_social", False)
        
        secreto.estado = EstadoSecreto.oculto
        # Ahora actualizo la base de datos
        self.secretos.guardar(secreto)

        posterior_en_desgracia = getattr(jugador, "en_desgracia_social", False)
        if previo_en_desgracia and (not posterior_en_desgracia):
            raise JugadorSaleDeDesgraciaSocial()


        return OcultarSecretoResultado(secreto=secreto)
      
    async def verificar_seleccionar_jugador_set(self, partida_id: int, jugador_id: int, set_id: int, id_seleccionado: int, posicion_secreto: Optional[int]= None) -> None:
        """ Verifica que un jugador pueda seleccionar a otro jugador para aplicarle el efecto de un set.
            Levanta excepciones en caso de error."""
        
        jugador = await self.jugadores.obtener(jugador_id)
        if not jugador:
            raise JugadorNoEncontrado()

        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()

        if getattr(jugador, "id_partida", None) != partida_id:
            raise JugadorNoEnPartida()

        set = await self.sets.obtener_set_por_id(set_id)
        if not set:
            raise SetNoEncontrado()

        if getattr(set, "id_partida", None) != partida_id:
            raise SetNoEnPartida()

        if getattr(set, "id_jugador", None) == id_seleccionado or set.nombre == "Parker Pyne":
            raise NoPuedeAplicarseEfectosAsiMismo()

        jugador_seleccionado = await self.jugadores.obtener(id_seleccionado)
        if not jugador_seleccionado:
            raise JugadorNoEncontrado()

        if getattr(jugador_seleccionado, "id_partida", None) != partida_id:
            raise JugadorNoEnPartida()

        if getattr(set, "id_jugador", None) != jugador_id:
            raise SetNoCorrespondeAlJugadorSeleccionado()
        
        match set.nombre:
            case "Miss Marple" | "Hercule Poirot":
                if posicion_secreto is None:
                    raise PosicionSecretoNoProporcionada()
                
            case "Mr Satterthwaite":
                if posicion_secreto is not None:
                    raise SetNoSoportaSeleccionDeJugador()
                
            case "Parker Pyne":
                if posicion_secreto is None:
                    raise PosicionSecretoNoProporcionada()
                
            case "Lady Eileen \"Bundle\" Brent":
                if posicion_secreto is not None:
                    raise SetNoSoportaSeleccionDeJugador()
                
            case "Beresford":
                if posicion_secreto is not None:
                    raise SetNoSoportaSeleccionDeJugador()

        secretos = await self.secretos.obtener_secretos(partida_id, id_seleccionado)
        if not secretos:
            raise SecretoNoEncontrado()

        if posicion_secreto is not None:
            largo = await self.secretos.contar_secretos_jugador(partida_id, id_seleccionado)
            if posicion_secreto < 0 or posicion_secreto > largo - 1:
                raise SecretoNoEncontrado()


    async def descartar_not_so_fast(self, partida_id: int, jugador_id: int) -> NotsoFastResultado:
        jugador = await self.jugadores.obtener(jugador_id)
        if not jugador:
            raise JugadorNoEncontrado()

        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()
        
        if getattr(jugador, "id_partida", None) != partida_id:
            raise JugadorNoEnPartida()
        
        cartas = await self.cartas.obtener_cartas_en_mano(partida_id, jugador_id)
        if not cartas:
            raise ValueError("Cartas no encontradas")
        
        cartas_a_descartar = [
        carta for carta in cartas
        if carta.nombre == "Not so fast" and carta.tipo == TipoCarta.instant
        ]

        if not cartas_a_descartar:
            return NotsoFastResultado(carta=[])

        cantidad_descartadas = await self.cartas.obtener_cantidad_descartadas(partida_id)

        for i, carta in enumerate(cartas_a_descartar, start=1):
            carta.posicion = PosicionCarta.descarte
            carta.id_jugador = None
            carta.orden_en_descarte = cantidad_descartadas + i
            await self.cartas.guardar(carta)

        return NotsoFastResultado(carta=cartas_a_descartar)
    
    async def preparar_evento(self, partida_id: int, jugador_id: int, carta_id: int, carta_descarte: Optional[int] = None, secreto_id: Optional[int] = None, jugador_objetivo_id: Optional[int] = None, set_id: Optional[int] = None) -> EventoResultado:
        jugador = await self.jugadores.obtener(jugador_id)
        if not jugador:
            raise JugadorNoEncontrado()

        if getattr(jugador, "en_desgracia_social", False):
            raise JugadorEnDesgraciaSocial()

        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()
        
        if getattr(jugador, "id_partida", None) != partida_id:
            raise JugadorNoEnPartida()
        
        
        carta = await self.cartas.obtener_carta(partida_id, jugador_id, carta_id)
        if not carta:
            raise ValueError("Carta no encontrada")
        
        if carta.tipo != TipoCarta.event:
            raise CartaNoEsEvento()
            
        nombre = carta.nombre.lower().strip()
        
        match nombre:
            case "cards off the table":
                resultado = await self.descartar_not_so_fast(partida_id, jugador_objetivo_id)
                descartado = await self.descartar_carta(partida_id, jugador_id, carta.id_carta)
                if not resultado.carta:
                    return EventoResultado(tipo_evento="Cards off the table", cartas_descartadas=[], mensaje="El jugador no tiene cartas Not so Fast para descartar", carta_evento_descartada=descartado.carta)
    
                return EventoResultado(tipo_evento="Cards off the table", cartas_descartadas=resultado.carta, mensaje=f"{len(resultado.carta)} cartas descartadas del jugador objetivo", carta_evento_descartada=descartado.carta)

            case "another victim":
                try:
                    robado = await self.robar_set(partida_id, jugador_id, set_id)
                except SetNoEncontrado:
                    descartado = await self.descartar_carta(partida_id, jugador_id, carta.id_carta)
                    return EventoResultado(tipo_evento="Another Victim", mensaje="No se pudo robar el set", carta_evento_descartada=descartado.carta)

                descartado = await self.descartar_carta(partida_id, jugador_id, carta.id_carta)
                return EventoResultado(tipo_evento="Another Victim", set_robado=robado.set, mensaje="Se robo un set con exito", carta_evento_descartada=descartado.carta)

            case "look into the ashes":
                if not carta_descarte:
                    raise ValueError("Debe especificarse una carta del descarte para este evento")
                
                carta_objetivo = await self.cartas.obtener_carta_id(partida_id, carta_descarte)
                if not carta_objetivo or carta_objetivo.posicion != PosicionCarta.descarte:
                    raise ValueError("La carta seleccionada no esta en el descarte")
                
                carta_objetivo.posicion = PosicionCarta.mano
                carta_objetivo.id_jugador = jugador_id
                carta_objetivo.orden_en_descarte = None
                await self.cartas.guardar(carta_objetivo)

                descartado = await self.descartar_carta(partida_id, jugador_id, carta.id_carta)

                return EventoResultado(tipo_evento="Look Into The Ashes", cartas_agregadas=[carta_objetivo], mensaje=f"La carta {carta_objetivo.id_carta} fue recuperada del descarte", carta_evento_descartada=descartado.carta)

            case "and then there was one more...":
                try:
                    robado = await self.robar_secreto(partida_id, jugador_objetivo_id, secreto_id)
                except (JugadorEnDesgraciaSocial, JugadorSaleDeDesgraciaSocial) as e:
                    # Intentar adjuntar contexto si es posible; si no, relanzar tal cual
                    try:
                        secreto_ctx, posicion_ctx = await self._obtener_secreto_y_posicion(partida_id, jugador_objetivo_id, secreto_id)
                        raise self._adjuntar_ctx_desgracia(e, secreto=secreto_ctx, posicion=posicion_ctx, partida_id=partida_id, jugador_id=jugador_objetivo_id)
                    except Exception:
                        raise e
                if not robado:
                    return EventoResultado(tipo_evento="And Then There Was One More...", mensaje="No se pudo ocultar el secreto")
                descartado = await self.descartar_carta(partida_id, jugador_id, carta.id_carta)
                secreto_final = getattr(robado, "secreto", None)
                return EventoResultado(
                    tipo_evento="And Then There Was One More...",
                    secreto_oculto=secreto_final,
                    mensaje=f"Se ocultó el secreto {getattr(secreto_final,'id_secreto', None)}",
                    carta_evento_descartada=descartado.carta,
                    jugador_que_recibe_secreto=jugador_objetivo_id
                )

            case "delay the murderer's espace!":
                resultado = await self.ver_del_descarte(partida_id, jugador_id)
                cartas_descarte = resultado.descarte
                if not cartas_descarte:
                    descartado = await self.descartar_carta(partida_id, jugador_id, carta.id_carta)
                    return EventoResultado(tipo_evento="Delay the murderer's espace!", mensaje="No hay cartas para reintegrar al mazo", carta_evento_descartada=descartado.carta)

                ultimo_orden_mazo = await self.cartas.contar_en_mazo(partida_id)

                for i, c in enumerate(cartas_descarte, start=1):
                    c.posicion = PosicionCarta.mazo
                    c.id_jugador = None
                    c.orden_en_descarte = None
                    c.orden_en_mazo = ultimo_orden_mazo + i
                    await self.cartas.guardar(c)

                # descartar la carta que activo el evento
                descartado = await self.descartar_carta(partida_id, jugador_id, carta.id_carta)

                return EventoResultado(tipo_evento="Delay the murderer's espace!", cartas_agregadas=cartas_descarte, mensaje=f"{len(cartas_descarte)} cartas fueron reintegradas al mazo", carta_evento_descartada=descartado.carta)

            case "early train to paddington":
                # obtener todas las cartas disponibles en el mazo (hasta 6)
                cartas_a_mover = await self.cartas.obtener_primeras_de_mazo(partida_id)
                if not cartas_a_mover:
                    return EventoResultado(tipo_evento="Early Train To Paddington", mensaje="No hay cartas en el mazo para mover al descarte")
                
                # obtener el orden actual del descarte
                cantidad_en_descarte = await self.cartas.obtener_cantidad_descartadas(partida_id)

                # mover las cartas al descarte
                for i, c in enumerate(cartas_a_mover, start=1):
                    c.posicion = PosicionCarta.descarte
                    c.id_jugador = None
                    c.orden_en_mazo = None
                    c.orden_en_descarte = cantidad_en_descarte + i
                    await self.cartas.guardar(c)

                # descartar la carta que aplica el evento
                carta.posicion = PosicionCarta.descarte
                carta.id_jugador = None
                carta.orden_en_descarte = cantidad_en_descarte + len(cartas_a_mover) + 1
                await self.cartas.guardar(carta)

                mensaje = f"{len(cartas_a_mover)} cartas fueron movidas del mazo al descarte"

                fin_de_mazo = False
                asesino_id = None
                if hasattr(self.cartas, "contar_en_mazo"):
                    restantes = await self.cartas.contar_en_mazo(partida_id) 
                    if restantes == 0:
                        cast(Any, partida).estado = EstadoPartida.Finalizada
                        await self.partidas.guardar(cast(Any, partida))
                        if hasattr(self.partidas, "confirmar"):
                            await self.partidas.confirmar()  
                            mensaje += ". El asesino ha ganado. La partida ha finalizado."
                            fin_de_mazo = True

                            asesino_resultado = await self.obtener_asesino(partida_id)
                            asesino_id = asesino_resultado.asesino

                return EventoResultado(tipo_evento="Early Train To Paddington", cartas_descartadas=cartas_a_mover, mensaje=mensaje, fin_de_mazo=fin_de_mazo, carta_evento_descartada=carta, asesino_ganador=asesino_id)
                
            case _:
                raise EventoNoImplementado()

    async def _obtener_secreto_y_posicion(self, partida_id: int, jugador_id: int, secreto_id: int) -> tuple[SecretoDB, int]:
        """Resuelve el secreto y su índice dentro de los secretos del jugador.
        Intenta primero obtener la lista completa; si está vacía prueba con revelados.
        Lanza SecretoNoEncontrado si no puede resolverlo."""
        secretos_ordenados: list[SecretoDB] = []
        if hasattr(self.secretos, "obtener_secretos"):
            try:
                secretos_ordenados = await self.secretos.obtener_secretos(partida_id, jugador_id)
            except Exception:
                secretos_ordenados = []
        if (not secretos_ordenados) and hasattr(self.secretos, "obtener_secretos_revelados"):
            try:
                secretos_ordenados = await self.secretos.obtener_secretos_revelados(partida_id)
            except Exception:
                secretos_ordenados = []
        if not secretos_ordenados:
            raise SecretoNoEncontrado()
        for idx, s in enumerate(secretos_ordenados):
            if getattr(s, "id_secreto", None) == secreto_id:
                return s, idx
        raise SecretoNoEncontrado()

    async def _validar_posicion_en_secretos(self, partida_id: int, jugador_id: int, posicion: int) -> None:
        """Valida que la posición exista para el jugador en la partida."""
        largo = await self.secretos.contar_secretos_jugador(partida_id, jugador_id)
        if posicion < 0 or posicion > (largo - 1):
            raise SecretoNoEncontrado()

    @staticmethod
    def _adjuntar_ctx_desgracia(
        e: Exception,
        *,
        secreto: SecretoDB,
        posicion: int,
        partida_id: int,
        jugador_id: int,
        set_id: Optional[int] = None
    ) -> Exception:
        setattr(e, "secreto_afectado", secreto)
        setattr(e, "posicion_secreto", posicion)
        setattr(e, "jugador_id", jugador_id)
        setattr(e, "partida_id", partida_id)
        if set_id is not None:  # solo se agrega si tiene sentido
            setattr(e, "set_id", set_id)
        return e


    async def aplicar_efectos_set(self, partida_id: int, jugador_id: int, set_id: int, secreto_id: int) -> AplicarEfectoSetResultado:
        """ Aplica los efectos del set jugado por otro jugador.
        jugador_id es a quien se le aplican los efectos."""

        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()

        set_a_aplicar = await self.sets.obtener_set_por_id(set_id)
        if not set_a_aplicar:
            raise SetNoEncontrado()

        if getattr(set_a_aplicar, "id_partida", None) != partida_id:
            raise SetNoEnPartida()

        jugador = await self.jugadores.obtener(jugador_id)
        if not jugador:
            raise JugadorNoEncontrado()

        if getattr(jugador, "id_partida", None) != partida_id:
            raise JugadorNoEnPartida()

        # Calcular posición del secreto
        secretos_ordenados = await self.secretos.obtener_secretos(partida_id, jugador_id)
        posicion_en_lista = -1
        for indice, s in enumerate(secretos_ordenados):
            if getattr(s, "id_secreto", None) == secreto_id:
                posicion_en_lista = indice
                break
        if posicion_en_lista == -1:
            raise SecretoNoEncontrado()

        # establecer el secreto afectado desde la lista ordenada
        secreto = secretos_ordenados[posicion_en_lista]
        match set_a_aplicar.nombre:
            case "Hercule Poirot" | "Miss Marple":
                try:
                    res = await self.revelar_secreto(partida_id, jugador_id, secreto_id)
                except (AsesinoRevelado, JugadorEnDesgraciaSocial, JugadorSaleDeDesgraciaSocial) as e:
                    raise self._adjuntar_ctx_desgracia(e, secreto=secreto, posicion=posicion_en_lista,
                                                       partida_id=partida_id, jugador_id=jugador_id, set_id=set_id)
                if not res:
                    raise SecretoNoDisponible()
                secreto = getattr(res, "secreto", secreto)

            case "Mr Satterthwaite":
                try:
                    res = await self.revelar_secreto(partida_id, jugador_id, secreto_id)
                except (AsesinoRevelado, JugadorEnDesgraciaSocial, JugadorSaleDeDesgraciaSocial) as e:
                    raise self._adjuntar_ctx_desgracia(e, secreto=secreto, posicion=posicion_en_lista,
                                                       partida_id=partida_id, jugador_id=jugador_id, set_id=set_id)
                if not res:
                    raise SecretoNoDisponible()

                cartas_del_set = await self.sets.obtener_cartas_del_set(set_id) or []
                tiene_wildcard = any(getattr(c, "nombre", "") == "Harley Quin Wildcard" for c in cartas_del_set)

                if tiene_wildcard:
                    rob = await self.robar_secreto(partida_id, getattr(set_a_aplicar, "id_jugador", 0), secreto_id)
                    if not rob:
                        raise SecretoNoDisponible()
                    secreto = getattr(rob, "secreto", secreto)

            case "Parker Pyne":
                # ocultar secreto del jugador afectado
                res = await self.ocultar_secreto(partida_id, jugador_id, secreto_id)
                if not res:
                    raise SecretoNoDisponible()
                secreto = getattr(res, "secreto", secreto)

            case "Lady Eileen \"Bundle\" Brent" | "Beresford":
                try:
                    res = await self.revelar_secreto(partida_id, jugador_id, secreto_id)
                except (AsesinoRevelado, JugadorEnDesgraciaSocial, JugadorSaleDeDesgraciaSocial) as e:
                    raise self._adjuntar_ctx_desgracia(e, secreto=secreto, posicion=posicion_en_lista,
                                                       partida_id=partida_id, jugador_id=jugador_id, set_id=set_id)
        if not res:
            raise SecretoNoDisponible()
        secreto = getattr(res, "secreto", secreto)

        return AplicarEfectoSetResultado(secreto_afectado=secreto, posicion_secreto=posicion_en_lista)

    async def permite_nsf(
        self,
        partida_id:int,
        tipo_accion: str,
        payload: Dict[str, Any],
        id_jugador_accion: int
    ) -> bool:
        """
        Verifica si una accion es cancelable, incluyendo las reglas complejas.
        Devuelve Falso si NO es cancelable.
        """

        # regla Beresford
        if tipo_accion == "jugar_set":
            cartas_ids = list(map(int, (payload.get("cartas_id") or [])))
            # usamos el id del jugador si no viene en el payload
            jugador_id = int(payload.get("id_jugador", id_jugador_accion))
            try:
                res = await self.cartas.obtener_cartas_en_mano(partida_id, jugador_id)
                nombres = {cast(Any, c).nombre.lower(): cast(Any,c).id_carta for c in res if cast(Any,c).id_carta in cartas_ids}
                if len(nombres) == len(cartas_ids) and {"tommy beresford", "tuppence beresford"}.issubset(set(nombres.keys())) and len(cartas_ids) == 2:
                    return False
            except Exception:
                    pass
                
        # si no es, lo paso por la ruta simple
        return await self._regla_nsf_es_cancelable_tipo(tipo_accion, payload, partida_id)
    
    async def _regla_nsf_es_cancelable_tipo(self, tipo_accion: str, payload: Dict[str, Any], partida_id: int) -> bool:
        """
        Define si una accion es cancelable por su tipo
        """
        if tipo_accion == "jugar_evento":
            nombre = str(payload.get("nombre", "")).lower()
            if "cards off the table" in nombre:
                return False
            return True
        
        if tipo_accion == "jugar_set":
            return True
        if tipo_accion == "agregar_a_set":
        # Aca, el payload tiene id_jugador, set_id, carta_id
        # necesito ver el caso particular Beresford
            id_jugador = payload.get("id_jugador")
            id_de_carta = payload.get("carta_id")
        # todos los chequeos importantes se hacen en otras funciones, acá no puedo perder mucho tiempo
            carta_involucrada = await self.cartas.obtener_carta(partida_id, id_jugador, id_de_carta)
            beresford = {"tommy beresford", "tuppence beresford"}
            nombre_carta = carta_involucrada.nombre.lower()

            if nombre_carta not in beresford:
                return True
            
            set_involucrado_id = payload.get("set_id")
            set_jugador = await self.sets.obtener_cartas_del_set(set_involucrado_id)
            nombres_en_set = {carta.nombre.lower() for carta in set_jugador}
            tiene_tommy = "tommy beresford" in nombres_en_set
            tiene_tuppence = "tuppence beresford" in nombres_en_set
            if tiene_tommy and tiene_tuppence:
               return False

            # el caso de si no estan mezclados
            return True

        if tipo_accion == "jugar_nsf":
            return True
        return False



    async def validar_carta_nsf(self, partida_id: int, jugador_id: int, carta_id: int) -> None:
        """
        Esta funcion busca revisar si la carta es nsf y compatible en sus datos.
        En caso de que no lo sea, va a levantar alguna de las excepciones que tenemos,
        y va a ser manejado por quien corresponda.
        """

        jugador = await self.jugadores.obtener(jugador_id)
        if jugador is None:
            raise ValueError("jugador_no_encontrado")

        partida = await self.partidas.obtener(partida_id)
        if partida is None:
            raise PartidaNoEncontrada()

        if getattr(jugador, "id_partida", None) != partida_id:
            raise ValueError("jugador_no_en_partida")

        carta = await self.cartas.obtener_carta(partida_id, jugador_id, carta_id)
        if not carta:
            raise ValueError("no_hay_tal_carta")
        
        if carta.nombre.lower() != "not so fast":
            raise ValueError("no_es_nsf_pero_intento_actuar_como_nsf")

     
    async def agregar_carta_a_set_propio(self, partida_id: int, jugador_id: int, carta_id: int, set_id: int) -> JugarSetResultado:
        """ Permite a un jugador agregar una carta de su mano a un set que ya posee."""
        
        jugador = await self.jugadores.obtener(jugador_id)
        if not jugador:
            raise JugadorNoEncontrado()

        partida = await self.partidas.obtener(partida_id)
        if not partida:
            raise PartidaNoEncontrada()

        if getattr(jugador, "id_partida", None) != partida_id:
            raise JugadorNoEnPartida()

        carta = await self.cartas.obtener_carta(partida_id, jugador_id, carta_id)
        if not carta:
            raise CartaNoEncontrada()

        if carta.posicion != PosicionCarta.mano:
            raise CartaNoEnMano()

        set_del_jugador = await self.sets.obtener_set_por_id(set_id)
        if not set_del_jugador:
            raise SetNoEncontrado()

        if getattr(set_del_jugador, "id_jugador", None) != jugador_id:
            raise SetNoCorrespondeAlJugadorSeleccionado()

        if carta.tipo != TipoCarta.detective:
            raise TipoCartaNoCompatibleConSet()

        # Compatibilidad de carta con el set
        if carta.nombre != "Adriane Oliver":
            if getattr(set_del_jugador, "nombre", None) == "Beresford":
                # El set se llama "Beresford" pero acepta a ambos hermanos
                permitidas_beresford = {"Tommy Beresford", "Tuppence Beresford"}
                if carta.nombre not in permitidas_beresford:
                    raise CartaNoCompatibleConSet()
            else:
                # Para el resto de los sets, el nombre de la carta debe coincidir con el del set
                if carta.nombre != set_del_jugador.nombre:
                    raise CartaNoCompatibleConSet()

        # Agregar la carta al set
        carta.posicion = PosicionCarta.set
        carta.id_set = set_del_jugador.id_set
        if hasattr(self.cartas, "guardar"):
            await self.cartas.guardar(carta)
        return JugarSetResultado(set=set_del_jugador)


    async def obtener_nombre_set(self, set_id: int) -> ObtenerNombreSetResultado:

        """Se busca obtener el nombre del set. Se usa despues de 
        verificar_seleccionar_jugador_set"""

        set = await self.sets.obtener_set_por_id(set_id)

        if set is None:
            resultado = "Desconocido"
        else:
            resultado = set.nombre
        return ObtenerNombreSetResultado(nombre=resultado)
