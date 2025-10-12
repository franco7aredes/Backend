import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import PartidaNoEncontrada
from app.capa_2_logica.resultados import ObtenerCartasResultado
from app.capa_0_definicion_bd.models.cartas_modelos import TipoCarta, PosicionCarta


@pytest.mark.asyncio
async def test_obtener_cartas_jugador_con_exito(async_client):
    # Cartas dummy con atributos necesarios para el DTO
    c1 = type("C", (), {})()
    c1.id_carta = 1
    c1.id_partida = 7
    c1.id_jugador = 10
    c1.posicion = PosicionCarta.mano
    c1.nombre = "Hercule Poirot"
    c1.tipo = TipoCarta.detective

    c2 = type("C", (), {})()
    c2.id_carta = 2
    c2.id_partida = 7
    c2.id_jugador = 10
    c2.posicion = PosicionCarta.mano
    c2.nombre = "Not so fast"
    c2.tipo = TipoCarta.instant

    class S:
        async def obtener_cartas_propias(self, *args, **kwargs): ...

    mock_service = S()
    setattr(mock_service, "obtener_cartas_propias", AsyncMock(return_value=ObtenerCartasResultado(cartas=[c1, c2])))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.get("/partida/7/cartas/10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["cantidad"] == 2
    assert isinstance(body["cartas"], list) and len(body["cartas"]) == 2
    # Verificar que vengan los campos clave del DTO
    for item in body["cartas"]:
        assert "id_carta" in item
        assert "posicion" in item and item["posicion"] == "mano"
        assert "nombre" in item and isinstance(item["nombre"], str)
        assert "tipo" in item and isinstance(item["tipo"], str)

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_obtener_cartas_jugador_partida_no_encontrada(async_client):
    class S:
        async def obtener_cartas_propias(self, *args, **kwargs): ...

    async def raise_nf(*_, **__):
        raise PartidaNoEncontrada()

    mock_service = S()
    setattr(mock_service, "obtener_cartas_propias", raise_nf)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.get("/partida/999/cartas/10")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Partida no encontrada"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_obtener_cartas_jugador_no_encontrado(async_client):
    class S:
        async def obtener_cartas_propias(self, *args, **kwargs): ...

    async def raise_je(*_, **__):
        raise ValueError("jugador_no_encontrado")

    mock_service = S()
    setattr(mock_service, "obtener_cartas_propias", raise_je)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.get("/partida/7/cartas/404")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Jugador no encontrado"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_obtener_cartas_jugador_no_pertenece(async_client):
    class S:
        async def obtener_cartas_propias(self, *args, **kwargs): ...

    async def raise_jnp(*_, **__):
        raise ValueError("jugador_no_en_partida")

    mock_service = S()
    setattr(mock_service, "obtener_cartas_propias", raise_jnp)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    resp = await async_client.get("/partida/7/cartas/11")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Jugador no pertenece a la partida"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)