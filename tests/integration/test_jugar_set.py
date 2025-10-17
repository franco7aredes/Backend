import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.resultados import JugarSetResultado
from app.capa_2_logica.errores import PartidaNoEncontrada

@pytest.mark.asyncio
async def test_preparar_set(async_client):
    class S:
        async def preparar_set(self, *args, **kwargs): ...
    set_data = {"id_set": 1, "id_partida": 1, "id_jugador": 1, "nombre": "Miss Marple"}
    mock_service = S()
    setattr(mock_service, "preparar_set", AsyncMock(return_value=JugarSetResultado(set=set_data)))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    payload = {"id_jugador": 1, "cartas_id": [1, 2, 3]}
    resp = await async_client.post("/partidas/1/sets", json=payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["set"]["id_set"] == 1
    assert body["set"]["nombre"] == "Miss Marple"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_jugar_set_partida_no_encontrada(async_client):
    class S:
        async def preparar_set(self, *args, **kwargs): ...
    async def raise_nf(*_, **__):
        raise PartidaNoEncontrada()

    mock_service = S()
    setattr(mock_service, "preparar_set", raise_nf)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    payload = {"id_jugador": 1, "cartas_id": [1, 2]}
    resp = await async_client.post("/partidas/1/sets", json=payload)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Partida no encontrada"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_jugar_set_value_error(async_client):
    class S:
        async def preparar_set(self, *args, **kwargs): ...
    async def raise_err(*_, **__):
        raise ValueError("Set inválido")

    mock_service = S()
    setattr(mock_service, "preparar_set", raise_err)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    payload = {"id_jugador": 1, "cartas_id": [1, 2]}
    resp = await async_client.post("/partidas/1/sets", json=payload)

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Set inválido"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)
