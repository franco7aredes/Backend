import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import Dict

from app.main import app as fastapi_app
from app.capa_2_logica.fabrica import obtener_servicio_juego
from app.capa_2_logica.servicio_juego import ServicioJuego
from app.capa_2_logica.resultados import DescartarResultado, CantidadManosResultado
from app.capa_2_logica.errores import PartidaNoEncontrada

from app.capa_3_api.dtos.nsf import ActivarNSFPedido, JugarNSFPedido
from app.capa_3_api.nsf_tipos import VentanaNSFActiva

import app.capa_3_api.routers.nsf as nsf_router_modulo

# esto voy a usar de limpieza, pues tengo algo en el router que se comparte constantemente
@pytest.fixture(autouse=True)
def limpiar_estado_global_ventanas():
    nsf_router_modulo._VENTANAS.clear()
    yield
    nsf_router_modulo._VENTANAS.clear()


@pytest.mark.asyncio
async def test_activar_nsf_bonito(async_client, monkeypatch):
    class S:
        async def permite_nsf(self, *args, **kwargs):...

    mock_service = S()
    setattr(mock_service, "permite_nsf", AsyncMock(return_value=True))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    mock_difundir = AsyncMock()
    # mockeo la ventana
    mock_obj = MagicMock()
    mock_obj.ventana_id = "ventana-test-uuid"
    mock_obj.tiempo_ms = 621877
    mock_obj.tarea = MagicMock()
    mock_activar = AsyncMock(return_value=mock_obj)

    monkeypatch.setattr(nsf_router_modulo.administrador, "difundir_a_partida", mock_difundir)
    monkeypatch.setattr(nsf_router_modulo,"activar_ventana_nsf", mock_activar)

    pedido = {
        "id_jugador": 1,
        "tipo_accion": "jugar_set",
        "payload": {"juajua":"esto no se si importa para test"}
    }

    res = await async_client.post("/partidas/1/nsf/activar", json=pedido)

    assert res.status_code == 201
    cuerpo = res.json()
    assert cuerpo["window_id"] == "ventana-test-uuid"
    assert cuerpo["deadline_ms"] == 621877
    
    # ahora veo si se llamaron los mocks
    mock_service.permite_nsf.assert_called_once_with(
        partida_id=1,
        tipo_accion="jugar_set",
        payload={"juajua":"esto no se si importa para test"},
        id_jugador_accion=1
    )
    mock_difundir.assert_called_once()
    mock_activar.assert_called_once()
    assert mock_difundir.call_args[0][1]["evento"] == "canplaynsf"


    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_activar_nsf_no_cancelable(async_client):

    class S:
        async def permite_nsf(self, *args, **kwargs):...

    mock_service = S()
    setattr(mock_service, "permite_nsf", AsyncMock(return_value=False))
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    pedido = {
        "id_jugador": 1,
        "tipo_accion": "jugar_set",
        "payload": {}
    }

    res = await async_client.post("/partidas/1/nsf/activar", json=pedido)

    assert res.status_code == 204
    assert 1 not in nsf_router_modulo._VENTANAS

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_activar_nsf_en_curso(async_client):

    ventana_presente = VentanaNSFActiva(
        partida_id=1, ventana_id="presente", actor_id=2,
        tipo_accion="jugar", payload={}, contador=0, tiempo_ms= 4141
    )
    nsf_router_modulo._VENTANAS[1] = ventana_presente

    class S:
        async def permite_nsf(self, *args, **kwargs):...

    mock_service = S()
    # voy a revisar si llama a la funcion del servicio, por eso esto no lo hacia antes
    mock_es_cancelable = AsyncMock(return_value=True)

    setattr(mock_service, "permite_nsf", mock_es_cancelable)
    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    pedido = {
        "id_jugador": 1,
        "tipo_accion": "jugar_set",
        "payload": {}
    }

    res = await async_client.post("/partidas/1/nsf/activar", json=pedido)

    assert res.status_code == 409
    assert res.json()["detail"] == "nsf_en_curso"
    mock_es_cancelable.assert_not_called()

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_jugar_nsf_bonito(async_client, monkeypatch):
    
    mock_tarea_original = MagicMock()
    mock_tarea_original.done.return_value = False

    existente = VentanaNSFActiva(
        partida_id=2, ventana_id="ventana123", actor_id=3,
        tipo_accion="jugar_set", payload={}, contador=0, tiempo_ms=99999999,
        tarea=mock_tarea_original # la original
    )

    nsf_router_modulo._VENTANAS[2] = existente

    class S:
        async def validar_carta_nsf(self, *args, **kwargs):...
        async def descartar_carta(self, *args, **kwargs):...
        async def obtener_cantidad_manos(self, *args, **kwargs):...

    mock_service = S()
    setattr(mock_service, "validar_carta_nsf", AsyncMock(return_value=None))
    setattr(mock_service, "descartar_carta", AsyncMock(return_value=DescartarResultado(carta=object())))
    setattr(mock_service, "obtener_cantidad_manos", AsyncMock(return_value=CantidadManosResultado(cartas_por_jugador={3: 5, 6: 4})))

    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    async def mock_refrescar_side_effect(ventana, ventanas_dict):
        ventana.contador += 1
        ventana.tiempo_ms = 55555  # El valor que el test espera
        if ventana.tarea:
            ventana.tarea.cancel()


    # mockeo utilidades que voy a chequear despues
    mock_difundir = AsyncMock()
    mock_refrescar = AsyncMock(side_effect=mock_refrescar_side_effect)

    monkeypatch.setattr(nsf_router_modulo.administrador, "difundir_a_partida", mock_difundir)
    monkeypatch.setattr(nsf_router_modulo.time, "time", lambda: 50000.0)
    monkeypatch.setattr(nsf_router_modulo, "refrescar_ventana_nsf", mock_refrescar)

    # el otro jugador va a hacer el pedido
    pedido = {
        "id_jugador": 6,
        "carta_id": 99,
        "ventana_id": "ventana123"
    }

    res = await async_client.post("/partidas/2/nsf/jugar", json=pedido)

    # veo las respuestas HTTP
    assert res.status_code == 200
    cuerpo = res.json()
    assert cuerpo["count"] == 1
    assert cuerpo["deadline_ms"] == 55555

    # veo los mocks
    mock_service.validar_carta_nsf.assert_called_once_with(2, 6, 99)
    mock_service.descartar_carta.assert_called_once_with(2, 6, 99)
    mock_tarea_original.cancel.assert_called_once()
    mock_refrescar.assert_called_once()

    # veamos que se difundio 3 veces
    assert mock_difundir.call_count == 3
    assert mock_difundir.call_args_list[0][0][1]["evento"] == "jugador_descarto"
    assert mock_difundir.call_args_list[1][0][1]["evento"] == "manos_actualizadas"
    assert mock_difundir.call_args_list[2][0][1]["evento"] == "nsfplayed"
    assert mock_difundir.call_args_list[2][0][1]["count"] == 1

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_jugar_nsf_falla_ventana_vencida(async_client, monkeypatch):

    existente = VentanaNSFActiva(
        partida_id=1, ventana_id="ventana123", actor_id=2,
        tipo_accion="jugar_set", payload={}, contador=0, tiempo_ms=1000
    )
    nsf_router_modulo._VENTANAS[1] = existente

    # decimos que justo paso el tiempo de ventana
    monkeypatch.setattr(nsf_router_modulo.time, "time", lambda: 1.501)

    pedido = {
        "id_jugador": 5,
        "carta_id": 99,
        "ventana_id": "ventana123"
    }

    res = await async_client.post("/partidas/1/nsf/jugar", json=pedido)

    assert res.status_code == 410
    assert res.json()["detail"] == "ventana_expirada"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_jugar_nsf_cancela_el_actor(async_client, monkeypatch):

    
    existente = VentanaNSFActiva(
        partida_id=1, ventana_id="ventana123", actor_id=2,
        tipo_accion="jugar_set", payload={}, contador=0, tiempo_ms=99999999
    )
    nsf_router_modulo._VENTANAS[1] = existente

    monkeypatch.setattr(nsf_router_modulo.time, "time", lambda: 100.0)

    pedido = {
        "id_jugador": 2,
        "carta_id": 99,
        "ventana_id": "ventana123"
    }

    res = await async_client.post("/partidas/1/nsf/jugar", json=pedido)
    
    assert res.status_code == 400
    assert res.json()["detail"] == "iniciador_no_puede_primer_nsf"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_jugar_nsf_error_no_es_nsf(async_client, monkeypatch):

    existente = VentanaNSFActiva(
        partida_id=1, ventana_id="ventana123", actor_id=2,
        tipo_accion="jugar_set", payload={}, contador=0, tiempo_ms=9999999
    )
    nsf_router_modulo._VENTANAS[1] = existente

    class S:
        async def validar_carta_nsf(self, *args, **kwargs):...
    
    mock_service = S()
    async def raise_err( *_, **__):
        raise ValueError("no_es_nsf_pero_intento_actuar_como_nsf")

    setattr(mock_service, "validar_carta_nsf", raise_err)

    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    monkeypatch.setattr(nsf_router_modulo.time, "time", lambda: 100.0)
    
    pedido = {
        "id_jugador": 22,
        "carta_id": 99,
        "ventana_id": "ventana123"
    }

    res = await async_client.post("/partidas/1/nsf/jugar", json=pedido)

    assert res.status_code == 400
    assert res.json()["detail"] == "Sos un vivo, esto no es una carta NSF"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_jugar_nsf_error_partida_no_encontrada(async_client, monkeypatch):

    existente = VentanaNSFActiva(
        partida_id=1, ventana_id="ventana123", actor_id=2,
        tipo_accion="jugar_set", payload={}, contador=0, tiempo_ms=9999999
    )
    nsf_router_modulo._VENTANAS[1] = existente

    class S:
        async def validar_carta_nsf(self, *args, **kwargs):...
    
    mock_service = S()
    async def raise_err( *_, **__):
        raise PartidaNoEncontrada()

    setattr(mock_service, "validar_carta_nsf", raise_err)

    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    monkeypatch.setattr(nsf_router_modulo.time, "time", lambda: 100.0)
    
    pedido = {
        "id_jugador": 22,
        "carta_id": 99,
        "ventana_id": "ventana123"
    }

    res = await async_client.post("/partidas/1/nsf/jugar", json=pedido)

    assert res.status_code == 404
    assert res.json()["detail"] == "Partida no encontrada"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_jugar_nsf_error_jugador_no_encontrado(async_client, monkeypatch):

    existente = VentanaNSFActiva(
        partida_id=1, ventana_id="ventana123", actor_id=2,
        tipo_accion="jugar_set", payload={}, contador=0, tiempo_ms=9999999
    )
    nsf_router_modulo._VENTANAS[1] = existente

    class S:
        async def validar_carta_nsf(self, *args, **kwargs):...
    
    mock_service = S()
    async def raise_err( *_, **__):
        raise ValueError("jugador_no_encontrado")

    setattr(mock_service, "validar_carta_nsf", raise_err)

    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    monkeypatch.setattr(nsf_router_modulo.time, "time", lambda: 100.0)
    
    pedido = {
        "id_jugador": 22,
        "carta_id": 99,
        "ventana_id": "ventana123"
    }

    res = await async_client.post("/partidas/1/nsf/jugar", json=pedido)

    assert res.status_code == 404
    assert res.json()["detail"] == "Jugador no encontrado"

    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_jugar_nsf_error_jugador_no_en_partida(async_client, monkeypatch):

    existente = VentanaNSFActiva(
        partida_id=1, ventana_id="ventana123", actor_id=2,
        tipo_accion="jugar_set", payload={}, contador=0, tiempo_ms=9999999
    )
    nsf_router_modulo._VENTANAS[1] = existente

    class S:
        async def validar_carta_nsf(self, *args, **kwargs):...
    
    mock_service = S()
    async def raise_err( *_, **__):
        raise ValueError("jugador_no_en_partida")

    setattr(mock_service, "validar_carta_nsf", raise_err)

    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    monkeypatch.setattr(nsf_router_modulo.time, "time", lambda: 100.0)
    
    pedido = {
        "id_jugador": 22,
        "carta_id": 99,
        "ventana_id": "ventana123"
    }

    res = await async_client.post("/partidas/1/nsf/jugar", json=pedido)

    assert res.status_code == 400
    assert res.json()["detail"] == "El jugador no pertenece a la partida indicada"
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_jugar_nsf_error_no_hay_tal_carta(async_client, monkeypatch):

    existente = VentanaNSFActiva(
        partida_id=1, ventana_id="ventana123", actor_id=2,
        tipo_accion="jugar_set", payload={}, contador=0, tiempo_ms=9999999
    )
    nsf_router_modulo._VENTANAS[1] = existente

    class S:
        async def validar_carta_nsf(self, *args, **kwargs):...
    
    mock_service = S()
    async def raise_err( *_, **__):
        raise ValueError("no_hay_tal_carta")

    setattr(mock_service, "validar_carta_nsf", raise_err)

    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    monkeypatch.setattr(nsf_router_modulo.time, "time", lambda: 100.0)

    
    pedido = {
        "id_jugador": 22,
        "carta_id": 99,
        "ventana_id": "ventana123"
    }

    res = await async_client.post("/partidas/1/nsf/jugar", json=pedido)

    assert res.status_code == 400
    assert res.json()["detail"] == "La carta mandada no coincide con los datos guardados"
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)

