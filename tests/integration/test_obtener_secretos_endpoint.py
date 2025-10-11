import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.errores import PartidaNoEncontrada
from app.capa_2_logica.resultados import ObtenerSecretosResultado
from app.capa_0_definicion_bd.models.secretos_modelos import(
    EstadoSecreto,
    TipoSecreto,
    SecretoDB
)


@pytest.mark.asyncio
async def test_obtener_secretos_bonito(async_client):
    class S:
        async def obtener_secretos_propios(self, partida_id: int, jugador_id: int): ...
    mock_service = S()
    setattr(mock_service, "obtener_secretos_propios", 
        AsyncMock(return_value=ObtenerSecretosResultado(
            secretos=[
                SecretoDB(id_secreto=1, id_partida=1, id_jugador=2, tipo=TipoSecreto.asesino, estado=EstadoSecreto.oculto),
                SecretoDB(id_secreto=2, id_partida=1, id_jugador=2, tipo=TipoSecreto.otro, estado=EstadoSecreto.oculto),
                SecretoDB(id_secreto=3, id_partida=1, id_jugador=2, tipo=TipoSecreto.otro, estado=EstadoSecreto.oculto)
            ]
        )))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service
    
    resp = await async_client.get("/partidas/1/secretos", params={"jugador_id": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mensaje"].startswith("Tienes 3 secretos")
    assert len(body["secretos"]) == 3
    assert all(s["estado"] == "oculto" for s in body["secretos"])

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_obtener_cero_secretos(async_client):
    class S:
        async def obtener_secretos_propios(self, partida_id: int, jugador_id: int): ...
    mock_service = S()
    setattr(mock_service, "obtener_secretos_propios", 
        AsyncMock(return_value=ObtenerSecretosResultado(secretos=[])))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service
    
    resp = await async_client.get("/partidas/1/secretos", params={"jugador_id": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mensaje"].startswith("Tienes 0 secretos")
    assert len(body["secretos"]) == 0

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)
