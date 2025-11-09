import pytest
from unittest.mock import AsyncMock

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.resultados import EventoResultado
from app.capa_2_logica.errores import PartidaNoEncontrada, JugadorNoEncontrado, JugadorNoEnPartida
from app.capa_2_logica.errores import JugadorEnDesgraciaSocial, JugadorSaleDeDesgraciaSocial

@pytest.mark.asyncio
async def test_jugar_evento_exitoso(async_client):
    class S:
        async def preparar_evento(self, *args, **kwargs): ...
    
    mock_resultado = EventoResultado(
        tipo_evento="Early Train To Paddington",
        mensaje="6 cartas fueron movidas del mazo al descarte",
        cartas_descartadas=[type("Carta", (), {"id_carta": i})() for i in range(1, 7)],
        carta_evento_descartada=type("Carta", (), {"id_carta": 40})(),
        fin_de_mazo=False
    )

    mock_service = S()
    setattr(mock_service, "preparar_evento", AsyncMock(return_value=mock_resultado))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    payload = {
        "id_jugador": 1,
        "id_carta": 40,
        "id_carta_descarte": None,
        "id_secreto": None,
        "id_jugador_objetivo": None,
        "id_set": None
    }

    resp = await async_client.post("/partidas/1/eventos", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["mensaje"] == "Evento jugado con éxito"
    assert body["tipo_evento"] == "Early Train To Paddington"
    assert body["detalle"] == "6 cartas fueron movidas del mazo al descarte"
    assert body["cartas_descartadas"] == [1, 2, 3, 4, 5, 6]
    assert body["fin_de_mazo"] is False
    assert body["carta_evento_descartada"] == 40

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_jugar_evento_fin_de_mazo(async_client):
    class S:
        async def preparar_evento(self, *args, **kwargs): ...

    mock_resultado = EventoResultado(
        tipo_evento="Early Train To Paddington",
        mensaje="6 cartas fueron movidas del mazo al descarte. El asesino ha ganado. La partida ha finalizado.",
        cartas_descartadas=[type("Carta", (), {"id_carta": i})() for i in range(1, 7)],
        fin_de_mazo=True  
    )

    mock_service = S()
    setattr(mock_service, "preparar_evento", AsyncMock(return_value=mock_resultado))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    payload = {
        "id_jugador": 1,
        "id_carta": 40,
        "id_carta_descarte": None,
        "id_secreto": None,
        "id_jugador_objetivo": None,
        "id_set": None
    }

    resp = await async_client.post("/partidas/1/eventos", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["mensaje"] == "Evento jugado con éxito"
    assert body["tipo_evento"] == "Early Train To Paddington"
    assert body["detalle"] == mock_resultado.mensaje
    assert body["cartas_descartadas"] == [1, 2, 3, 4, 5, 6]
    assert body["fin_de_mazo"] is True  

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_jugar_evento_partida_no_encontrada(async_client):
    class S:
        async def preparar_evento(self, *args, **kwargs): ...
    async def raise_nf(*_, **__):
        raise PartidaNoEncontrada()

    mock_service = S()
    setattr(mock_service, "preparar_evento", raise_nf)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    payload = {"id_jugador": 1, "id_carta": 40}
    resp = await async_client.post("/partidas/1/eventos", json=payload)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Partida no encontrada"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

from app.capa_2_logica.errores import CartaNoEsEvento

@pytest.mark.asyncio
async def test_jugar_evento_carta_no_es_evento(async_client):
    class S:
        async def preparar_evento(self, *args, **kwargs): ...
    async def raise_err(*_, **__):
        raise CartaNoEsEvento()

    mock_service = S()
    setattr(mock_service, "preparar_evento", raise_err)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    payload = {"id_jugador": 1, "id_carta": 40}
    resp = await async_client.post("/partidas/1/eventos", json=payload)

    assert resp.status_code == 400
    assert resp.json()["detail"] == "La carta no es un evento"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


from app.capa_2_logica.errores import EventoNoImplementado

@pytest.mark.asyncio
async def test_jugar_evento_no_implementado(async_client):
    class S:
        async def preparar_evento(self, *args, **kwargs): ...
    async def raise_err(*_, **__):
        raise EventoNoImplementado("Evento no reconocido")

    mock_service = S()
    setattr(mock_service, "preparar_evento", raise_err)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    payload = {"id_jugador": 1, "id_carta": 999}
    resp = await async_client.post("/partidas/1/eventos", json=payload)

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Evento no reconocido"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)  

@pytest.mark.asyncio
async def test_jugar_evento_jugador_no_encontrado(async_client):
    class S:
        async def preparar_evento(self, *args, **kwargs): ...
    async def raise_err(*_, **__):
        raise JugadorNoEncontrado()

    mock_service = S()
    setattr(mock_service, "preparar_evento", raise_err)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    payload = {"id_jugador": 1, "id_carta": 40}
    resp = await async_client.post("/partidas/1/eventos", json=payload)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Jugador no encontrado"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_jugar_evento_jugador_no_en_partida(async_client):
    class S:
        async def preparar_evento(self, *args, **kwargs): ...
    async def raise_err(*_, **__):
        raise JugadorNoEnPartida()

    mock_service = S()
    setattr(mock_service, "preparar_evento", raise_err)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    payload = {"id_jugador": 1, "id_carta": 40}
    resp = await async_client.post("/partidas/1/eventos", json=payload)

    assert resp.status_code == 400
    assert resp.json()["detail"] == "El jugador no pertenece a la partida"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_jugar_evento_entra_en_desgracia_sin_set_id_notificacion(async_client, monkeypatch):
    import app.capa_3_api.routers.partidas as rpartidas

    llamadas = []

    async def fake_notificar_entra(*_, **kwargs):
        llamadas.append(kwargs)

    monkeypatch.setattr(rpartidas, "notificar_jugador_entra_en_desgracia_detalle", fake_notificar_entra, raising=True)

    class ServicioMock:
        async def preparar_evento(self, *_, **__):
            e = JugadorEnDesgraciaSocial()
            # contexto simulado
            secreto = type("Se", (), {
                "id_secreto": 77,
                "estado": type("E", (), {"name": "oculto"})(),
                "tipo": type("T", (), {"name": "otro"})()
            })()
            setattr(e, "secreto_afectado", secreto)
            setattr(e, "posicion_secreto", 1)
            setattr(e, "jugador_id", 8)
            setattr(e, "partida_id", 1)
            raise e

    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: ServicioMock()

    payload = {
        "id_jugador": 3,
        "id_carta": 40,
        "id_carta_descarte": None,
        "id_secreto": 77,
        "id_jugador_objetivo": 8,
        "id_set": None
    }

    resp = await async_client.post("/partidas/1/eventos", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["jugador_entra_en_desgracia_social"] is True
    assert data["secreto_id"] == 77
    # Verificación notificación
    assert len(llamadas) == 1
    kw = llamadas[0]
    assert "set_id" not in kw
    assert kw["partida_id"] == 1
    assert kw["jugador_id"] == 8
    assert kw["secreto_id"] == 77
    assert kw["posicion_secreto"] == 1
    assert kw["secreto_estado"] == "oculto"
    assert kw["secreto_tipo"] == "otro"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)


@pytest.mark.asyncio
async def test_jugar_evento_sale_de_desgracia_sin_set_id_notificacion(async_client, monkeypatch):
    import app.capa_3_api.routers.partidas as rpartidas

    llamadas = []

    async def fake_notificar_sale(*_, **kwargs):
        llamadas.append(kwargs)

    monkeypatch.setattr(rpartidas, "notificar_jugador_sale_de_desgracia_detalle", fake_notificar_sale, raising=True)

    class ServicioMock:
        async def preparar_evento(self, *_, **__):
            e = JugadorSaleDeDesgraciaSocial()
            secreto = type("Se", (), {
                "id_secreto": 99,
                "estado": type("E", (), {"name": "revelado"})(),
                "tipo": type("T", (), {"name": "otro"})()
            })()
            setattr(e, "secreto_afectado", secreto)
            setattr(e, "posicion_secreto", 0)
            setattr(e, "jugador_id", 10)
            setattr(e, "partida_id", 2)
            raise e

    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: ServicioMock()

    payload = {
        "id_jugador": 4,
        "id_carta": 60,
        "id_carta_descarte": None,
        "id_secreto": 99,
        "id_jugador_objetivo": 10,
        "id_set": None
    }

    resp = await async_client.post("/partidas/2/eventos", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["jugador_sale_de_desgracia_social"] is True
    assert data["secreto_id"] == 99

    assert len(llamadas) == 1
    kw = llamadas[0]
    assert "set_id" not in kw
    assert kw["partida_id"] == 2
    assert kw["jugador_id"] == 10
    assert kw["secreto_id"] == 99
    assert kw["posicion_secreto"] == 0
    assert kw["secreto_estado"] == "revelado"
    assert kw["secreto_tipo"] == "otro"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)