@pytest.mark.asyncio
async def test_jugar_nsf_error_no_hay_carta_para_descartar(async_client, monkeypatch):

    existente = VentanaNSFActiva(
        partida_id=1, ventana_id="ventana123", actor_id=2,
        tipo_accion="jugar_set", payload={}, contador=0, tiempo_ms=9999999
    )
    nsf_router_modulo._VENTANAS[1] = existente

    class S:
        async def validar_carta_nsf(self, *args, **kwargs):...
        async def descartar_carta(self, *args, **kwargs):...
    
    mock_service = S()
    async def raise_err( *_, **__):
        raise Exception

    setattr(mock_service, "validar_carta_nsf", AsyncMock(return_value=None))
    setattr(mock_service, "descartar_carta", raise_err)

    fastapi_app.dependency_overrides[obtener_servicio_juego] = lambda: mock_service

    monkeypatch.setattr(nsf_router_modulo.time, "time", lambda: 100.0)

    
    pedido = {
        "id_jugador": 22,
        "carta_id": 99,
        "ventana_id": "ventana123"
    }

    res = await async_client.post("/partidas/1/nsf/jugar", json=pedido)

    mock_service.validar_carta_nsf.assert_called_once_with(1, 22, 99)
    assert res.status_code == 404
    assert res.json()["detail"] == "No se encontro carta para descartar en esta partida"
    fastapi_app.dependency_overrides.pop(obtener_servicio_juego, None)
