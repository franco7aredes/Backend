import asyncio
from typing import Dict, List, Any
from .websockets.ApiWS import administrador
from app.capa_3_api.mapeadores import mapear_cartas_a_dto
from typing import Optional


async def _notificar_jugadores_async(cartas_repartidas: Dict[int, List[Any]]):
    for jugador_id, cartas in cartas_repartidas.items():
        cartas_data = [c.dict() for c in mapear_cartas_a_dto(cartas)]
        mensaje = {"evento": "partida_iniciada", "data": {"mano": cartas_data}}
        await administrador.enviar_mensaje(mensaje, jugador_id)

async def _notificar_asesino_revelado(partida_id: int) -> None:
    await administrador.difundir_a_partida(partida_id,
        {"evento": "asesino revelado"})

async def notificar_asesino_revelado_detalle(
    admin,
    partida_id: int,
    set_id: int,
    jugador_id: int,
    secreto_id: int,
    posicion_secreto: Optional[int],
    secreto_tipo: Optional[str],
) -> None:
    try:
        await admin.difundir_a_partida(
            partida_id,
            {
                "evento": "asesino_revelado",
                "partida_id": partida_id,
                "set_id": set_id,
                "jugador_id": jugador_id,
                "secreto_id": secreto_id,
                "posicion_secreto": posicion_secreto,
                "secreto_tipo": secreto_tipo,
                "mensaje": "Se reveló el asesino. La partida finaliza.",
            },
        )
    except Exception:
        pass

async def notificar_jugador_entra_en_desgracia_detalle(
    admin,
    partida_id: int,
    set_id: int,
    jugador_id: int,
    secreto_id: int,
    posicion_secreto: Optional[int],
    secreto_estado: Optional[str],
    secreto_tipo: Optional[str],
) -> None:
    # evento de entrada en desgracia
    try:
        await admin.difundir_a_partida(
            partida_id,
            {
                "evento": "jugador_entra_en_desgracia_social",
                "partida_id": partida_id,
                "jugador_id": jugador_id,
                "causa": "revelacion_secreto",
                "secreto_id": secreto_id,
                "posicion_secreto": posicion_secreto,
                "secreto_tipo": secreto_tipo,
            },
        )
    except Exception:
        pass
    # eco del efecto aplicado
    try:
        await admin.difundir_a_partida(
            partida_id,
            {
                "evento": "efecto_set_aplicado",
                "partida_id": partida_id,
                "set_id": set_id,
                "jugador_id": jugador_id,
                "secreto_id": secreto_id,
                "posicion_secreto": posicion_secreto,
                "secreto_estado": secreto_estado,
                "secreto_tipo": secreto_tipo,
            },
        )
    except Exception:
        pass

async def notificar_jugador_sale_de_desgracia_detalle(
    admin,
    partida_id: int,
    set_id: int,
    jugador_id: int,
    secreto_id: int,
    posicion_secreto: Optional[int],
    secreto_estado: Optional[str],
    secreto_tipo: Optional[str],
) -> None:
    try:
        await admin.difundir_a_partida(
            partida_id,
            {
                "evento": "jugador_sale_de_desgracia_social",
                "partida_id": partida_id,
                "jugador_id": jugador_id,
            },
        )
    except Exception:
        pass
    try:
        await admin.difundir_a_partida(
            partida_id,
            {
                "evento": "efecto_set_aplicado",
                "partida_id": partida_id,
                "set_id": set_id,
                "jugador_id": jugador_id,
                "secreto_id": secreto_id,
                "posicion_secreto": posicion_secreto,
                "secreto_estado": secreto_estado,
                "secreto_tipo": secreto_tipo,
            },
        )
    except Exception:
        pass

async def notificar_efecto_set_aplicado(
    admin,
    partida_id: int,
    set_id: int,
    jugador_id: int,
    secreto_id: int,
    posicion_secreto: Optional[int],
    secreto_estado: Optional[str],
    secreto_tipo: Optional[str],
) -> None:
    try:
        await admin.difundir_a_partida(
            partida_id,
            {
                "evento": "efecto_set_aplicado",
                "partida_id": partida_id,
                "set_id": set_id,
                "jugador_id": jugador_id,
                "secreto_id": secreto_id,
                "posicion_secreto": posicion_secreto,
                "secreto_estado": secreto_estado,
                "secreto_tipo": secreto_tipo,
            },
        )
    except Exception:
        pass

async def notificar_fin_por_desgracia_social_detalle(
    admin,
    partida_id: int,
    asesino_id: int
) -> None:
    try:
        await admin.difundir_a_partida(
            partida_id,
            {
                "evento": "fin_por_desgracia_social",
                "partida_id": partida_id,
                "asesinoId": asesino_id,
            }
        )
    except Exception:
        pass