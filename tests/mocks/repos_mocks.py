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
except Exception:  # pragma: no cover - los tests pueden no necesitar estos imports
    EstadoPartida = SimpleNamespace(en_juego="En Juego", en_espera="En Espera", finalizada="Finalizada")  # type: ignore
    PosicionCarta = SimpleNamespace(mazo="mazo", mano="mano", descarte="descarte")  # type: ignore
    EstadoSecreto = SimpleNamespace(oculto="oculto", revelado="revelado")
    TipoSecreto = SimpleNamespace(asesino="asesino", complice="complice", otro="otro")
    class CartaModelo:  # type: ignore
        def __init__(self, id_carta: int, id_partida: int, id_jugador: Optional[int], posicion: Any):
            self.id_carta = id_carta
            self.id_partida = id_partida
            self.id_jugador = id_jugador
            self.posicion = posicion
        
    class SecretoDB:
        def __init__(self, id_secreto: int, id_partida: int, id_jugador: int, tipo: Any, estado: Any):
            self.id_secreto = id_secreto
            self.id_partida = id_partida
            self.id_jugador = id_jugador
            self.tipo = tipo
            self.estado = estado


# --------- Fábricas de Repos Mockeados (Async) ---------

def _async_method(default_return: Any = None) -> AsyncMock:
    m = AsyncMock()
    if default_return is not None:
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
    Podés reconfigurar luego: repo.obtener.return_value = ...; repo.obtener.side_effect = ...
    """
    repo = MagicMock()
    repo.db = object()
    repo.crear = _async_method(crear_return)
    repo.obtener = _async_method(obtener_return)
    repo.listar_en_espera = _async_method(listar_en_espera_return)
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
    repo.obtener = _async_method(obtener_return)
    # opcional: guardar_muchos si el servicio lo usa
    repo.guardar_muchos = _async_method()
    return repo


def crear_repo_carta_mock(
    *,
    crear_muchas_return: Any | None = None,
    contar_en_mano_return: Any | None = None,
    obtener_mazo_disponible_return: Any | None = None,
    contar_en_mazo_return: Any | None = None,
) -> MagicMock:
    repo = MagicMock()
    repo.db = object()
    repo.crear_muchas = _async_method(crear_muchas_return)
    repo.contar_en_mano = _async_method(contar_en_mano_return)
    repo.obtener_mazo_disponible = _async_method(obtener_mazo_disponible_return)
    # algunos servicios pueden intentar persistir en lote
    repo.guardar_muchas = _async_method()
    # y consultar restantes en el mazo
    repo.contar_en_mazo = _async_method(contar_en_mazo_return if contar_en_mazo_return is not None else 0)
    return repo

    
def crear_repo_secreto_mock(
    *,
    crear_muchos_return: Any | None = None,
) -> MagicMock:
    repo = MagicMock()
    repo.db = object()
    repo.crear_muchos = _async_method(crear_muchos_return)
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
        estado = getattr(EstadoPartida, "en_juego", "en_juego")
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


def crear_jugador(*, id_jugador: int = 1, orden_turno: Optional[int] = 1, id_partida: int = 1, nombre: str = "Jugador") -> Any:
    return type(
        "JugadorDummy",
        (),
        {
            "id_jugador": id_jugador,
            "orden_turno": orden_turno,
            "id_partida": id_partida,
            "nombre": nombre,
        },
    )()


def crear_carta(
    *, id_carta: int = 1, id_partida: int = 1, id_jugador: Optional[int] = None, posicion: Any | None = None
) -> CartaModelo:
    if posicion is None:
        posicion = getattr(PosicionCarta, "mazo", "mazo")
    return CartaModelo(id_carta=id_carta, id_partida=id_partida, id_jugador=id_jugador, posicion=posicion)

def crear_secreto(
    *, id_secreto: int = 1, id_partida: int = 1, id_jugador: int = 1, tipo: Any  = TipoSecreto.otro, estado: Any = EstadoSecreto.oculto
 ) -> SecretoDB:
    return SecretoDB(id_secreto=id_secreto, id_partida=id_partida, id_jugador=id_jugador, tipo=tipo, estado=estado)
