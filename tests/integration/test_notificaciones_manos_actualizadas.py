import pytest
from unittest.mock import AsyncMock
from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.resultados import (
    ReponerResultado,
    DescartarResultado,
    CantidadManosResultado,
)
from app.capa_0_definicion_bd.models.cartas_modelos import PosicionCarta, TipoCarta
import app.capa_3_api.websockets.ApiWS as wsmod

class _Carta:
    id_carta = 1
    id_partida = 9
    id_jugador = 3
    posicion = PosicionCarta.mano
    nombre = "X"
    tipo = TipoCarta.instant

@pytest.mark.asyncio
async def test_reponer_emite_manos_actualizadas(async_client, monkeypatch):
    class S:
        async def reponer_del_mazo(self, *a, **k): ...
        async def obtener_cantidad_cartas_en_mazo(self, *a, **k): ...
        async def obtener_cantidad_manos(self, *a, **k): ...

    svc = S()
    setattr(svc, "reponer_del_mazo", AsyncMock(return_value=ReponerResultado(
        cartas=[_Carta()], fin_de_mazo=False, max_alcanzado=False, sin_cartas=False)))
    setattr(svc, "obtener_cantidad_cartas_en_mazo", AsyncMock(return_value=type("R", (), {"cantidad": 10})()))
    setattr(svc, "obtener_cantidad_manos", AsyncMock(return_value=CantidadManosResultado(cartas_por_jugador={3: 4})))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: svc

    monkeypatch.setattr(wsmod.administrador, "difundir_a_partida", AsyncMock())

    resp = await async_client.put("/partida/9/reponer", json={"jugador_id": 3})
    assert resp.status_code == 200

    # Broadcast manos_actualizadas
    wsmod.administrador.difundir_a_partida.assert_any_call(
        9,
        {
            "evento": "manos_actualizadas",
            "partida_id": 9,
            "manos": [{"id_jugador": 3, "cantidad": 4}],
        },
    )

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_descartar_emite_manos_actualizadas(async_client, monkeypatch):
    class CartaDesc:
        id_carta = 5
        id_partida = 11
        id_jugador = 7
        posicion = PosicionCarta.mano
        nombre = "Dead card folly"
        tipo = TipoCarta.event

    class S:
        async def descartar_carta(self, *a, **k): ...
        async def obtener_cantidad_manos(self, *a, **k): ...

    svc = S()
    setattr(svc, "descartar_carta", AsyncMock(return_value=DescartarResultado(carta=CartaDesc())))
    setattr(svc, "obtener_cantidad_manos", AsyncMock(return_value=CantidadManosResultado(cartas_por_jugador={7: 2})))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: svc

    monkeypatch.setattr(wsmod.administrador, "difundir_a_partida", AsyncMock())

    resp = await async_client.patch(
        "/partida/11/descartar",
        json={"jugador_id": 7, "carta_id": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id_carta"] == 5

    # Broadcast jugador_descarto
    wsmod.administrador.difundir_a_partida.assert_any_call(
        11,
        {
            "evento": "jugador_descarto",
            "partida_id": 11,
            "jugador_id": 7,
            "carta": 5,
        },
    )
    # Broadcast manos_actualizadas
    wsmod.administrador.difundir_a_partida.assert_any_call(
        11,
        {
            "evento": "manos_actualizadas",
            "partida_id": 11,
            "manos": [{"id_jugador": 7, "cantidad": 2}],
        },
    )

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_reponer_draft_emite_manos_actualizadas_varios_jugadores(async_client, monkeypatch):

    # Mock cartas y manos de varios jugadores
    class _Carta:
        id_carta = 2
        id_partida = 20
        id_jugador = 5
        posicion = PosicionCarta.mano
        nombre = "Y"
        tipo = TipoCarta.event

    class ServicioMock:
        async def reponer_del_draft(self, *a, **k):
            return ReponerResultado(
                cartas=[_Carta()],
                fin_de_mazo=False,
                max_alcanzado=False,
                sin_cartas=False
            )
        async def obtener_cantidad_cartas_en_mazo(self, *a, **k):
            class R: cantidad = 8
            return R()
        async def obtener_cantidad_manos(self, *a, **k):
            # Varios jugadores
            return CantidadManosResultado(cartas_por_jugador={5: 3, 6: 2})


    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: ServicioMock()

    mock_difundir = AsyncMock()
    monkeypatch.setattr(wsmod.administrador, "difundir_a_partida", mock_difundir)

    resp = await async_client.put("/partida/20/reponer_draft?carta_id=1", json={"jugador_id": 5})
    assert resp.status_code == 200

    # Debe emitir manos_actualizadas con todos los jugadores
    mock_difundir.assert_any_call(
        20,
        {
            "evento": "manos_actualizadas",
            "partida_id": 20,
            "manos": [{"id_jugador": 5, "cantidad": 3}, {"id_jugador": 6, "cantidad": 2}],
        },
    )

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)