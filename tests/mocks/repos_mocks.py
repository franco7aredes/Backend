"""
Utilidades para crear repositorios mockeados reutilizables en tests.

Evita reescribir clases dummy en cada test. Provee:
- Fábricas de repos (con AsyncMock en sus métodos)
- Atajos para crear objetos de dominio mínimos (partida, jugador, carta)
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock

# Enums y modelos (solo para tipos/valores por defecto)
try:
    from app.capa_0_definicion_bd.models.partidas_modelos import EstadoPartida
    from app.capa_0_definicion_bd.models.secretos_modelos import SecretoDB, EstadoSecreto, Tiposecreto
    from app.capa_0_definicion_bd.models.cartas_modelos import Carta as CartaModelo, PosicionCarta
    from app.capa_0_definicion_bd.models.sets_modelos import Set as SetModelo
except Exception:  # pragma: no cover - los tests pueden no necesitar estos imports
    EstadoPartida = SimpleNamespace(en_juego="En Juego", en_espera="En Espera", finalizada="Finalizada")  # type: ignore
    PosicionCarta = SimpleNamespace(mazo="mazo", mano="mano", descarte="descarte", draft="draft")  # type: ignore
    EstadoSecreto = SimpleNamespace(oculto="oculto", revelado="revelado")
    TipoSecreto = SimpleNamespace(asesino="asesino", complice="complice", otro="otro")
    class CartaModelo:  # type: ignore
        def __init__(self, id_carta: int, id_partida: int, id_jugador: Optional[int], posicion: Any, orden_en_descarte: Optional[int]):
            self.id_carta = id_carta
            self.id_partida = id_partida
            self.id_jugador = id_jugador
            self.posicion = posicion
            self.orden_en_descarte = orden_en_descarte
        
    class SecretoDB:
        def __init__(self, id_secreto: int, id_partida: int, id_jugador: int, tipo: Any, estado: Any):
            self.id_secreto = id_secreto
            self.id_partida = id_partida
            self.id_jugador = id_jugador
            self.tipo = tipo
            self.estado = estado
    
    class SetModelo:
        def __init__(self, id_set: int, id_partida: int, id_jugador: int, nombre: str):
            self.id_set = id_set
            self.id_partida = id_partida
            self.id_jugador = id_jugador
            self.nombre = nombre


# --------- Fábricas de Repos Mockeados (Async) ---------

def _async_method(default_return: Any = None) -> AsyncMock:
    m = AsyncMock()
    m.return_value = default_return
    return m


def crear_repo_partida_mock(
    *,
    obtener_return: Any | None = None,
    listar_en_espera_return: Any | None = None,
    crear_return: Any | None = None,
    confirmar_return: Any | None = None,
) -> MagicMock:
    """Repo de partidas con métodos async mockeados.
    """
    repo = MagicMock()
    repo.db = object()
    repo.crear = _async_method(crear_return)
    repo.obtener = AsyncMock(return_value=obtener_return)
    repo.listar_en_espera = _async_method(listar_en_espera_return if listar_en_espera_return is not None else [])
    repo.guardar = _async_method()
    repo.confirmar = _async_method(confirmar_return)
    return repo


def crear_repo_jugador_mock(
    *,
    obtener_return: Any | None = None,
    listar_por_partida_return: Any | None = None,
    crear_return: Any | None = None,
) -> MagicMock:
    repo = MagicMock()
    repo.db = object()
    repo.listar_por_partida = _async_method(listar_por_partida_return)
    repo.crear = _async_method(crear_return)
    repo.obtener = AsyncMock(return_value=obtener_return)
    # opcional: guardar_muchos si el servicio lo usa
    repo.guardar_muchos = _async_method()
    return repo


def crear_repo_carta_mock(
    *,
    crear_muchas_return: Any | None = None,
    contar_en_mano_return: Any | None = None,
    obtener_mazo_disponible_return: Any | None = None,
    contar_en_mazo_return: Any | None = None,
    obtener_draft_return: Any | None = None,
    obtener_cartas_en_mano_return: Any | None = None,
    obtener_draft_disponible_return: Any | None = None,
    mover_primera_carta_mazo_a_draft_return: Any | None = None,
    obtener_cantidad_descartadas_return: Any | None = None,
    obtener_primeras_de_descarte_return: Any | None = None,
    obtener_carta_return: Any | None = None,
) -> MagicMock:
    
    repo = MagicMock()
    repo.db = object()
    repo.crear_muchas = _async_method(crear_muchas_return)
    repo.contar_en_mano = _async_method(contar_en_mano_return)
    repo.obtener_mazo_disponible = _async_method(obtener_mazo_disponible_return)
    repo.obtener_draft = _async_method(obtener_draft_return)
    # algunos servicios pueden intentar persistir en lote
    repo.guardar_muchas = _async_method()
    # y consultar restantes en el mazo
    repo.contar_en_mazo = _async_method(contar_en_mazo_return if contar_en_mazo_return is not None else 0)
    repo.obtener_cartas_en_mano = _async_method(obtener_cartas_en_mano_return)
    repo.obtener_draft_disponible = _async_method(obtener_draft_disponible_return)
    repo.mover_primera_carta_mazo_a_draft = _async_method(mover_primera_carta_mazo_a_draft_return)
    repo.obtener_cantidad_descartadas = _async_method(obtener_cantidad_descartadas_return if obtener_cantidad_descartadas_return is not None else 0)
    repo.obtener_primeras_de_descarte = _async_method(obtener_primeras_de_descarte_return
        if obtener_primeras_de_descarte_return is not None
        else []
    )
    repo.obtener_carta = _async_method(obtener_carta_return)
    repo.guardar = _async_method()
    return repo

    
def crear_repo_secreto_mock(
    *,
    crear_muchos_return: Any | None = None,
    obtener_secretos_return: Any | None = None,
    obtener_secreto_asesino_return: Any | None = None,
    contar_secretos_jugador_return: Any | None = None,
    obtener_secretos_revelados_return: Any | None = None,
) -> MagicMock:
    repo = MagicMock()
    repo.db = object()
    repo.crear_muchos = _async_method(crear_muchos_return)
    repo.obtener_secretos = _async_method(obtener_secretos_return)
    repo.obtener_secreto_asesino = _async_method(obtener_secreto_asesino_return)
    repo.contar_secretos_jugador = _async_method(contar_secretos_jugador_return)
    repo.obtener_secretos_revelados = _async_method(obtener_secretos_revelados_return)
    return repo

def crear_repo_set_mock(
    *,
    crear_set_return: Any | None = None,
    obtener_set_por_id_return: Any | None = None,
    guardar_set_return: Any | None = None,
    obtener_cartas_del_set_return: Any | None = None,
) -> MagicMock:
    repo = MagicMock()
    repo.db = object()
    repo.crear_set = _async_method(crear_set_return)
    repo.obtener_set_por_id = _async_method(obtener_set_por_id_return)
    repo.guardar_set = _async_method(guardar_set_return)
    repo.obtener_cartas_del_set = _async_method(obtener_cartas_del_set_return)
    return repo

# --------- Constructores mínimos de entidades ---------

def crear_partida_en_juego(
    *,
    id_partida: int = 1,
    estado: Any = None,
    cantidad_jugadores: int = 2,
    minimo: int = 2,
    maximo: int = 4,
    turno_actual: int = 1,
) -> Any:
    if estado is None:
        estado = getattr(EstadoPartida, "en_juego", "En Juego")
    return type(
        "PartidaDummy",
        (),
        {
            "id_partida": id_partida,
            "estado": estado,
            "cantidad_jugadores": cantidad_jugadores,
            "minimo": minimo,
            "maximo": maximo,
            "turno_actual": turno_actual,
        },
    )()


def crear_partida_en_espera(
    *,
    id_partida: int = 1,
    cantidad_jugadores: int = 0,
    minimo: int = 2,
    maximo: int = 4,
) -> Any:
    return type(
        "PartidaDummy",
        (),
        {
            "id_partida": id_partida,
            "estado": getattr(EstadoPartida, "en_espera", "en_espera"),
            "cantidad_jugadores": cantidad_jugadores,
            "minimo": minimo,
            "maximo": maximo,
            "turno_actual": 1,
        },
    )()


def crear_partida_finalizada(*, id_partida: int = 1) -> Any:
    return type(
        "PartidaDummy",
        (),
        {
            "id_partida": id_partida,
            "estado": getattr(EstadoPartida, "finalizada", "finalizada"),
            "cantidad_jugadores": 0,
            "minimo": 2,
            "maximo": 4,
            "turno_actual": 1,
        },
    )()


def crear_jugador(*, id_jugador: int = 1, orden_turno: Optional[int] = 1, id_partida: int = 1, nombre: str = "Jugador", fecha_nacimiento: Optional[Any] = None) -> Any:
    return type(
        "JugadorDummy",
        (),
        {
            "id_jugador": id_jugador,
            "orden_turno": orden_turno,
            "id_partida": id_partida,
            "nombre": nombre,
            "fecha_nacimiento": fecha_nacimiento
        },
    )()


def crear_carta(
    *, id_carta: int = 1, id_partida: int = 1, id_jugador: Optional[int] = None, posicion: Any | None = None, orden_en_descarte: Optional[int] = None
) -> CartaModelo:
    if posicion is None:
        posicion = getattr(PosicionCarta, "mazo", "mazo")
    return CartaModelo(id_carta=id_carta, id_partida=id_partida, id_jugador=id_jugador, posicion=posicion, orden_en_descarte = orden_en_descarte)

def crear_secreto(
    *, id_secreto: int = 1, id_partida: int = 1, id_jugador: int = 1, tipo: Any  = TipoSecreto.otro, estado: Any = EstadoSecreto.oculto
 ) -> SecretoDB:
    return SecretoDB(id_secreto=id_secreto, id_partida=id_partida, id_jugador=id_jugador, tipo=tipo, estado=estado)

def crear_set(*, id_set: int = 1, id_partida: int = 1, id_jugador: int = 1, nombre: str = "Detective") -> SetModelo:
    return SetModelo(id_set=id_set, id_partida=id_partida, id_jugador=id_jugador, nombre=nombre)
