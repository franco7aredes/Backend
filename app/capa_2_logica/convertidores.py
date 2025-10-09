from typing import Any, Dict, cast

def _estado_a_str(estado: Any) -> str:
    return cast(str, estado.value) if hasattr(estado, "value") else cast(str, estado)


def partida_a_dict(p: Any) -> Dict[str, Any]:
    return {
        "id_partida": cast(int, p.id_partida),
        "minimo": cast(int, p.minimo),
        "maximo": cast(int, p.maximo),
        "id_jugador_creador": (cast(int, p.id_jugador_creador) if getattr(p, "id_jugador_creador", None) is not None else None),
        "estado": _estado_a_str(p.estado),
        "cantidad_jugadores": cast(int, p.cantidad_jugadores),
        "turno_actual": cast(int, p.turno_actual),
    }


def jugador_a_dict(j: Any) -> Dict[str, Any]:
    return {
        "id_jugador": cast(int, j.id_jugador),
        "nombre": cast(str, j.nombre),
        "fecha_nacimiento": j.fecha_nacimiento,
        "id_avatar": (cast(int, j.id_avatar) if getattr(j, "id_avatar", None) is not None else None),
        "orden_turno": (cast(int, j.orden_turno) if getattr(j, "orden_turno", None) is not None else None),
    }
