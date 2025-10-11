from typing import List, cast, Dict, Any
from datetime import date
from app.capa_3_api.dtos.partidas import Partida as PartidaDTO, Jugador as JugadorDTO
from app.capa_3_api.dtos.juego import Carta as CartaDTO
from app.capa_3_api.dtos.juego import SecretoDTO


def _estado_a_str(estado) -> str:
    return estado.value if hasattr(estado, "value") else cast(str, estado)


def mapear_partida_a_dict(p: Any) -> Dict[str, Any]:
    if isinstance(p, dict):
        return {
            "id_partida": cast(int, p.get("id_partida")),
            "minimo": cast(int, p.get("minimo")),
            "maximo": cast(int, p.get("maximo")),
            "id_jugador_creador": (cast(int, p.get("id_jugador_creador")) if p.get("id_jugador_creador") is not None else None),
            "estado": cast(str, p.get("estado")),
            "cantidad_jugadores": cast(int, p.get("cantidad_jugadores")),
            "turno_actual": cast(int, p.get("turno_actual")),
            "jugadores": [],
        }
    return {
        "id_partida": cast(int, getattr(p, "id_partida", None)),
        "minimo": cast(int, getattr(p, "minimo", None)),
        "maximo": cast(int, getattr(p, "maximo", None)),
        "id_jugador_creador": (cast(int, getattr(p, "id_jugador_creador", None)) if getattr(p, "id_jugador_creador", None) is not None else None),
        "estado": _estado_a_str(getattr(p, "estado", None)),
        "cantidad_jugadores": cast(int, getattr(p, "cantidad_jugadores", None)),
        "turno_actual": cast(int, getattr(p, "turno_actual", None)),
        "jugadores": [],
    }


def mapear_partidas_a_dict(partidas: List[Any]) -> List[Dict[str, Any]]:
    return [mapear_partida_a_dict(p) for p in partidas]


def mapear_jugador_a_dict(j: Any) -> Dict[str, Any]:
    if isinstance(j, dict):
        return {
            "id_jugador": cast(int, j.get("id_jugador")),
            "nombre": cast(str, j.get("nombre")),
            "fecha_nacimiento": cast(date, j.get("fecha_nacimiento")),
            "id_avatar": (cast(int, j.get("id_avatar")) if j.get("id_avatar") is not None else None),
            "orden_turno": (cast(int, j.get("orden_turno")) if j.get("orden_turno") is not None else None),
        }
    return {
        "id_jugador": cast(int, getattr(j, "id_jugador", None)),
        "nombre": cast(str, getattr(j, "nombre", None)),
        "fecha_nacimiento": cast(date, getattr(j, "fecha_nacimiento", None)),
        "id_avatar": (cast(int, getattr(j, "id_avatar", None)) if getattr(j, "id_avatar", None) is not None else None),
        "orden_turno": (cast(int, getattr(j, "orden_turno", None)) if getattr(j, "orden_turno", None) is not None else None),
    }


def mapear_jugadores_a_dict(jugadores: List[Any]) -> List[Dict[str, Any]]:
    return [mapear_jugador_a_dict(j) for j in jugadores]


# Versión que devuelve DTOs (Pydantic) para usar con response_model
def mapear_partida_a_dto(p: Any) -> PartidaDTO:
    d = mapear_partida_a_dict(p)
    return PartidaDTO(
        id_partida=cast(int, d.get("id_partida")),
        minimo=cast(int, d.get("minimo")),
        maximo=cast(int, d.get("maximo")),
        id_jugador_creador=cast(int, d.get("id_jugador_creador")) if d.get("id_jugador_creador") is not None else None,
        estado=cast(str, d.get("estado")),
        cantidad_jugadores=cast(int, d.get("cantidad_jugadores")),
        turno_actual=cast(int, d.get("turno_actual")),
        jugadores=[],
    )


def mapear_partidas_a_dto(partidas: List[Any]) -> List[PartidaDTO]:
    return [mapear_partida_a_dto(p) for p in partidas]


def mapear_jugador_a_dto(j: Any) -> JugadorDTO:
    d = mapear_jugador_a_dict(j)
    return JugadorDTO(
        id_jugador=cast(int, d.get("id_jugador")),
        nombre=cast(str, d.get("nombre")),
        fecha_nacimiento=cast(date, d.get("fecha_nacimiento")),
        id_avatar=cast(int, d.get("id_avatar")) if d.get("id_avatar") is not None else None,
        orden_turno=cast(int, d.get("orden_turno")) if d.get("orden_turno") is not None else None,
    )


def mapear_jugadores_a_dto(jugadores: List[Any]) -> List[JugadorDTO]:
    return [mapear_jugador_a_dto(j) for j in jugadores]


# Cartas
def mapear_carta_a_dto(carta: Any) -> CartaDTO:
    # Requiere from_attributes=True en model_config del DTO
    return CartaDTO.model_validate(carta)


def mapear_cartas_a_dto(cartas: List[Any]) -> List[CartaDTO]:
    return [mapear_carta_a_dto(c) for c in cartas]

# Secretos

def mapear_secreto_a_dto(secreto: Any) -> SecretoDTO:
    return SecretoDTO.model_validate(secreto)

def mapear_secretos_a_dto(secretos: List[Any]) -> List[SecretoDTO]:
    return [mapear_secreto_a_dto(s) for s in secretos]
